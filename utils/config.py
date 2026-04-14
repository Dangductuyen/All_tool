"""
Configuration manager - loads/saves app settings from config.json
"""
import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "app": {
        "name": "VideoEditor Pro",
        "version": "1.0.0",
        "language": "ENG",
        "theme": "dark"
    },
    "paths": {
        "projects_dir": str(Path.home() / "VideoEditorProjects"),
        "output_dir": str(Path.home() / "VideoEditorProjects" / "output"),
        "temp_dir": str(Path.home() / "VideoEditorProjects" / "temp")
    },
    "editor": {
        "default_resolution": "1920x1080",
        "default_fps": 30,
        "auto_save": True,
        "auto_save_interval": 300
    },
    "tts": {
        "default_engine": "edge_tts",
        "default_language": "vi-VN",
        "default_speed": 1.0,
        "output_format": "mp3"
    },
    "ocr": {
        "engine": "paddleocr",
        "use_gpu": False,
        "luminance": 128
    },
    "audio": {
        "whisper_model": "tiny",
        "language": "auto",
        "use_gpu": False,
        "vad_enabled": False,
        "split_vocal": False,
        "quantize": False
    },
    "download": {
        "default_platform": "tiktok",
        "max_concurrent": 3,
        "output_format": "mp4"
    },
    "translator": {
        "default_engine": "openai",
        "source_language": "auto",
        "target_language": "vi"
    },
    "export": {
        "video_codec": "h264",
        "audio_codec": "aac",
        "quality": "high",
        "format": "mp4"
    }
}

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")


class ConfigManager:
    """Singleton config manager for app settings."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._config = {}
            cls._instance._load()
        return cls._instance

    def _load(self):
        """Load config from file, create default if not exists."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
                # Merge with defaults for any missing keys
                self._config = self._deep_merge(DEFAULT_CONFIG, self._config)
            except (json.JSONDecodeError, IOError):
                self._config = DEFAULT_CONFIG.copy()
                self.save()
        else:
            self._config = DEFAULT_CONFIG.copy()
            self.save()

        # Ensure directories exist
        for key in ["projects_dir", "output_dir", "temp_dir"]:
            path = self._config["paths"].get(key)
            if path:
                os.makedirs(path, exist_ok=True)

    def _deep_merge(self, default: dict, override: dict) -> dict:
        """Deep merge override into default."""
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def get(self, section: str, key: str = None):
        """Get config value. If key is None, return entire section."""
        if key is None:
            return self._config.get(section, {})
        return self._config.get(section, {}).get(key)

    def set(self, section: str, key: str, value):
        """Set a config value and save."""
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
        self.save()

    def save(self):
        """Save config to file."""
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    @property
    def config(self):
        return self._config
