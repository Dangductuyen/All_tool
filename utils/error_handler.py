"""
Global error handler with detailed error reporting.
"""
import sys
import traceback
from functools import wraps
from typing import Callable, Optional

from utils.logger import log


class AppError(Exception):
    """Base application error."""
    def __init__(self, message: str, details: str = "", recoverable: bool = True):
        super().__init__(message)
        self.details = details
        self.recoverable = recoverable


class ServiceError(AppError):
    """Error in a service (TTS, OCR, download, etc.)."""
    pass


class UIError(AppError):
    """Error in the UI layer."""
    pass


class FileError(AppError):
    """Error related to file operations."""
    pass


def handle_errors(func: Callable) -> Callable:
    """Decorator to catch and log errors in functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AppError as e:
            log.error(f"[{type(e).__name__}] {e} | Details: {e.details}")
            if not e.recoverable:
                raise
            return None
        except Exception as e:
            log.error(f"Unexpected error in {func.__name__}: {e}")
            log.debug(traceback.format_exc())
            return None
    return wrapper


def global_exception_handler(exc_type, exc_value, exc_tb):
    """Global exception handler for uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log.critical(
        f"Uncaught exception: {exc_type.__name__}: {exc_value}\n"
        f"{''.join(traceback.format_tb(exc_tb))}"
    )


# Install global exception handler
sys.excepthook = global_exception_handler


class ErrorReporter:
    """Collects and reports errors for the UI to display."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._errors = []
            cls._instance._callback: Optional[Callable] = None
        return cls._instance

    def set_callback(self, callback: Callable):
        """Set callback to be called when new error is reported."""
        self._callback = callback

    def report(self, error: str, details: str = "", level: str = "error"):
        """Report an error."""
        entry = {"error": error, "details": details, "level": level}
        self._errors.append(entry)
        log.error(f"Error reported: {error}")
        if self._callback:
            self._callback(entry)

    def get_errors(self) -> list:
        return self._errors.copy()

    def clear(self):
        self._errors.clear()
