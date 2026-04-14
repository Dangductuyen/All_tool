"""
OCR Settings tab - configure and test OCR recognition.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QTextEdit, QGroupBox, QCheckBox, QComboBox,
    QFileDialog, QProgressBar
)
from PySide6.QtCore import Qt

from ui.widgets.animated_button import AnimatedButton
from services.ocr_service import OCRService
from utils.config import ConfigManager
from utils.logger import log


class OCRSettingTab(QWidget):
    """OCR settings and testing tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("OCR Settings")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Test Recognition
        test_group = QGroupBox("Test Recognition")
        test_layout = QVBoxLayout(test_group)

        btn_layout = QHBoxLayout()
        self.btn_load_image = AnimatedButton("Load Image", color="#4A90D9")
        self.btn_load_image.clicked.connect(self._load_image)
        btn_layout.addWidget(self.btn_load_image)

        self.btn_test = AnimatedButton("Test Recognition", color="#4AD97A",
                                       style_id="successButton")
        self.btn_test.clicked.connect(self._test_recognition)
        btn_layout.addWidget(self.btn_test)
        test_layout.addLayout(btn_layout)

        self.lbl_image = QLabel("No image loaded")
        self.lbl_image.setObjectName("subtitleLabel")
        test_layout.addWidget(self.lbl_image)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        test_layout.addWidget(self.progress)

        layout.addWidget(test_group)

        # Luminance control
        lum_group = QGroupBox("Luminance Adjustment")
        lum_layout = QVBoxLayout(lum_group)

        slider_row = QHBoxLayout()
        slider_row.addWidget(QLabel("Luminance:"))
        self.slider_luminance = QSlider(Qt.Orientation.Horizontal)
        self.slider_luminance.setMinimum(0)
        self.slider_luminance.setMaximum(255)
        self.slider_luminance.setValue(128)
        self.slider_luminance.valueChanged.connect(self._on_luminance_changed)
        slider_row.addWidget(self.slider_luminance)
        self.lbl_luminance = QLabel("128")
        self.lbl_luminance.setMinimumWidth(35)
        slider_row.addWidget(self.lbl_luminance)
        lum_layout.addLayout(slider_row)

        layout.addWidget(lum_group)

        # Output text
        output_group = QGroupBox("Recognition Output")
        output_layout = QVBoxLayout(output_group)
        self.txt_output = QTextEdit()
        self.txt_output.setPlaceholderText("Recognition results will appear here...")
        self.txt_output.setMinimumHeight(150)
        self.txt_output.setReadOnly(True)
        output_layout.addWidget(self.txt_output)
        layout.addWidget(output_group)

        # OCR Config
        config_group = QGroupBox("OCR Configuration")
        config_layout = QVBoxLayout(config_group)

        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("OCR Engine:"))
        self.cmb_engine = QComboBox()
        self.cmb_engine.addItems(["PaddleOCR", "Tesseract"])
        engine_row.addWidget(self.cmb_engine)
        config_layout.addLayout(engine_row)

        self.chk_gpu = QCheckBox("Enable GPU OCR")
        self.chk_gpu.setChecked(self.config.get("ocr", "use_gpu") or False)
        config_layout.addWidget(self.chk_gpu)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("OCR Language:"))
        self.cmb_ocr_lang = QComboBox()
        self.cmb_ocr_lang.addItems(["English", "Chinese", "Japanese", "Korean", "Vietnamese", "Multi"])
        lang_row.addWidget(self.cmb_ocr_lang)
        config_layout.addLayout(lang_row)

        self.btn_reset = QPushButton("Reset to Default")
        self.btn_reset.clicked.connect(self._reset_defaults)
        config_layout.addWidget(self.btn_reset)

        layout.addWidget(config_group)
        layout.addStretch()

        self._image_path = ""

    def _load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Image", "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff);;All Files (*)"
        )
        if file_path:
            self._image_path = file_path
            self.lbl_image.setText(f"Loaded: {file_path}")

    def _test_recognition(self):
        if not self._image_path:
            self.txt_output.setPlainText("Please load an image first.")
            return

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_test.setEnabled(False)

        engine = "paddleocr" if self.cmb_engine.currentText() == "PaddleOCR" else "tesseract"
        self._worker = OCRService.create_worker(
            self._image_path,
            use_gpu=self.chk_gpu.isChecked(),
            luminance=self.slider_luminance.value(),
            engine=engine,
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.start()

    def _on_finished(self, text: str):
        self.txt_output.setPlainText(text)
        self.progress.setVisible(False)
        self.btn_test.setEnabled(True)

    def _on_error(self, error: str):
        self.txt_output.setPlainText(f"Error: {error}")
        self.progress.setVisible(False)
        self.btn_test.setEnabled(True)

    def _on_luminance_changed(self, value: int):
        self.lbl_luminance.setText(str(value))

    def _reset_defaults(self):
        self.slider_luminance.setValue(128)
        self.chk_gpu.setChecked(False)
        self.cmb_engine.setCurrentIndex(0)
        self.cmb_ocr_lang.setCurrentIndex(0)
