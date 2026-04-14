"""
API Key Checker - Validates API keys and reports detailed status.

For each key, performs:
1. Lightweight API ping to verify authentication
2. Load available models the key can access
3. Report detailed status (valid/invalid/quota/permissions)

Supports: Gemini, OpenAI, DeepL, Groq
"""
import time
import threading
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field

from utils.logger import log


class KeyCheckStatus(Enum):
    """Detailed key validation status."""
    VALID = "valid"
    INVALID = "invalid"              # 401 - wrong key
    NO_PERMISSION = "no_permission"  # 403 - no access
    QUOTA_EXCEEDED = "quota_exceeded"  # 429 - rate limit/quota
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    UNCHECKED = "unchecked"


@dataclass
class KeyCheckResult:
    """Result of checking a single API key."""
    engine: str
    key: str
    key_index: int
    status: KeyCheckStatus
    message: str = ""
    available_models: List[str] = field(default_factory=list)
    selected_model: str = ""
    response_time_ms: float = 0.0
    timestamp: str = ""
    usage_info: str = ""  # e.g. DeepL character count

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")

    @property
    def is_valid(self) -> bool:
        return self.status == KeyCheckStatus.VALID

    @property
    def masked_key(self) -> str:
        if len(self.key) > 12:
            return self.key[:8] + "..." + self.key[-4:]
        return self.key[:4] + "..."

    def to_log_line(self) -> str:
        """Format as log line: [Time] [AI] [Key Index] [Model] [Status]"""
        model_info = f" (model: {self.selected_model})" if self.selected_model else ""
        if self.is_valid:
            return (f"[{self.timestamp}] {self.engine} Key#{self.key_index} "
                    f"-> OK{model_info}")
        else:
            return (f"[{self.timestamp}] {self.engine} Key#{self.key_index} "
                    f"-> FAIL {self.status.value}: {self.message}")


def _classify_check_error(exception: Exception) -> Tuple[KeyCheckStatus, str]:
    """Classify an exception into KeyCheckStatus and message."""
    raw = str(exception).lower()

    # Check for status codes in error
    status_code = None
    if hasattr(exception, 'status_code'):
        status_code = exception.status_code
    elif hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
        status_code = exception.response.status_code
    else:
        for code_str in ['401', '403', '404', '429', '408']:
            if code_str in str(exception):
                status_code = int(code_str)
                break

    if status_code == 401 or 'unauthorized' in raw or 'invalid api key' in raw or 'invalid_api_key' in raw:
        return KeyCheckStatus.INVALID, "API key khong hop le hoac da bi thu hoi"
    elif status_code == 403 or 'forbidden' in raw or 'permission' in raw:
        return KeyCheckStatus.NO_PERMISSION, "API key khong co quyen truy cap"
    elif status_code == 429 or 'rate limit' in raw or 'quota' in raw or 'too many' in raw:
        return KeyCheckStatus.QUOTA_EXCEEDED, "Da vuot quota hoac rate limit"
    elif 'timeout' in raw or 'timed out' in raw:
        return KeyCheckStatus.TIMEOUT, "Request timeout"
    elif 'connection' in raw or 'network' in raw or 'dns' in raw or 'unreachable' in raw:
        return KeyCheckStatus.NETWORK_ERROR, "Khong the ket noi toi server"
    else:
        return KeyCheckStatus.INVALID, str(exception)[:200]


# ============================================================
# Per-Engine Key Check Functions
# ============================================================

def check_gemini_key(api_key: str, key_index: int) -> KeyCheckResult:
    """Validate Gemini API key and load available models."""
    start = time.time()
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        # Step 1: List models (validates key + gets available models)
        models = []
        for m in genai.list_models():
            methods = m.supported_generation_methods or []
            if "generateContent" in methods:
                name = m.name.replace("models/", "")
                # Filter out embedding/vision-only models
                name_lower = name.lower()
                if any(skip in name_lower for skip in ["embedding", "aqa", "retrieval"]):
                    continue
                models.append(name)

        elapsed = (time.time() - start) * 1000
        return KeyCheckResult(
            engine="gemini",
            key=api_key,
            key_index=key_index,
            status=KeyCheckStatus.VALID,
            message=f"API key hop le - {len(models)} models kha dung",
            available_models=models,
            response_time_ms=elapsed,
        )

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        status, message = _classify_check_error(e)
        return KeyCheckResult(
            engine="gemini",
            key=api_key,
            key_index=key_index,
            status=status,
            message=message,
            response_time_ms=elapsed,
        )


def check_openai_key(api_key: str, key_index: int) -> KeyCheckResult:
    """Validate OpenAI API key and load available models."""
    start = time.time()
    try:
        import openai
        client = openai.OpenAI(api_key=api_key, timeout=15)

        # Step 1: List models (validates key + gets available models)
        response = client.models.list()
        models = []
        for m in response.data:
            mid = m.id.lower()
            # Filter: only chat/completion models, not embedding/whisper/dall-e/tts
            if any(skip in mid for skip in ["embedding", "whisper", "dall-e",
                                             "tts", "davinci", "babbage",
                                             "moderation"]):
                continue
            if "gpt" in mid or "o1" in mid or "o3" in mid or "chatgpt" in mid:
                models.append(m.id)
        models.sort()

        elapsed = (time.time() - start) * 1000
        return KeyCheckResult(
            engine="openai",
            key=api_key,
            key_index=key_index,
            status=KeyCheckStatus.VALID,
            message=f"API key hop le - {len(models)} models kha dung",
            available_models=models,
            response_time_ms=elapsed,
        )

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        status, message = _classify_check_error(e)
        return KeyCheckResult(
            engine="openai",
            key=api_key,
            key_index=key_index,
            status=status,
            message=message,
            response_time_ms=elapsed,
        )


def check_deepl_key(api_key: str, key_index: int) -> KeyCheckResult:
    """Validate DeepL API key."""
    start = time.time()
    try:
        import httpx

        base_url = "https://api-free.deepl.com"
        if not api_key.endswith(":fx"):
            base_url = "https://api.deepl.com"

        with httpx.Client(timeout=15) as client:
            resp = client.get(
                f"{base_url}/v2/usage",
                headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
            )

        elapsed = (time.time() - start) * 1000

        if resp.status_code == 200:
            data = resp.json()
            used = data.get("character_count", 0)
            limit = data.get("character_limit", 0)
            remaining = limit - used
            usage_info = f"{used}/{limit} ky tu (con lai: {remaining})"

            if remaining <= 0:
                return KeyCheckResult(
                    engine="deepl",
                    key=api_key,
                    key_index=key_index,
                    status=KeyCheckStatus.QUOTA_EXCEEDED,
                    message=f"Het quota - {usage_info}",
                    available_models=["default"],
                    usage_info=usage_info,
                    response_time_ms=elapsed,
                )

            return KeyCheckResult(
                engine="deepl",
                key=api_key,
                key_index=key_index,
                status=KeyCheckStatus.VALID,
                message=f"API key hop le - {usage_info}",
                available_models=["default"],
                usage_info=usage_info,
                response_time_ms=elapsed,
            )
        elif resp.status_code == 403:
            return KeyCheckResult(
                engine="deepl",
                key=api_key,
                key_index=key_index,
                status=KeyCheckStatus.INVALID,
                message="API key khong hop le",
                response_time_ms=elapsed,
            )
        elif resp.status_code == 429 or resp.status_code == 456:
            return KeyCheckResult(
                engine="deepl",
                key=api_key,
                key_index=key_index,
                status=KeyCheckStatus.QUOTA_EXCEEDED,
                message=f"Quota exceeded (HTTP {resp.status_code})",
                response_time_ms=elapsed,
            )
        else:
            return KeyCheckResult(
                engine="deepl",
                key=api_key,
                key_index=key_index,
                status=KeyCheckStatus.INVALID,
                message=f"HTTP {resp.status_code}: {resp.text[:100]}",
                response_time_ms=elapsed,
            )

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        status, message = _classify_check_error(e)
        return KeyCheckResult(
            engine="deepl",
            key=api_key,
            key_index=key_index,
            status=status,
            message=message,
            response_time_ms=elapsed,
        )


def check_groq_key(api_key: str, key_index: int) -> KeyCheckResult:
    """Validate Groq API key and load available models."""
    start = time.time()
    try:
        from groq import Groq
        client = Groq(api_key=api_key, timeout=15)

        # Step 1: List models (validates key + gets available models)
        response = client.models.list()
        models = []
        for m in response.data:
            mid = m.id.lower()
            # Filter: only text generation models, not whisper/vision-only
            if any(skip in mid for skip in ["whisper", "guard", "tool-use"]):
                continue
            models.append(m.id)
        models.sort()

        elapsed = (time.time() - start) * 1000
        return KeyCheckResult(
            engine="groq",
            key=api_key,
            key_index=key_index,
            status=KeyCheckStatus.VALID,
            message=f"API key hop le - {len(models)} models kha dung",
            available_models=models,
            response_time_ms=elapsed,
        )

    except Exception as e:
        elapsed = (time.time() - start) * 1000
        status, message = _classify_check_error(e)
        return KeyCheckResult(
            engine="groq",
            key=api_key,
            key_index=key_index,
            status=status,
            message=message,
            response_time_ms=elapsed,
        )


# Registry of check functions
KEY_CHECKERS = {
    "gemini": check_gemini_key,
    "openai": check_openai_key,
    "deepl": check_deepl_key,
    "groq": check_groq_key,
}


def check_key(engine: str, api_key: str, key_index: int = 1) -> KeyCheckResult:
    """Check a single API key for any engine."""
    checker = KEY_CHECKERS.get(engine)
    if not checker:
        return KeyCheckResult(
            engine=engine,
            key=api_key,
            key_index=key_index,
            status=KeyCheckStatus.INVALID,
            message=f"Engine '{engine}' khong duoc ho tro",
        )
    return checker(api_key, key_index)


def check_all_keys(keys_by_engine: Dict[str, List[str]]) -> List[KeyCheckResult]:
    """Check all API keys across all engines.

    Args:
        keys_by_engine: Dict mapping engine name to list of API key strings.

    Returns:
        List of KeyCheckResult for every key.
    """
    results = []
    for engine, keys in keys_by_engine.items():
        for idx, key in enumerate(keys, start=1):
            result = check_key(engine, key, key_index=idx)
            results.append(result)
            log.info(result.to_log_line())
    return results
