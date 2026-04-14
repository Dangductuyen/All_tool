"""
SRT Translator Service - Multi-AI translation engine with comprehensive error handling.

Supports: Gemini (Google), OpenAI (GPT), DeepL, Groq (LLaMA/Mixtral)

Features:
- Smart Auto Mode: auto-validate keys, load models, select best model
- Multiple API key management with auto-rotation
- Retry with exponential backoff
- Auto fallback: model A -> model B -> model C
- Detailed error reporting (401, 403, 404, 429, network, timeout)
- Batch processing with configurable size
- Multi-threaded translation
- Rate limiting
- Translation cache
"""
import json
import os
import re
import time
import hashlib
import threading
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Tuple, Callable
from dataclasses import dataclass, field
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PySide6.QtCore import QThread, Signal, QObject

from utils.logger import log
from services.subtitle_service import SubtitleEntry


# ============================================================
# Constants & Configuration
# ============================================================

API_KEY_LINKS = {
    "gemini": "https://ai.google.dev/",
    "openai": "https://platform.openai.com/api-keys",
    "deepl": "https://www.deepl.com/pro-api",
    "groq": "https://console.groq.com/keys",
}

TRANSLATOR_ENGINES = {
    "gemini": {"name": "Gemini (Google)", "requires_key": "GEMINI_API_KEY"},
    "openai": {"name": "OpenAI (GPT)", "requires_key": "OPENAI_API_KEY"},
    "deepl": {"name": "DeepL", "requires_key": "DEEPL_API_KEY"},
    "groq": {"name": "Groq (LLaMA/Mixtral)", "requires_key": "GROQ_API_KEY"},
}

DEFAULT_MODELS = {
    "gemini": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
    "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
    "deepl": ["default"],
    "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "gemma2-9b-it"],
}

SUPPORTED_LANGUAGES = [
    ("auto", "Auto Detect"),
    ("en", "English"),
    ("vi", "Vietnamese"),
    ("zh", "Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
    ("fr", "French"),
    ("de", "German"),
    ("es", "Spanish"),
    ("pt", "Portuguese"),
    ("th", "Thai"),
    ("id", "Indonesian"),
    ("ru", "Russian"),
    ("ar", "Arabic"),
    ("it", "Italian"),
    ("nl", "Dutch"),
    ("pl", "Polish"),
    ("tr", "Turkish"),
]

DEEPL_LANG_MAP = {
    "en": "EN", "vi": "VI", "zh": "ZH", "ja": "JA", "ko": "KO",
    "fr": "FR", "de": "DE", "es": "ES", "pt": "PT-BR", "th": "TH",
    "id": "ID", "ru": "RU", "ar": "AR", "it": "IT", "nl": "NL",
    "pl": "PL", "tr": "TR",
}

MAX_RETRY = 5
API_KEY_FILE = os.path.join(str(Path.home()), ".srt_translator_keys.json")


# ============================================================
# Error Types
# ============================================================

class TranslationErrorCode(Enum):
    AUTH_INVALID = 401
    NO_PERMISSION = 403
    MODEL_NOT_FOUND = 404
    QUOTA_EXCEEDED = 429
    NETWORK_ERROR = 0
    TIMEOUT = 408
    UNKNOWN = 500


@dataclass
class TranslationError:
    """Structured translation error with detailed info."""
    code: TranslationErrorCode
    message: str
    details: str = ""
    engine: str = ""
    model: str = ""
    block_id: int = 0
    timestamp: str = ""
    raw_error: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S")

    @property
    def user_message(self) -> str:
        messages = {
            TranslationErrorCode.AUTH_INVALID: "API key khong hop le hoac da bi thu hoi",
            TranslationErrorCode.NO_PERMISSION: "API key khong co quyen truy cap model nay",
            TranslationErrorCode.MODEL_NOT_FOUND: "Model khong ton tai hoac khong ho tro API hien tai",
            TranslationErrorCode.QUOTA_EXCEEDED: "Da vuot quota hoac rate limit",
            TranslationErrorCode.NETWORK_ERROR: "Khong the ket noi toi server API",
            TranslationErrorCode.TIMEOUT: "Request timeout, thu lai",
            TranslationErrorCode.UNKNOWN: f"Loi khong xac dinh: {self.raw_error}",
        }
        return messages.get(self.code, self.message)

    def to_log_line(self) -> str:
        status = f"ERROR {self.code.value} ({self.user_message})"
        return f"[{self.timestamp}] [{self.engine}] [{self.model}] Block {self.block_id} -> {status}"


def classify_error(exception: Exception, engine: str = "", model: str = "",
                   block_id: int = 0) -> TranslationError:
    """Classify an exception into a structured TranslationError."""
    raw = str(exception)
    err_lower = raw.lower()

    # Check HTTP status codes
    status_code = None
    if hasattr(exception, 'status_code'):
        status_code = exception.status_code
    elif hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
        status_code = exception.response.status_code
    else:
        # Try to extract from error message
        for code_str in ['401', '403', '404', '429', '408']:
            if code_str in raw:
                status_code = int(code_str)
                break

    if status_code == 401 or 'unauthorized' in err_lower or 'invalid api key' in err_lower or 'invalid_api_key' in err_lower:
        code = TranslationErrorCode.AUTH_INVALID
    elif status_code == 403 or 'forbidden' in err_lower or 'permission' in err_lower:
        code = TranslationErrorCode.NO_PERMISSION
    elif status_code == 404 or 'not found' in err_lower or 'model_not_found' in err_lower or 'does not exist' in err_lower:
        code = TranslationErrorCode.MODEL_NOT_FOUND
    elif status_code == 429 or 'rate limit' in err_lower or 'quota' in err_lower or 'too many' in err_lower:
        code = TranslationErrorCode.QUOTA_EXCEEDED
    elif 'timeout' in err_lower or 'timed out' in err_lower or status_code == 408:
        code = TranslationErrorCode.TIMEOUT
    elif 'connection' in err_lower or 'network' in err_lower or 'dns' in err_lower or 'unreachable' in err_lower:
        code = TranslationErrorCode.NETWORK_ERROR
    else:
        code = TranslationErrorCode.UNKNOWN

    return TranslationError(
        code=code,
        message=raw[:200],
        details=raw,
        engine=engine,
        model=model,
        block_id=block_id,
        raw_error=raw,
    )


# ============================================================
# API Key Manager
# ============================================================

class KeyStatus(Enum):
    VALID = "valid"
    INVALID = "invalid"
    QUOTA_EXCEEDED = "quota_exceeded"
    UNCHECKED = "unchecked"


@dataclass
class APIKeyEntry:
    key: str
    status: KeyStatus = KeyStatus.UNCHECKED
    last_used: float = 0.0
    error_count: int = 0
    last_error: str = ""


class APIKeyManager:
    """Manages multiple API keys per engine with rotation and validation."""

    def __init__(self):
        self._keys: Dict[str, List[APIKeyEntry]] = {
            "gemini": [],
            "openai": [],
            "deepl": [],
            "groq": [],
        }
        self._lock = threading.Lock()
        self.load_keys()

    def add_key(self, engine: str, key: str) -> bool:
        """Add a new API key for an engine."""
        with self._lock:
            if engine not in self._keys:
                return False
            # Check for duplicate
            for entry in self._keys[engine]:
                if entry.key == key:
                    return False
            self._keys[engine].append(APIKeyEntry(key=key))
            self.save_keys()
            return True

    def remove_key(self, engine: str, key: str) -> bool:
        """Remove an API key."""
        with self._lock:
            if engine not in self._keys:
                return False
            self._keys[engine] = [e for e in self._keys[engine] if e.key != key]
            self.save_keys()
            return True

    def get_keys(self, engine: str) -> List[APIKeyEntry]:
        """Get all keys for an engine."""
        with self._lock:
            return list(self._keys.get(engine, []))

    def get_best_key(self, engine: str) -> Optional[str]:
        """Get the best available key (valid, least recently used)."""
        with self._lock:
            keys = self._keys.get(engine, [])
            if not keys:
                return None
            # Prefer valid keys, then unchecked, then quota_exceeded (might have reset)
            priority = {KeyStatus.VALID: 0, KeyStatus.UNCHECKED: 1, KeyStatus.QUOTA_EXCEEDED: 2}
            valid_keys = [k for k in keys if k.status != KeyStatus.INVALID]
            if not valid_keys:
                # All invalid, try the first one anyway
                return keys[0].key
            valid_keys.sort(key=lambda k: (priority.get(k.status, 3), k.last_used))
            return valid_keys[0].key

    def rotate_key(self, engine: str, failed_key: str, error: TranslationError) -> Optional[str]:
        """Mark a key as failed and rotate to next available key."""
        with self._lock:
            keys = self._keys.get(engine, [])
            for entry in keys:
                if entry.key == failed_key:
                    entry.error_count += 1
                    entry.last_error = error.user_message
                    if error.code == TranslationErrorCode.AUTH_INVALID:
                        entry.status = KeyStatus.INVALID
                    elif error.code == TranslationErrorCode.QUOTA_EXCEEDED:
                        entry.status = KeyStatus.QUOTA_EXCEEDED
                    break
            self.save_keys()

        return self.get_best_key(engine)

    def mark_key_valid(self, engine: str, key: str):
        """Mark a key as valid after successful use."""
        with self._lock:
            for entry in self._keys.get(engine, []):
                if entry.key == key:
                    entry.status = KeyStatus.VALID
                    entry.last_used = time.time()
                    entry.error_count = 0
                    break
            self.save_keys()

    def update_key_status(self, engine: str, key: str, status: KeyStatus,
                          error_msg: str = ""):
        """Update key status."""
        with self._lock:
            for entry in self._keys.get(engine, []):
                if entry.key == key:
                    entry.status = status
                    entry.last_error = error_msg
                    break
            self.save_keys()

    def save_keys(self):
        """Save keys to local file."""
        try:
            data = {}
            for engine, entries in self._keys.items():
                data[engine] = [
                    {
                        "key": e.key,
                        "status": e.status.value,
                        "error_count": e.error_count,
                        "last_error": e.last_error,
                    }
                    for e in entries
                ]
            with open(API_KEY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error(f"Failed to save API keys: {e}")

    def load_keys(self):
        """Load keys from local file."""
        if not os.path.exists(API_KEY_FILE):
            return
        try:
            with open(API_KEY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for engine, entries in data.items():
                if engine in self._keys:
                    self._keys[engine] = []
                    for entry_data in entries:
                        status_val = entry_data.get("status", "unchecked")
                        try:
                            status = KeyStatus(status_val)
                        except ValueError:
                            status = KeyStatus.UNCHECKED
                        self._keys[engine].append(APIKeyEntry(
                            key=entry_data["key"],
                            status=status,
                            error_count=entry_data.get("error_count", 0),
                            last_error=entry_data.get("last_error", ""),
                        ))
        except Exception as e:
            log.error(f"Failed to load API keys: {e}")


# ============================================================
# Translation Cache
# ============================================================

class TranslationCache:
    """Simple in-memory cache for translations."""

    def __init__(self, max_size: int = 10000):
        self._cache: Dict[str, str] = {}
        self._max_size = max_size
        self._lock = threading.Lock()

    def _make_key(self, text: str, engine: str, model: str,
                  source_lang: str, target_lang: str) -> str:
        raw = f"{engine}:{model}:{source_lang}:{target_lang}:{text}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, text: str, engine: str, model: str,
            source_lang: str, target_lang: str) -> Optional[str]:
        key = self._make_key(text, engine, model, source_lang, target_lang)
        with self._lock:
            return self._cache.get(key)

    def put(self, text: str, translation: str, engine: str, model: str,
            source_lang: str, target_lang: str):
        key = self._make_key(text, engine, model, source_lang, target_lang)
        with self._lock:
            if len(self._cache) >= self._max_size:
                # Remove oldest 10%
                keys_to_remove = list(self._cache.keys())[:self._max_size // 10]
                for k in keys_to_remove:
                    del self._cache[k]
            self._cache[key] = translation

    def clear(self):
        with self._lock:
            self._cache.clear()


# ============================================================
# Rate Limiter
# ============================================================

class RateLimiter:
    """Token bucket rate limiter per engine."""

    def __init__(self, requests_per_minute: int = 60):
        self._rpm = requests_per_minute
        self._tokens = requests_per_minute
        self._last_refill = time.time()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = 30.0) -> bool:
        """Wait for a token. Returns False if timed out."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            with self._lock:
                now = time.time()
                elapsed = now - self._last_refill
                self._tokens = min(self._rpm, self._tokens + elapsed * (self._rpm / 60.0))
                self._last_refill = now
                if self._tokens >= 1:
                    self._tokens -= 1
                    return True
            time.sleep(0.1)
        return False


# ============================================================
# AI Translation Clients
# ============================================================

def _build_translate_prompt(texts: List[str], source_lang: str,
                            target_lang: str) -> str:
    """Build translation prompt for LLM-based engines."""
    numbered = "\n".join(f"[{i+1}] {t}" for i, t in enumerate(texts))
    return (
        f"Translate the following subtitle lines from {source_lang} to {target_lang}.\n"
        f"IMPORTANT RULES:\n"
        f"- Return EXACTLY {len(texts)} lines\n"
        f"- Each line starts with [number] matching the input\n"
        f"- Do NOT add or remove any lines\n"
        f"- Do NOT include the original text\n"
        f"- Keep the translation natural and concise for subtitles\n"
        f"- Preserve any formatting or special characters\n\n"
        f"{numbered}"
    )


def _parse_translate_response(response_text: str, count: int) -> List[str]:
    """Parse numbered translation response into list of strings."""
    lines = []
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Remove [N] or N. prefix
        cleaned = re.sub(r'^\[?\d+\]?\s*\.?\s*', '', line)
        if cleaned:
            lines.append(cleaned)
    # If count doesn't match, return what we have
    return lines


def translate_gemini(texts: List[str], api_key: str, model: str,
                     source_lang: str, target_lang: str,
                     timeout: float = 30.0) -> List[str]:
    """Translate using Google Gemini API."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")

    genai.configure(api_key=api_key)
    gen_model = genai.GenerativeModel(model)
    prompt = _build_translate_prompt(texts, source_lang, target_lang)

    response = gen_model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,
            max_output_tokens=4096,
        ),
        request_options={"timeout": timeout},
    )

    if not response.text:
        raise RuntimeError("Gemini returned empty response")

    return _parse_translate_response(response.text, len(texts))


def translate_openai(texts: List[str], api_key: str, model: str,
                     source_lang: str, target_lang: str,
                     timeout: float = 30.0) -> List[str]:
    """Translate using OpenAI API."""
    try:
        import openai
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")

    client = openai.OpenAI(api_key=api_key, timeout=timeout)
    prompt = _build_translate_prompt(texts, source_lang, target_lang)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a professional subtitle translator. Follow the instructions exactly."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    result = response.choices[0].message.content
    if not result:
        raise RuntimeError("OpenAI returned empty response")

    return _parse_translate_response(result.strip(), len(texts))


def translate_deepl(texts: List[str], api_key: str, model: str,
                    source_lang: str, target_lang: str,
                    timeout: float = 30.0) -> List[str]:
    """Translate using DeepL API."""
    try:
        import httpx
    except ImportError:
        raise RuntimeError("httpx package not installed. Run: pip install httpx")

    # Determine if free or pro key
    base_url = "https://api-free.deepl.com"
    if not api_key.endswith(":fx"):
        base_url = "https://api.deepl.com"

    target = DEEPL_LANG_MAP.get(target_lang, target_lang.upper())
    source = DEEPL_LANG_MAP.get(source_lang, None) if source_lang != "auto" else None

    payload = {
        "text": texts,
        "target_lang": target,
    }
    if source:
        payload["source_lang"] = source

    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{base_url}/v2/translate",
            headers={
                "Authorization": f"DeepL-Auth-Key {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

        if response.status_code == 401:
            raise RuntimeError("401 Unauthorized: Invalid DeepL API key")
        elif response.status_code == 403:
            raise RuntimeError("403 Forbidden: DeepL API key does not have permission")
        elif response.status_code == 429:
            raise RuntimeError("429 Too Many Requests: DeepL rate limit exceeded")
        elif response.status_code == 456:
            raise RuntimeError("429 Quota exceeded: DeepL character quota reached")
        elif response.status_code != 200:
            raise RuntimeError(f"{response.status_code}: {response.text}")

        data = response.json()
        translations = data.get("translations", [])
        return [t.get("text", "") for t in translations]


def translate_groq(texts: List[str], api_key: str, model: str,
                   source_lang: str, target_lang: str,
                   timeout: float = 30.0) -> List[str]:
    """Translate using Groq API."""
    try:
        from groq import Groq
    except ImportError:
        raise RuntimeError("groq package not installed. Run: pip install groq")

    client = Groq(api_key=api_key, timeout=timeout)
    prompt = _build_translate_prompt(texts, source_lang, target_lang)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a professional subtitle translator. Follow the instructions exactly."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    result = response.choices[0].message.content
    if not result:
        raise RuntimeError("Groq returned empty response")

    return _parse_translate_response(result.strip(), len(texts))


TRANSLATE_FUNCTIONS = {
    "gemini": translate_gemini,
    "openai": translate_openai,
    "deepl": translate_deepl,
    "groq": translate_groq,
}


# ============================================================
# Model Loader
# ============================================================

def load_models_gemini(api_key: str) -> List[str]:
    """Load available Gemini models."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        models = []
        for m in genai.list_models():
            if "generateContent" in (m.supported_generation_methods or []):
                name = m.name.replace("models/", "")
                models.append(name)
        return models if models else DEFAULT_MODELS["gemini"]
    except Exception as e:
        log.warning(f"Failed to load Gemini models: {e}")
        return DEFAULT_MODELS["gemini"]


def load_models_openai(api_key: str) -> List[str]:
    """Load available OpenAI models."""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.models.list()
        models = []
        for m in response.data:
            if "gpt" in m.id.lower():
                models.append(m.id)
        models.sort()
        return models if models else DEFAULT_MODELS["openai"]
    except Exception as e:
        log.warning(f"Failed to load OpenAI models: {e}")
        return DEFAULT_MODELS["openai"]


def load_models_deepl(api_key: str) -> List[str]:
    """DeepL doesn't have model selection."""
    return ["default"]


def load_models_groq(api_key: str) -> List[str]:
    """Load available Groq models."""
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        response = client.models.list()
        models = []
        for m in response.data:
            models.append(m.id)
        # Filter for known good translation models
        preferred = ["mixtral", "llama", "gemma"]
        filtered = [m for m in models if any(p in m.lower() for p in preferred)]
        return filtered if filtered else models if models else DEFAULT_MODELS["groq"]
    except Exception as e:
        log.warning(f"Failed to load Groq models: {e}")
        return DEFAULT_MODELS["groq"]


MODEL_LOADERS = {
    "gemini": load_models_gemini,
    "openai": load_models_openai,
    "deepl": load_models_deepl,
    "groq": load_models_groq,
}


# ============================================================
# API Key Validator
# ============================================================

def validate_api_key(engine: str, api_key: str) -> Tuple[bool, str]:
    """Validate an API key by making a lightweight API call.
    Returns (is_valid, message)."""
    try:
        if engine == "gemini":
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            list(genai.list_models())
            return True, "API key hop le"

        elif engine == "openai":
            import openai
            client = openai.OpenAI(api_key=api_key)
            client.models.list()
            return True, "API key hop le"

        elif engine == "deepl":
            import httpx
            base_url = "https://api-free.deepl.com"
            if not api_key.endswith(":fx"):
                base_url = "https://api.deepl.com"
            with httpx.Client(timeout=10) as client:
                resp = client.get(
                    f"{base_url}/v2/usage",
                    headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    used = data.get("character_count", 0)
                    limit = data.get("character_limit", 0)
                    return True, f"Hop le - Da dung {used}/{limit} ky tu"
                elif resp.status_code == 403:
                    return False, "API key khong hop le"
                else:
                    return False, f"Loi {resp.status_code}"

        elif engine == "groq":
            from groq import Groq
            client = Groq(api_key=api_key)
            client.models.list()
            return True, "API key hop le"

        return False, "Engine khong duoc ho tro"

    except Exception as e:
        err = classify_error(e, engine=engine)
        return False, err.user_message


# ============================================================
# Translation Worker (QThread)
# ============================================================

@dataclass
class TranslationTask:
    """A single translation task for a batch of subtitle entries."""
    batch_index: int
    entries: List[SubtitleEntry]
    retry_count: int = 0
    failed_count: int = 0


class TranslateWorker(QThread):
    """Worker thread for subtitle translation with full error handling and smart fallback."""

    # Signals
    finished = Signal(list)
    error = Signal(str)
    progress = Signal(int, str)
    log_message = Signal(str)
    block_error = Signal(int, str, str)  # block_id, error_code, error_message
    model_changed = Signal(str)  # emitted when auto-fallback changes model

    def __init__(self, entries: List[SubtitleEntry], engine: str,
                 model: str, source_lang: str, target_lang: str,
                 key_manager: APIKeyManager, batch_size: int = 10,
                 num_threads: int = 1, ai_manager=None, parent=None):
        super().__init__(parent)
        self.entries = entries
        self.engine = engine
        self.model = model
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.key_manager = key_manager
        self.ai_manager = ai_manager  # Optional AIManager for smart fallback
        self.batch_size = batch_size
        self.num_threads = max(1, min(num_threads, 20))
        self._stop_flag = False
        self._cache = TranslationCache()
        self._rate_limiter = RateLimiter(requests_per_minute=60)
        self._translated: Dict[int, SubtitleEntry] = {}
        self._lock = threading.Lock()
        self._completed_batches = 0
        self._total_batches = 0

    def stop(self):
        """Request translation stop."""
        self._stop_flag = True

    def run(self):
        """Main translation loop."""
        try:
            self._log(f"Bat dau dich {len(self.entries)} blocks voi {self.engine}/{self.model}")
            self._log(f"Batch size: {self.batch_size}, Threads: {self.num_threads}")

            # Create batches
            batches: List[TranslationTask] = []
            for i in range(0, len(self.entries), self.batch_size):
                batch_entries = self.entries[i:i + self.batch_size]
                batches.append(TranslationTask(
                    batch_index=i // self.batch_size,
                    entries=batch_entries,
                ))
            self._total_batches = len(batches)

            if self.num_threads <= 1:
                # Single-threaded
                for task in batches:
                    if self._stop_flag:
                        self._log("Dich bi dung boi nguoi dung")
                        break
                    self._translate_batch(task)
            else:
                # Multi-threaded
                with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
                    futures = {executor.submit(self._translate_batch, task): task
                               for task in batches}
                    for future in as_completed(futures):
                        if self._stop_flag:
                            break
                        try:
                            future.result()
                        except Exception as e:
                            task = futures[future]
                            self._log(f"Batch {task.batch_index} that bai: {e}")

            # Assemble results in order
            result = []
            for entry in self.entries:
                if entry.index in self._translated:
                    result.append(self._translated[entry.index])
                else:
                    result.append(entry)  # Keep original if translation failed

            self._log(f"Hoan thanh! Da dich {len(self._translated)}/{len(self.entries)} blocks")
            self.finished.emit(result)

        except Exception as e:
            log.error(f"Translation worker error: {e}")
            self.error.emit(str(e))

    def _translate_batch(self, task: TranslationTask):
        """Translate a single batch with smart retry, key rotation, and model fallback."""
        if self._stop_flag:
            return

        entries = task.entries
        texts = [e.text for e in entries]
        start_idx = task.batch_index * self.batch_size + 1
        end_idx = start_idx + len(entries) - 1

        # Check cache first
        cached_results = []
        uncached_indices = []
        for i, text in enumerate(texts):
            cached = self._cache.get(text, self.engine, self.model,
                                     self.source_lang, self.target_lang)
            if cached:
                cached_results.append((i, cached))
            else:
                uncached_indices.append(i)

        if not uncached_indices:
            # All cached
            self._log(f"Blocks {start_idx}-{end_idx} -> CACHED")
            for i, cached_text in cached_results:
                entry = entries[i]
                with self._lock:
                    self._translated[entry.index] = SubtitleEntry(
                        entry.index, entry.start, entry.end, cached_text
                    )
            self._update_progress()
            return

        # Translate uncached texts
        uncached_texts = [texts[i] for i in uncached_indices]
        current_key = self.key_manager.get_best_key(self.engine)
        current_model = self.model
        retry = 0

        while retry < MAX_RETRY and not self._stop_flag:
            if not current_key:
                self._log(f"Blocks {start_idx}-{end_idx} -> ERROR: Khong co API key")
                self.block_error.emit(start_idx, "NO_KEY", "Khong co API key kha dung")
                break

            # Rate limit
            if not self._rate_limiter.acquire(timeout=30):
                self._log(f"Blocks {start_idx}-{end_idx} -> Rate limit timeout")
                continue

            try:
                translate_fn = TRANSLATE_FUNCTIONS.get(self.engine)
                if not translate_fn:
                    raise RuntimeError(f"Engine '{self.engine}' khong duoc ho tro")

                translated_texts = translate_fn(
                    uncached_texts, current_key, current_model,
                    self.source_lang, self.target_lang,
                )

                # Validate result count
                if len(translated_texts) < len(uncached_texts):
                    self._log(f"Blocks {start_idx}-{end_idx} -> WARNING: Nhan {len(translated_texts)}/{len(uncached_texts)} translations")
                    # Pad with originals
                    while len(translated_texts) < len(uncached_texts):
                        translated_texts.append(uncached_texts[len(translated_texts)])

                # Success - update cache and results
                self.key_manager.mark_key_valid(self.engine, current_key)

                for j, idx in enumerate(uncached_indices):
                    entry = entries[idx]
                    trans_text = translated_texts[j] if j < len(translated_texts) else entry.text
                    with self._lock:
                        self._translated[entry.index] = SubtitleEntry(
                            entry.index, entry.start, entry.end, trans_text
                        )
                    self._cache.put(entry.text, trans_text, self.engine,
                                    current_model, self.source_lang, self.target_lang)

                # Also store cached results
                for i, cached_text in cached_results:
                    entry = entries[i]
                    with self._lock:
                        self._translated[entry.index] = SubtitleEntry(
                            entry.index, entry.start, entry.end, cached_text
                        )

                ts = datetime.now().strftime("%H:%M:%S")
                key_idx = self._get_key_index(current_key)
                self._log(f"[{ts}] [{self.engine}] Key#{key_idx} [{current_model}] Blocks {start_idx}-{end_idx} -> SUCCESS")
                self._update_progress()
                return

            except Exception as e:
                retry += 1
                t_err = classify_error(e, self.engine, current_model, start_idx)
                key_idx = self._get_key_index(current_key)
                self._log(f"[{t_err.timestamp}] [{self.engine}] Key#{key_idx} [{current_model}] Block {start_idx} -> ERROR {t_err.code.value} ({t_err.user_message})")

                # Use AIManager for smart fallback if available
                if self.ai_manager:
                    old_key, old_model = current_key, current_model
                    fallback = self.ai_manager.handle_translation_error(
                        self.engine, t_err.code, current_key, current_model
                    )
                    new_key = fallback.get("key")
                    new_model = fallback.get("model")

                    if new_key is None and new_model is None:
                        self._log(f"  -> Khong con fallback kha dung")
                        self.block_error.emit(start_idx, str(t_err.code.value), t_err.user_message)
                        break

                    if new_key and new_key != old_key:
                        current_key = new_key
                        new_idx = self._get_key_index(new_key)
                        self._log(f"  -> Auto switch -> Key#{new_idx}")

                    if new_model and new_model != old_model:
                        current_model = new_model
                        self._log(f"  -> Auto fallback model: {old_model} -> {new_model}")
                        self.model_changed.emit(new_model)

                    # Backoff for rate-limit errors
                    if t_err.code in (TranslationErrorCode.QUOTA_EXCEEDED,
                                      TranslationErrorCode.NETWORK_ERROR,
                                      TranslationErrorCode.TIMEOUT):
                        wait_time = min(2 ** retry, 60)
                        self._log(f"  -> Doi {wait_time}s (retry {retry}/{MAX_RETRY})")
                        time.sleep(wait_time)
                else:
                    # Legacy fallback (no AIManager)
                    if t_err.code == TranslationErrorCode.AUTH_INVALID:
                        new_key = self.key_manager.rotate_key(self.engine, current_key, t_err)
                        if new_key and new_key != current_key:
                            self._log(f"  -> Rotating API key...")
                            current_key = new_key
                        else:
                            self._log(f"  -> Khong con API key kha dung")
                            self.block_error.emit(start_idx, str(t_err.code.value), t_err.user_message)
                            break

                    elif t_err.code == TranslationErrorCode.QUOTA_EXCEEDED:
                        new_key = self.key_manager.rotate_key(self.engine, current_key, t_err)
                        if new_key and new_key != current_key:
                            self._log(f"  -> Rotating API key...")
                            current_key = new_key
                        else:
                            wait_time = min(2 ** retry, 60)
                            self._log(f"  -> Rate limit, doi {wait_time}s (retry {retry}/{MAX_RETRY})")
                            time.sleep(wait_time)

                    elif t_err.code == TranslationErrorCode.MODEL_NOT_FOUND:
                        fallback_models = DEFAULT_MODELS.get(self.engine, [])
                        fallback_found = False
                        for fb_model in fallback_models:
                            if fb_model != current_model:
                                self._log(f"  -> Fallback sang model: {fb_model}")
                                current_model = fb_model
                                self.model_changed.emit(fb_model)
                                fallback_found = True
                                break
                        if not fallback_found:
                            self.block_error.emit(start_idx, str(t_err.code.value), t_err.user_message)
                            break

                    elif t_err.code in (TranslationErrorCode.NETWORK_ERROR, TranslationErrorCode.TIMEOUT):
                        wait_time = min(2 ** retry, 30)
                        self._log(f"  -> Retry sau {wait_time}s (retry {retry}/{MAX_RETRY})")
                        time.sleep(wait_time)

                    else:
                        wait_time = min(2 ** retry, 30)
                        self._log(f"  -> Retry sau {wait_time}s (retry {retry}/{MAX_RETRY})")
                        time.sleep(wait_time)

        if retry >= MAX_RETRY:
            self._log(f"Blocks {start_idx}-{end_idx} -> SKIP (that bai sau {MAX_RETRY} lan thu)")
            self.block_error.emit(start_idx, "MAX_RETRY", f"That bai sau {MAX_RETRY} lan thu")
            self._update_progress()

    def _update_progress(self):
        """Update progress signal."""
        with self._lock:
            self._completed_batches += 1
            if self._total_batches > 0:
                pct = int((self._completed_batches / self._total_batches) * 100)
            else:
                pct = 100
            translated_count = len(self._translated)

        self.progress.emit(pct, f"Da dich {translated_count}/{len(self.entries)} blocks ({pct}%)")

    def _get_key_index(self, key: str) -> int:
        """Get the display index of an API key."""
        keys = self.key_manager.get_keys(self.engine)
        for i, entry in enumerate(keys, start=1):
            if entry.key == key:
                return i
        return 0

    def _log(self, message: str):
        """Emit log message."""
        log.info(f"[Translator] {message}")
        self.log_message.emit(message)


# ============================================================
# Format Checker
# ============================================================

@dataclass
class FormatCheckResult:
    """Result of SRT format validation between input and output."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    input_block_count: int = 0
    output_block_count: int = 0
    missing_blocks: List[int] = field(default_factory=list)
    empty_blocks: List[int] = field(default_factory=list)
    timestamp_mismatches: List[int] = field(default_factory=list)


def check_srt_format(original: List[SubtitleEntry],
                     translated: List[SubtitleEntry]) -> FormatCheckResult:
    """Compare input vs output SRT format strictly."""
    result = FormatCheckResult(
        input_block_count=len(original),
        output_block_count=len(translated),
    )

    # Check block count
    if len(original) != len(translated):
        result.is_valid = False
        result.errors.append(
            f"So block khong khop: input={len(original)}, output={len(translated)}"
        )

    # Build lookup maps
    orig_map = {e.index: e for e in original}
    trans_map = {e.index: e for e in translated}

    # Check each block
    for idx, orig_entry in orig_map.items():
        if idx not in trans_map:
            result.is_valid = False
            result.missing_blocks.append(idx)
            result.errors.append(f"Block {idx}: thieu trong output")
            continue

        trans_entry = trans_map[idx]

        # Check timestamp match
        if orig_entry.start != trans_entry.start or orig_entry.end != trans_entry.end:
            result.is_valid = False
            result.timestamp_mismatches.append(idx)
            result.errors.append(
                f"Block {idx}: timestamp khong khop - "
                f"input=({orig_entry.start} --> {orig_entry.end}) "
                f"output=({trans_entry.start} --> {trans_entry.end})"
            )

        # Check empty translation
        if not trans_entry.text.strip():
            result.empty_blocks.append(idx)
            result.warnings.append(f"Block {idx}: ban dich rong")

    return result


# ============================================================
# Translator Service (Facade)
# ============================================================

class TranslatorService:
    """Main facade for the subtitle translator."""

    _key_manager: Optional[APIKeyManager] = None

    @classmethod
    def get_key_manager(cls) -> APIKeyManager:
        if cls._key_manager is None:
            cls._key_manager = APIKeyManager()
        return cls._key_manager

    @staticmethod
    def get_engines() -> dict:
        return TRANSLATOR_ENGINES

    @staticmethod
    def get_languages() -> List[tuple]:
        return SUPPORTED_LANGUAGES

    @staticmethod
    def get_api_key_link(engine: str) -> str:
        return API_KEY_LINKS.get(engine, "")

    @staticmethod
    def get_default_models(engine: str) -> List[str]:
        return DEFAULT_MODELS.get(engine, [])

    @staticmethod
    def load_models(engine: str, api_key: str) -> List[str]:
        loader = MODEL_LOADERS.get(engine)
        if loader:
            return loader(api_key)
        return DEFAULT_MODELS.get(engine, [])

    @staticmethod
    def validate_key(engine: str, api_key: str) -> Tuple[bool, str]:
        return validate_api_key(engine, api_key)

    @classmethod
    def create_worker(cls, entries: List[SubtitleEntry], engine: str,
                      model: str, source_lang: str, target_lang: str,
                      batch_size: int = 10,
                      num_threads: int = 1,
                      ai_manager=None) -> TranslateWorker:
        return TranslateWorker(
            entries=entries,
            engine=engine,
            model=model,
            source_lang=source_lang,
            target_lang=target_lang,
            key_manager=cls.get_key_manager(),
            batch_size=batch_size,
            num_threads=num_threads,
            ai_manager=ai_manager,
        )

    @staticmethod
    def check_format(original: List[SubtitleEntry],
                     translated: List[SubtitleEntry]) -> FormatCheckResult:
        return check_srt_format(original, translated)
