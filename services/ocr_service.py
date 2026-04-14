"""
OCR service using PaddleOCR or Tesseract.
"""
import os
from typing import Optional

from PySide6.QtCore import QThread, Signal

from utils.logger import log
from utils.error_handler import handle_errors


class OCRWorker(QThread):
    """Worker thread for OCR processing."""
    finished = Signal(str)  # recognized text
    error = Signal(str)
    progress = Signal(int)

    def __init__(self, image_path: str, use_gpu: bool = False,
                 luminance: int = 128, engine: str = "paddleocr", parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.use_gpu = use_gpu
        self.luminance = luminance
        self.engine = engine

    def run(self):
        try:
            self.progress.emit(10)
            if self.engine == "paddleocr":
                text = self._run_paddleocr()
            else:
                text = self._run_tesseract()
            self.progress.emit(100)
            self.finished.emit(text)
        except Exception as e:
            log.error(f"OCR error: {e}")
            self.error.emit(str(e))

    def _run_paddleocr(self) -> str:
        """Run PaddleOCR (mock if not installed)."""
        try:
            from paddleocr import PaddleOCR
            ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=self.use_gpu)
            self.progress.emit(50)
            result = ocr.ocr(self.image_path, cls=True)
            texts = []
            if result and result[0]:
                for line in result[0]:
                    texts.append(line[1][0])
            return "\n".join(texts)
        except ImportError:
            log.warning("PaddleOCR not installed, returning mock result")
            self.progress.emit(50)
            return f"[Mock OCR Result]\nSample text recognized from: {os.path.basename(self.image_path)}\nLuminance threshold: {self.luminance}\nGPU: {'Enabled' if self.use_gpu else 'Disabled'}"

    def _run_tesseract(self) -> str:
        """Run Tesseract OCR (mock if not installed)."""
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(self.image_path)
            self.progress.emit(50)
            text = pytesseract.image_to_string(img)
            return text
        except ImportError:
            log.warning("Tesseract/pytesseract not installed, returning mock result")
            self.progress.emit(50)
            return f"[Mock Tesseract Result]\nSample text from: {os.path.basename(self.image_path)}"


class OCRService:
    """OCR service for text recognition from images/video frames."""

    @staticmethod
    def create_worker(image_path: str, use_gpu: bool = False,
                      luminance: int = 128, engine: str = "paddleocr") -> OCRWorker:
        return OCRWorker(image_path, use_gpu, luminance, engine)

    @staticmethod
    def preprocess_frame(image_path: str, luminance: int = 128) -> str:
        """Preprocess image for better OCR (adjust luminance)."""
        try:
            from PIL import Image, ImageEnhance
            img = Image.open(image_path)
            factor = luminance / 128.0
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(factor)
            processed_path = image_path.rsplit(".", 1)[0] + "_processed.png"
            img.save(processed_path)
            return processed_path
        except ImportError:
            return image_path
