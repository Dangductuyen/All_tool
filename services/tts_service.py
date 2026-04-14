"""
Text-to-Speech service supporting multiple engines.
Engines: Edge TTS, OpenAI TTS, Vbee, Minimax (mock for API-based)
"""
import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

from PySide6.QtCore import QObject, Signal, QThread

from utils.logger import log
from utils.error_handler import handle_errors

# Voice data for different engines
EDGE_TTS_VOICES = [
    {"name": "vi-VN-HoaiMyNeural", "engine": "edge_tts", "lang": "vi-VN", "gender": "female", "tags": ["female", "natural"]},
    {"name": "vi-VN-NamMinhNeural", "engine": "edge_tts", "lang": "vi-VN", "gender": "male", "tags": ["male", "natural"]},
    {"name": "en-US-JennyNeural", "engine": "edge_tts", "lang": "en-US", "gender": "female", "tags": ["female", "natural"]},
    {"name": "en-US-GuyNeural", "engine": "edge_tts", "lang": "en-US", "gender": "male", "tags": ["male", "natural"]},
    {"name": "en-US-AriaNeural", "engine": "edge_tts", "lang": "en-US", "gender": "female", "tags": ["female", "natural"]},
    {"name": "ja-JP-NanamiNeural", "engine": "edge_tts", "lang": "ja-JP", "gender": "female", "tags": ["female", "natural"]},
    {"name": "ko-KR-SunHiNeural", "engine": "edge_tts", "lang": "ko-KR", "gender": "female", "tags": ["female", "natural"]},
    {"name": "zh-CN-XiaoxiaoNeural", "engine": "edge_tts", "lang": "zh-CN", "gender": "female", "tags": ["female", "natural"]},
    {"name": "zh-CN-YunxiNeural", "engine": "edge_tts", "lang": "zh-CN", "gender": "male", "tags": ["male", "natural"]},
    {"name": "fr-FR-DeniseNeural", "engine": "edge_tts", "lang": "fr-FR", "gender": "female", "tags": ["female", "natural"]},
    {"name": "de-DE-KatjaNeural", "engine": "edge_tts", "lang": "de-DE", "gender": "female", "tags": ["female", "natural"]},
    {"name": "es-ES-ElviraNeural", "engine": "edge_tts", "lang": "es-ES", "gender": "female", "tags": ["female", "natural"]},
    {"name": "pt-BR-FranciscaNeural", "engine": "edge_tts", "lang": "pt-BR", "gender": "female", "tags": ["female", "natural"]},
    {"name": "th-TH-PremwadeeNeural", "engine": "edge_tts", "lang": "th-TH", "gender": "female", "tags": ["female", "natural"]},
    {"name": "id-ID-GadisNeural", "engine": "edge_tts", "lang": "id-ID", "gender": "female", "tags": ["female", "natural"]},
]

OPENAI_VOICES = [
    {"name": "alloy", "engine": "openai", "lang": "multi", "gender": "neutral", "tags": ["neutral", "natural"]},
    {"name": "echo", "engine": "openai", "lang": "multi", "gender": "male", "tags": ["male", "natural"]},
    {"name": "fable", "engine": "openai", "lang": "multi", "gender": "neutral", "tags": ["neutral", "storytelling"]},
    {"name": "onyx", "engine": "openai", "lang": "multi", "gender": "male", "tags": ["male", "deep"]},
    {"name": "nova", "engine": "openai", "lang": "multi", "gender": "female", "tags": ["female", "natural"]},
    {"name": "shimmer", "engine": "openai", "lang": "multi", "gender": "female", "tags": ["female", "soft"]},
]

VBEE_VOICES = [
    {"name": "hn_female_ngochuyen_news_48k", "engine": "vbee", "lang": "vi-VN", "gender": "female", "tags": ["female", "news"]},
    {"name": "hn_male_manhdung_news_48k", "engine": "vbee", "lang": "vi-VN", "gender": "male", "tags": ["male", "news"]},
    {"name": "sg_female_thaotrinh_dial_48k", "engine": "vbee", "lang": "vi-VN", "gender": "female", "tags": ["female", "southern"]},
    {"name": "hn_female_thutrang_dial_48k", "engine": "vbee", "lang": "vi-VN", "gender": "female", "tags": ["female", "tiktok"]},
]

MINIMAX_VOICES = [
    {"name": "male-qn-qingse", "engine": "minimax", "lang": "zh-CN", "gender": "male", "tags": ["male", "natural"]},
    {"name": "female-shaonv", "engine": "minimax", "lang": "zh-CN", "gender": "female", "tags": ["female", "young"]},
    {"name": "female-yujie", "engine": "minimax", "lang": "zh-CN", "gender": "female", "tags": ["female", "mature"]},
    {"name": "presenter_male", "engine": "minimax", "lang": "zh-CN", "gender": "male", "tags": ["male", "presenter"]},
]

ALL_VOICES = EDGE_TTS_VOICES + OPENAI_VOICES + VBEE_VOICES + MINIMAX_VOICES

LANGUAGES = [
    ("vi-VN", "Vietnamese"),
    ("en-US", "English (US)"),
    ("ja-JP", "Japanese"),
    ("ko-KR", "Korean"),
    ("zh-CN", "Chinese (Simplified)"),
    ("fr-FR", "French"),
    ("de-DE", "German"),
    ("es-ES", "Spanish"),
    ("pt-BR", "Portuguese (Brazil)"),
    ("th-TH", "Thai"),
    ("id-ID", "Indonesian"),
    ("multi", "Multilingual"),
]

ENGINES = ["edge_tts", "openai", "vbee", "minimax"]


class TTSWorker(QThread):
    """Worker thread for TTS generation."""
    finished = Signal(str)  # output file path
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, engine: str, voice: str, text: str, speed: float,
                 output_path: str, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.voice = voice
        self.text = text
        self.speed = speed
        self.output_path = output_path

    def run(self):
        try:
            if self.engine == "edge_tts":
                self._generate_edge_tts()
            elif self.engine == "openai":
                self._generate_mock("OpenAI TTS")
            elif self.engine == "vbee":
                self._generate_mock("Vbee TTS")
            elif self.engine == "minimax":
                self._generate_mock("Minimax TTS")
            else:
                self.error.emit(f"Unknown engine: {self.engine}")
                return
            self.finished.emit(self.output_path)
        except Exception as e:
            log.error(f"TTS generation error: {e}")
            self.error.emit(str(e))

    def _generate_edge_tts(self):
        """Generate speech using Edge TTS."""
        try:
            import edge_tts
            self.progress.emit(20)
            rate_str = f"+{int((self.speed - 1) * 100)}%" if self.speed >= 1 else f"{int((self.speed - 1) * 100)}%"
            communicate = edge_tts.Communicate(
                self.text, self.voice, rate=rate_str
            )
            self.progress.emit(50)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(communicate.save(self.output_path))
            loop.close()
            self.progress.emit(100)
        except ImportError:
            self._generate_mock("Edge TTS (mock - install edge-tts)")
        except Exception as e:
            self.error.emit(f"Edge TTS error: {e}")

    def _generate_mock(self, engine_name: str):
        """Mock TTS generation - creates a silent audio file placeholder."""
        self.progress.emit(30)
        import struct
        import wave
        # Generate a short silent WAV file as placeholder
        duration = min(len(self.text) * 0.05, 10.0)
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        out_path = self.output_path
        if not out_path.endswith(".wav"):
            out_path = self.output_path.rsplit(".", 1)[0] + ".wav"
        with wave.open(out_path, "w") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            for _ in range(n_samples):
                wav_file.writeframes(struct.pack("<h", 0))
        self.output_path = out_path
        self.progress.emit(100)
        log.info(f"[{engine_name}] Mock audio generated: {out_path}")


class TTSService:
    """TTS service providing voice listing and generation."""

    @staticmethod
    def get_voices(engine: str = None, language: str = None, tag: str = None) -> List[dict]:
        """Filter voices by engine, language, and/or tag."""
        voices = ALL_VOICES
        if engine:
            voices = [v for v in voices if v["engine"] == engine]
        if language:
            voices = [v for v in voices if v["lang"] == language or v["lang"] == "multi"]
        if tag:
            voices = [v for v in voices if tag.lower() in [t.lower() for t in v["tags"]]]
        return voices

    @staticmethod
    def get_languages() -> List[tuple]:
        return LANGUAGES

    @staticmethod
    def get_engines() -> List[str]:
        return ENGINES

    @staticmethod
    def create_worker(engine: str, voice: str, text: str, speed: float,
                      output_dir: str) -> TTSWorker:
        """Create a TTS worker thread."""
        ext = "mp3" if engine == "edge_tts" else "wav"
        filename = f"tts_{engine}_{voice.replace('-', '_')}_{int(asyncio.get_event_loop().time() if False else __import__('time').time())}.{ext}"
        output_path = os.path.join(output_dir, filename)
        return TTSWorker(engine, voice, text, speed, output_path)
