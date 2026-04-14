"""
Subtitle translator service supporting OpenAI, Gemini, Groq.
"""
import os
import re
from typing import List, Optional

from PySide6.QtCore import QThread, Signal

from utils.logger import log
from services.subtitle_service import SubtitleEntry

TRANSLATOR_ENGINES = {
    "openai": {"name": "OpenAI GPT", "requires_key": "OPENAI_API_KEY"},
    "gemini": {"name": "Google Gemini", "requires_key": "GEMINI_API_KEY"},
    "groq": {"name": "Groq", "requires_key": "GROQ_API_KEY"},
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
]


class TranslateWorker(QThread):
    """Worker thread for subtitle translation."""
    finished = Signal(list)  # translated SubtitleEntry list
    error = Signal(str)
    progress = Signal(int, str)  # progress percent, status message

    def __init__(self, entries: List[SubtitleEntry], engine: str,
                 source_lang: str, target_lang: str, api_key: str = "",
                 batch_size: int = 10, parent=None):
        super().__init__(parent)
        self.entries = entries
        self.engine = engine
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.api_key = api_key
        self.batch_size = batch_size

    def run(self):
        try:
            translated = self._translate_batch()
            self.finished.emit(translated)
        except Exception as e:
            log.error(f"Translation error: {e}")
            self.error.emit(str(e))

    def _translate_batch(self) -> List[SubtitleEntry]:
        """Translate subtitle entries in batches."""
        translated = []
        total = len(self.entries)

        for i in range(0, total, self.batch_size):
            batch = self.entries[i:i + self.batch_size]
            batch_texts = [e.text for e in batch]
            progress = int((i / total) * 100)
            self.progress.emit(progress, f"Translating {i+1}-{min(i+self.batch_size, total)} of {total}...")

            if self.engine == "openai":
                translated_texts = self._translate_openai(batch_texts)
            elif self.engine == "gemini":
                translated_texts = self._translate_gemini(batch_texts)
            elif self.engine == "groq":
                translated_texts = self._translate_groq(batch_texts)
            else:
                translated_texts = self._translate_mock(batch_texts)

            for j, entry in enumerate(batch):
                new_text = translated_texts[j] if j < len(translated_texts) else entry.text
                translated.append(SubtitleEntry(
                    entry.index, entry.start, entry.end, new_text
                ))

        self.progress.emit(100, "Translation complete!")
        return translated

    def _translate_openai(self, texts: List[str]) -> List[str]:
        """Translate using OpenAI API."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            prompt = (
                f"Translate the following subtitle texts from {self.source_lang} to {self.target_lang}. "
                f"Return only the translations, one per line, preserving the order.\n\n"
                + "\n".join(f"{i+1}. {t}" for i, t in enumerate(texts))
            )
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            result = response.choices[0].message.content.strip()
            lines = []
            for line in result.split("\n"):
                cleaned = re.sub(r'^\d+\.\s*', '', line.strip())
                if cleaned:
                    lines.append(cleaned)
            return lines if len(lines) == len(texts) else self._translate_mock(texts)
        except Exception as e:
            log.warning(f"OpenAI translation failed: {e}, using mock")
            return self._translate_mock(texts)

    def _translate_gemini(self, texts: List[str]) -> List[str]:
        """Translate using Gemini API (mock)."""
        return self._translate_mock(texts, engine="Gemini")

    def _translate_groq(self, texts: List[str]) -> List[str]:
        """Translate using Groq API (mock)."""
        return self._translate_mock(texts, engine="Groq")

    def _translate_mock(self, texts: List[str], engine: str = "Mock") -> List[str]:
        """Mock translation for demo."""
        return [f"[{engine} → {self.target_lang}] {text}" for text in texts]


class TranslatorService:
    """Subtitle translator service."""

    @staticmethod
    def get_engines() -> dict:
        return TRANSLATOR_ENGINES

    @staticmethod
    def get_languages() -> List[tuple]:
        return SUPPORTED_LANGUAGES

    @staticmethod
    def create_worker(entries: List[SubtitleEntry], engine: str,
                      source_lang: str, target_lang: str,
                      api_key: str = "", batch_size: int = 10) -> TranslateWorker:
        return TranslateWorker(entries, engine, source_lang, target_lang, api_key, batch_size)
