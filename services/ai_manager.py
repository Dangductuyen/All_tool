"""
AI Manager - Core orchestrator for smart auto-mode translation.

This is the most important module. It coordinates:
- Key validation (key_checker.py)
- Smart model selection (model_selector.py)
- Auto fallback on errors (model -> model -> model, key -> key)
- Per-engine state tracking (which keys/models are active)

Usage (Smart Auto Mode):
    manager = AIManager()
    manager.add_key("gemini", "AIza...")
    manager.check_all()  # validates keys + loads models + auto-selects
    engine_state = manager.get_state("gemini")
    # engine_state.active_model -> best model auto-selected
    # engine_state.active_key -> best key
"""
import time
import threading
from datetime import datetime
from typing import List, Optional, Dict, Callable
from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtCore import QThread, Signal

from utils.logger import log
from services.key_checker import (
    KeyCheckResult, KeyCheckStatus, check_key, check_all_keys,
)
from services.model_selector import (
    ModelSelection, select_best_model, get_fallback_model,
    get_lighter_model, filter_models, rank_models, MODEL_PRIORITY,
)
from services.translator_service import (
    APIKeyManager, KeyStatus, TranslationErrorCode,
)


# ============================================================
# Engine State
# ============================================================

@dataclass
class EngineKeyState:
    """State of a single API key within an engine."""
    key: str
    key_index: int
    status: KeyCheckStatus = KeyCheckStatus.UNCHECKED
    available_models: List[str] = field(default_factory=list)
    selected_model: str = ""
    error_count: int = 0
    last_error: str = ""
    last_used: float = 0.0
    usage_info: str = ""

    @property
    def is_usable(self) -> bool:
        return self.status in (KeyCheckStatus.VALID, KeyCheckStatus.UNCHECKED)

    @property
    def masked_key(self) -> str:
        if len(self.key) > 12:
            return self.key[:8] + "..." + self.key[-4:]
        return self.key[:4] + "..."


@dataclass
class EngineState:
    """Complete state of an AI engine."""
    engine: str
    keys: List[EngineKeyState] = field(default_factory=list)
    active_key_index: int = -1
    active_model: str = ""
    all_available_models: List[str] = field(default_factory=list)
    is_checked: bool = False
    last_check_time: str = ""

    @property
    def active_key(self) -> Optional[str]:
        if 0 <= self.active_key_index < len(self.keys):
            return self.keys[self.active_key_index].key
        return None

    @property
    def active_key_state(self) -> Optional[EngineKeyState]:
        if 0 <= self.active_key_index < len(self.keys):
            return self.keys[self.active_key_index]
        return None

    @property
    def has_valid_key(self) -> bool:
        return any(k.is_usable for k in self.keys)

    @property
    def valid_key_count(self) -> int:
        return sum(1 for k in self.keys if k.status == KeyCheckStatus.VALID)

    @property
    def total_key_count(self) -> int:
        return len(self.keys)

    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        if not self.keys:
            return "Chua co API key"
        if not self.is_checked:
            return f"{len(self.keys)} key(s) chua kiem tra"

        valid = self.valid_key_count
        total = self.total_key_count
        model = self.active_model or "chua chon"

        if valid == 0:
            return f"0/{total} key hop le"
        return f"{valid}/{total} key OK | Model: {model}"


# ============================================================
# Check All Keys Worker (QThread)
# ============================================================

class CheckAllKeysWorker(QThread):
    """Background worker to check all API keys across engines."""

    # Signal: engine, key_index, KeyCheckResult (as dict for thread safety)
    key_checked = Signal(str, int, object)
    # Signal: all done
    all_done = Signal(list)  # List[KeyCheckResult]
    # Signal: log message
    log_message = Signal(str)

    def __init__(self, keys_by_engine: Dict[str, List[str]], parent=None):
        super().__init__(parent)
        self.keys_by_engine = keys_by_engine

    def run(self):
        results = []
        for engine, keys in self.keys_by_engine.items():
            for idx, key in enumerate(keys, start=1):
                self.log_message.emit(
                    f"Dang kiem tra {engine} Key#{idx}..."
                )
                result = check_key(engine, key, key_index=idx)
                results.append(result)
                self.key_checked.emit(engine, idx, result)
                self.log_message.emit(result.to_log_line())

        self.all_done.emit(results)


# ============================================================
# AI Manager
# ============================================================

class AIManager:
    """Core AI management orchestrator.

    Manages:
    - API keys per engine with validation
    - Smart model selection per engine
    - Auto fallback on errors
    - Key rotation
    """

    def __init__(self, key_manager: Optional[APIKeyManager] = None):
        self._key_manager = key_manager
        self._states: Dict[str, EngineState] = {
            "gemini": EngineState(engine="gemini"),
            "openai": EngineState(engine="openai"),
            "deepl": EngineState(engine="deepl"),
            "groq": EngineState(engine="groq"),
        }
        self._lock = threading.Lock()
        self._check_worker: Optional[CheckAllKeysWorker] = None

        # Sync from key_manager if provided
        if key_manager:
            self._sync_from_key_manager()

    def _sync_from_key_manager(self):
        """Sync key states from the APIKeyManager."""
        if not self._key_manager:
            return

        for engine in self._states:
            entries = self._key_manager.get_keys(engine)
            key_states = []
            for idx, entry in enumerate(entries):
                status_map = {
                    KeyStatus.VALID: KeyCheckStatus.VALID,
                    KeyStatus.INVALID: KeyCheckStatus.INVALID,
                    KeyStatus.QUOTA_EXCEEDED: KeyCheckStatus.QUOTA_EXCEEDED,
                    KeyStatus.UNCHECKED: KeyCheckStatus.UNCHECKED,
                }
                key_states.append(EngineKeyState(
                    key=entry.key,
                    key_index=idx + 1,
                    status=status_map.get(entry.status, KeyCheckStatus.UNCHECKED),
                    error_count=entry.error_count,
                    last_error=entry.last_error,
                ))
            self._states[engine].keys = key_states

    def _sync_to_key_manager(self, engine: str):
        """Sync key states back to the APIKeyManager."""
        if not self._key_manager:
            return

        status_map = {
            KeyCheckStatus.VALID: KeyStatus.VALID,
            KeyCheckStatus.INVALID: KeyStatus.INVALID,
            KeyCheckStatus.QUOTA_EXCEEDED: KeyStatus.QUOTA_EXCEEDED,
            KeyCheckStatus.UNCHECKED: KeyStatus.UNCHECKED,
            KeyCheckStatus.NO_PERMISSION: KeyStatus.INVALID,
            KeyCheckStatus.NETWORK_ERROR: KeyStatus.UNCHECKED,
            KeyCheckStatus.TIMEOUT: KeyStatus.UNCHECKED,
        }

        state = self._states.get(engine)
        if not state:
            return

        for ks in state.keys:
            km_status = status_map.get(ks.status, KeyStatus.UNCHECKED)
            self._key_manager.update_key_status(
                engine, ks.key, km_status, ks.last_error
            )

    # ================================================================
    # Key Management
    # ================================================================

    def add_key(self, engine: str, key: str) -> bool:
        """Add an API key for an engine."""
        with self._lock:
            state = self._states.get(engine)
            if not state:
                return False

            # Check duplicate
            for ks in state.keys:
                if ks.key == key:
                    return False

            state.keys.append(EngineKeyState(
                key=key,
                key_index=len(state.keys) + 1,
            ))

            # Also add to key_manager
            if self._key_manager:
                self._key_manager.add_key(engine, key)

            return True

    def remove_key(self, engine: str, key: str) -> bool:
        """Remove an API key."""
        with self._lock:
            state = self._states.get(engine)
            if not state:
                return False

            state.keys = [ks for ks in state.keys if ks.key != key]
            # Re-index
            for i, ks in enumerate(state.keys):
                ks.key_index = i + 1

            # Reset active key if removed
            if state.active_key == key:
                state.active_key_index = -1
                self._auto_select_key(engine)

            if self._key_manager:
                self._key_manager.remove_key(engine, key)

            return True

    def get_keys(self, engine: str) -> List[EngineKeyState]:
        """Get all key states for an engine."""
        with self._lock:
            state = self._states.get(engine)
            return list(state.keys) if state else []

    # ================================================================
    # Key Checking
    # ================================================================

    def check_key(self, engine: str, key: str) -> KeyCheckResult:
        """Check a single API key and update state."""
        state = self._states.get(engine)
        if not state:
            return KeyCheckResult(
                engine=engine, key=key, key_index=0,
                status=KeyCheckStatus.INVALID,
                message=f"Engine '{engine}' khong ho tro",
            )

        # Find key state
        key_state = None
        for ks in state.keys:
            if ks.key == key:
                key_state = ks
                break

        if not key_state:
            # Key not in state, add it
            self.add_key(engine, key)
            key_state = state.keys[-1]

        # Perform check
        result = check_key(engine, key, key_state.key_index)

        # Update state
        with self._lock:
            key_state.status = result.status
            key_state.available_models = result.available_models
            key_state.usage_info = result.usage_info
            if result.is_valid:
                key_state.error_count = 0
                key_state.last_error = ""
            else:
                key_state.last_error = result.message

            # Merge available models into engine state
            if result.available_models:
                existing = set(state.all_available_models)
                for m in result.available_models:
                    if m not in existing:
                        state.all_available_models.append(m)

            self._sync_to_key_manager(engine)

        return result

    def check_engine(self, engine: str) -> List[KeyCheckResult]:
        """Check all keys for a single engine and auto-select best model."""
        results = []
        state = self._states.get(engine)
        if not state or not state.keys:
            return results

        for ks in state.keys:
            result = self.check_key(engine, ks.key)
            results.append(result)

        # Auto-select best model and key
        with self._lock:
            state.is_checked = True
            state.last_check_time = datetime.now().strftime("%H:%M:%S")
            self._auto_select_key(engine)
            self._auto_select_model(engine)

        return results

    def create_check_all_worker(self) -> Optional[CheckAllKeysWorker]:
        """Create a background worker to check all keys.

        Returns None if no keys to check.
        """
        keys_by_engine = {}
        for engine, state in self._states.items():
            if state.keys:
                keys_by_engine[engine] = [ks.key for ks in state.keys]

        if not keys_by_engine:
            return None

        self._check_worker = CheckAllKeysWorker(keys_by_engine)
        return self._check_worker

    def apply_check_result(self, result: KeyCheckResult):
        """Apply a single check result from the background worker."""
        state = self._states.get(result.engine)
        if not state:
            return

        with self._lock:
            for ks in state.keys:
                if ks.key == result.key:
                    ks.status = result.status
                    ks.available_models = result.available_models
                    ks.usage_info = result.usage_info
                    ks.selected_model = result.selected_model
                    if result.is_valid:
                        ks.error_count = 0
                        ks.last_error = ""
                    else:
                        ks.last_error = result.message
                    break

            # Merge models
            if result.available_models:
                existing = set(state.all_available_models)
                for m in result.available_models:
                    if m not in existing:
                        state.all_available_models.append(m)

            self._sync_to_key_manager(result.engine)

    def finalize_check(self, engine: str):
        """Called after all keys for an engine are checked.
        Auto-selects best key and model."""
        with self._lock:
            state = self._states.get(engine)
            if state:
                state.is_checked = True
                state.last_check_time = datetime.now().strftime("%H:%M:%S")
                self._auto_select_key(engine)
                self._auto_select_model(engine)

    # ================================================================
    # Auto Selection (called with lock held)
    # ================================================================

    def _auto_select_key(self, engine: str):
        """Auto-select the best available key for an engine."""
        state = self._states.get(engine)
        if not state or not state.keys:
            state.active_key_index = -1
            return

        # Priority: VALID > UNCHECKED > QUOTA_EXCEEDED (might have reset)
        priority = {
            KeyCheckStatus.VALID: 0,
            KeyCheckStatus.UNCHECKED: 1,
            KeyCheckStatus.QUOTA_EXCEEDED: 2,
        }

        best_idx = -1
        best_priority = 999

        for i, ks in enumerate(state.keys):
            p = priority.get(ks.status, 999)
            if p < best_priority:
                best_priority = p
                best_idx = i

        state.active_key_index = best_idx

    def _auto_select_model(self, engine: str):
        """Auto-select the best model for an engine based on available models."""
        state = self._states.get(engine)
        if not state:
            return

        if state.all_available_models:
            selection = select_best_model(engine, state.all_available_models)
            state.active_model = selection.selected_model
            # Re-sort the available models list
            state.all_available_models = selection.available_models
        else:
            # Use priority list defaults
            priority = MODEL_PRIORITY.get(engine, [])
            state.active_model = priority[0] if priority else ""

        # Also update per-key selected models
        for ks in state.keys:
            if ks.is_usable and ks.available_models:
                sel = select_best_model(engine, ks.available_models)
                ks.selected_model = sel.selected_model

    # ================================================================
    # Getters
    # ================================================================

    def get_state(self, engine: str) -> Optional[EngineState]:
        """Get the full state for an engine."""
        return self._states.get(engine)

    def get_active_key(self, engine: str) -> Optional[str]:
        """Get the active API key for an engine."""
        state = self._states.get(engine)
        return state.active_key if state else None

    def get_active_model(self, engine: str) -> str:
        """Get the active model for an engine."""
        state = self._states.get(engine)
        return state.active_model if state else ""

    def get_available_models(self, engine: str) -> List[str]:
        """Get ranked available models for an engine."""
        state = self._states.get(engine)
        if state and state.all_available_models:
            return list(state.all_available_models)
        # Return priority defaults
        return list(MODEL_PRIORITY.get(engine, []))

    # ================================================================
    # Fallback / Error Handling
    # ================================================================

    def handle_translation_error(self, engine: str, error_code: TranslationErrorCode,
                                  current_key: str, current_model: str
                                  ) -> Dict[str, Optional[str]]:
        """Handle a translation error and return new key/model to try.

        Returns:
            Dict with 'key' and 'model' - either may be None if no fallback.
        """
        result = {"key": current_key, "model": current_model}
        state = self._states.get(engine)
        if not state:
            return result

        with self._lock:
            # Update key state
            for ks in state.keys:
                if ks.key == current_key:
                    ks.error_count += 1
                    ks.last_error = f"Error {error_code.value}"

                    if error_code == TranslationErrorCode.AUTH_INVALID:
                        ks.status = KeyCheckStatus.INVALID
                    elif error_code == TranslationErrorCode.QUOTA_EXCEEDED:
                        ks.status = KeyCheckStatus.QUOTA_EXCEEDED
                    elif error_code == TranslationErrorCode.NO_PERMISSION:
                        ks.status = KeyCheckStatus.NO_PERMISSION
                    break

            self._sync_to_key_manager(engine)

        # Decide action based on error type
        if error_code == TranslationErrorCode.AUTH_INVALID:
            # Key is bad -> rotate to next key
            new_key = self._get_next_usable_key(engine, current_key)
            if new_key:
                result["key"] = new_key
                log.info(f"[AIManager] Key rotation: {engine} -> Key#{self._get_key_index(engine, new_key)}")
            else:
                result["key"] = None
                log.warning(f"[AIManager] No usable keys left for {engine}")

        elif error_code == TranslationErrorCode.MODEL_NOT_FOUND:
            # Model doesn't exist -> try next model
            new_model = get_fallback_model(
                engine, current_model, state.all_available_models
            )
            if new_model:
                result["model"] = new_model
                with self._lock:
                    state.active_model = new_model
                log.info(f"[AIManager] Model fallback: {engine} {current_model} -> {new_model}")
            else:
                result["model"] = None
                log.warning(f"[AIManager] No fallback model for {engine}")

        elif error_code == TranslationErrorCode.NO_PERMISSION:
            # No permission for this model -> try next model, then next key
            new_model = get_fallback_model(
                engine, current_model, state.all_available_models
            )
            if new_model:
                result["model"] = new_model
                with self._lock:
                    state.active_model = new_model
                log.info(f"[AIManager] Permission fallback: {engine} -> model {new_model}")
            else:
                new_key = self._get_next_usable_key(engine, current_key)
                if new_key:
                    result["key"] = new_key
                    log.info(f"[AIManager] Permission fallback: {engine} -> key rotation")

        elif error_code == TranslationErrorCode.QUOTA_EXCEEDED:
            # Quota -> try rotating key first, then lighter model
            new_key = self._get_next_usable_key(engine, current_key)
            if new_key:
                result["key"] = new_key
                log.info(f"[AIManager] Quota rotation: {engine} -> Key#{self._get_key_index(engine, new_key)}")
            else:
                # All keys quota exceeded -> try lighter model
                lighter = get_lighter_model(
                    engine, current_model, state.all_available_models
                )
                if lighter and lighter != current_model:
                    result["model"] = lighter
                    with self._lock:
                        state.active_model = lighter
                    log.info(f"[AIManager] Quota fallback: {engine} -> lighter model {lighter}")

        # For network/timeout errors, we keep the same key/model (retry will handle it)

        return result

    def _get_next_usable_key(self, engine: str, current_key: str) -> Optional[str]:
        """Get next usable key, skipping the current one."""
        state = self._states.get(engine)
        if not state:
            return None

        usable = [ks for ks in state.keys if ks.is_usable and ks.key != current_key]
        if not usable:
            return None

        # Sort by error_count ascending, then by last_used ascending
        usable.sort(key=lambda ks: (ks.error_count, ks.last_used))
        return usable[0].key

    def _get_key_index(self, engine: str, key: str) -> int:
        """Get the index of a key within an engine."""
        state = self._states.get(engine)
        if state:
            for ks in state.keys:
                if ks.key == key:
                    return ks.key_index
        return 0

    # ================================================================
    # Log Formatting
    # ================================================================

    def format_switch_log(self, engine: str, old_key: Optional[str],
                          new_key: Optional[str], old_model: str,
                          new_model: str) -> str:
        """Format a log line for key/model switch."""
        ts = datetime.now().strftime("%H:%M:%S")
        parts = [f"[{ts}]"]

        if old_key != new_key and new_key:
            new_idx = self._get_key_index(engine, new_key)
            parts.append(f"Auto switch -> Key#{new_idx}")

        if old_model != new_model and new_model:
            parts.append(f"Model: {old_model} -> {new_model}")

        return " ".join(parts)
