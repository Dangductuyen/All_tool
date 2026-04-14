"""
Audio transcription service using Whisper (faster-whisper).
Supports V1 (Tiny), V2 (Quantize), V3 (Medium) configurations.
"""
import os
from typing import Optional, List

from PySide6.QtCore import QThread, Signal

from utils.logger import log


WHISPER_MODELS = {
    "tiny": {"name": "Tiny", "size": "~75MB", "speed": "fastest"},
    "base": {"name": "Base", "size": "~150MB", "speed": "fast"},
    "small": {"name": "Small", "size": "~500MB", "speed": "medium"},
    "medium": {"name": "Medium", "size": "~1.5GB", "speed": "slow"},
    "large-v2": {"name": "Large V2", "size": "~3GB", "speed": "slowest"},
}

AUDIO_CONFIGS = {
    "v1": {
        "name": "Audio V1",
        "model": "tiny",
        "language": "auto",
        "use_gpu": False,
        "quantize": False,
        "split_vocal": False,
        "vad": False,
    },
    "v2": {
        "name": "Audio V2",
        "model": "tiny",
        "language": "auto",
        "use_gpu": False,
        "quantize": True,
        "split_vocal": False,
        "vad": False,
    },
    "v3": {
        "name": "Audio V3",
        "model": "medium",
        "language": "auto",
        "use_gpu": True,
        "quantize": False,
        "split_vocal": True,
        "vad": True,
    },
}


class TranscriptionWorker(QThread):
    """Worker thread for audio transcription."""
    finished = Signal(list)  # list of segments
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, audio_path: str, model: str = "tiny",
                 language: str = "auto", use_gpu: bool = False,
                 quantize: bool = False, vad: bool = False,
                 split_vocal: bool = False, parent=None):
        super().__init__(parent)
        self.audio_path = audio_path
        self.model = model
        self.language = language
        self.use_gpu = use_gpu
        self.quantize = quantize
        self.vad = vad
        self.split_vocal = split_vocal

    def run(self):
        try:
            self.progress.emit(10)
            segments = self._transcribe()
            self.progress.emit(100)
            self.finished.emit(segments)
        except Exception as e:
            log.error(f"Transcription error: {e}")
            self.error.emit(str(e))

    def _transcribe(self) -> list:
        """Transcribe audio using faster-whisper or mock."""
        try:
            from faster_whisper import WhisperModel
            compute_type = "int8" if self.quantize else "float16" if self.use_gpu else "int8"
            device = "cuda" if self.use_gpu else "cpu"
            model = WhisperModel(self.model, device=device, compute_type=compute_type)
            self.progress.emit(40)
            lang = None if self.language == "auto" else self.language
            segments_gen, info = model.transcribe(
                self.audio_path,
                language=lang,
                vad_filter=self.vad,
            )
            self.progress.emit(60)
            segments = []
            for seg in segments_gen:
                segments.append({
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text.strip(),
                })
            return segments
        except ImportError:
            log.warning("faster-whisper not installed, returning mock transcription")
            self.progress.emit(50)
            return [
                {"start": 0.0, "end": 2.5, "text": "[Mock] This is a sample transcription."},
                {"start": 2.5, "end": 5.0, "text": "[Mock] Whisper model not installed."},
                {"start": 5.0, "end": 8.0, "text": "[Mock] Install faster-whisper for real transcription."},
            ]


class AudioService:
    """Audio service for transcription and vocal separation."""

    @staticmethod
    def get_models() -> dict:
        return WHISPER_MODELS

    @staticmethod
    def get_configs() -> dict:
        return AUDIO_CONFIGS

    @staticmethod
    def create_worker(audio_path: str, config: str = "v1", **overrides) -> TranscriptionWorker:
        """Create transcription worker with a predefined config."""
        cfg = AUDIO_CONFIGS.get(config, AUDIO_CONFIGS["v1"]).copy()
        cfg.update(overrides)
        return TranscriptionWorker(
            audio_path,
            model=cfg["model"],
            language=cfg["language"],
            use_gpu=cfg["use_gpu"],
            quantize=cfg["quantize"],
            vad=cfg["vad"],
            split_vocal=cfg["split_vocal"],
        )

    @staticmethod
    def segments_to_srt(segments: list) -> str:
        """Convert transcription segments to SRT format."""
        lines = []
        for i, seg in enumerate(segments, 1):
            start = AudioService._format_time(seg["start"])
            end = AudioService._format_time(seg["end"])
            lines.append(f"{i}")
            lines.append(f"{start} --> {end}")
            lines.append(seg["text"])
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds to SRT time format."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
