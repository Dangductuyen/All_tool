"""
Audio panel with V1, V2, V3 configurations for Whisper transcription.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QCheckBox, QGroupBox, QTabWidget, QTextEdit,
    QFileDialog, QProgressBar
)
from PySide6.QtCore import Qt

from ui.widgets.animated_button import AnimatedButton
from services.audio_service import AudioService, AUDIO_CONFIGS
from utils.logger import log


class AudioVersionWidget(QWidget):
    """Widget for a single audio configuration version."""

    def __init__(self, version: str, config: dict, parent=None):
        super().__init__(parent)
        self.version = version
        self.config = config
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        # Model info
        model_group = QGroupBox("Model Configuration")
        model_layout = QVBoxLayout(model_group)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self.cmb_model = QComboBox()
        models = AudioService.get_models()
        for key, info in models.items():
            self.cmb_model.addItem(f"{info['name']} ({info['size']})", key)
        # Set default from config
        idx = self.cmb_model.findData(self.config["model"])
        if idx >= 0:
            self.cmb_model.setCurrentIndex(idx)
        model_row.addWidget(self.cmb_model)
        model_layout.addLayout(model_row)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Language:"))
        self.cmb_language = QComboBox()
        self.cmb_language.addItems(["Auto Detect", "Vietnamese", "English", "Chinese",
                                     "Japanese", "Korean", "French", "German"])
        lang_row.addWidget(self.cmb_language)
        model_layout.addLayout(lang_row)

        layout.addWidget(model_group)

        # Options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)

        self.chk_gpu = QCheckBox("Enable GPU acceleration")
        self.chk_gpu.setChecked(self.config.get("use_gpu", False))
        options_layout.addWidget(self.chk_gpu)

        if self.version == "v2":
            self.chk_quantize = QCheckBox("Quantize model (INT8)")
            self.chk_quantize.setChecked(self.config.get("quantize", False))
            options_layout.addWidget(self.chk_quantize)

        if self.version == "v3":
            self.chk_split_vocal = QCheckBox("Split vocal from background")
            self.chk_split_vocal.setChecked(self.config.get("split_vocal", False))
            options_layout.addWidget(self.chk_split_vocal)

            self.chk_vad = QCheckBox("Enable VAD (Voice Activity Detection)")
            self.chk_vad.setChecked(self.config.get("vad", False))
            options_layout.addWidget(self.chk_vad)

        layout.addWidget(options_group)

        # Input
        input_group = QGroupBox("Audio Input")
        input_layout = QVBoxLayout(input_group)

        file_row = QHBoxLayout()
        self.btn_load = AnimatedButton("Load Audio File", color="#4A90D9")
        self.btn_load.clicked.connect(self._load_audio)
        file_row.addWidget(self.btn_load)
        input_layout.addLayout(file_row)

        self.lbl_file = QLabel("No file loaded")
        self.lbl_file.setObjectName("subtitleLabel")
        input_layout.addWidget(self.lbl_file)

        layout.addWidget(input_group)

        # Transcribe button
        self.btn_transcribe = AnimatedButton("Transcribe", color="#4AD97A",
                                              style_id="successButton")
        self.btn_transcribe.clicked.connect(self._transcribe)
        layout.addWidget(self.btn_transcribe)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Output
        output_group = QGroupBox("Transcription Output")
        output_layout = QVBoxLayout(output_group)
        self.txt_output = QTextEdit()
        self.txt_output.setPlaceholderText("Transcription results will appear here...")
        self.txt_output.setReadOnly(True)
        self.txt_output.setMinimumHeight(150)
        output_layout.addWidget(self.txt_output)

        btn_row = QHBoxLayout()
        self.btn_save_srt = QPushButton("Save as SRT")
        self.btn_save_srt.clicked.connect(self._save_srt)
        btn_row.addWidget(self.btn_save_srt)

        self.btn_save_txt = QPushButton("Save as TXT")
        self.btn_save_txt.clicked.connect(self._save_txt)
        btn_row.addWidget(self.btn_save_txt)
        btn_row.addStretch()
        output_layout.addLayout(btn_row)

        layout.addWidget(output_group)
        layout.addStretch()

        self._audio_path = ""
        self._segments = []

    def _load_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Audio", "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;Video Files (*.mp4 *.avi *.mkv);;All Files (*)"
        )
        if file_path:
            self._audio_path = file_path
            self.lbl_file.setText(f"Loaded: {file_path}")

    def _transcribe(self):
        if not self._audio_path:
            self.txt_output.setPlainText("Please load an audio file first.")
            return

        self.btn_transcribe.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        overrides = {
            "model": self.cmb_model.currentData(),
            "use_gpu": self.chk_gpu.isChecked(),
        }
        if self.version == "v2" and hasattr(self, "chk_quantize"):
            overrides["quantize"] = self.chk_quantize.isChecked()
        if self.version == "v3":
            if hasattr(self, "chk_split_vocal"):
                overrides["split_vocal"] = self.chk_split_vocal.isChecked()
            if hasattr(self, "chk_vad"):
                overrides["vad"] = self.chk_vad.isChecked()

        self._worker = AudioService.create_worker(
            self._audio_path, config=self.version, **overrides
        )
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(self.progress.setValue)
        self._worker.start()

    def _on_finished(self, segments: list):
        self._segments = segments
        srt_text = AudioService.segments_to_srt(segments)
        self.txt_output.setPlainText(srt_text)
        self.progress.setVisible(False)
        self.btn_transcribe.setEnabled(True)

    def _on_error(self, error: str):
        self.txt_output.setPlainText(f"Error: {error}")
        self.progress.setVisible(False)
        self.btn_transcribe.setEnabled(True)

    def _save_srt(self):
        if not self._segments:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save SRT", "", "SRT Files (*.srt)"
        )
        if file_path:
            srt = AudioService.segments_to_srt(self._segments)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(srt)

    def _save_txt(self):
        if not self._segments:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save TXT", "", "Text Files (*.txt)"
        )
        if file_path:
            text = "\n".join(seg["text"] for seg in self._segments)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(text)


class AudioPanel(QWidget):
    """Audio panel with V1/V2/V3 tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("Audio Transcription (Whisper)")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        self.tab_widget = QTabWidget()
        for version, config in AUDIO_CONFIGS.items():
            widget = AudioVersionWidget(version, config)
            self.tab_widget.addTab(widget, config["name"])

        layout.addWidget(self.tab_widget)
