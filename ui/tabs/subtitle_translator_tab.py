"""
Subtitle Translator tab - translate SRT files using AI engines.
Supports: OpenAI, Gemini, Groq
"""
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QGroupBox, QFileDialog, QProgressBar,
    QSpinBox, QSplitter
)
from PySide6.QtCore import Qt

from ui.widgets.animated_button import AnimatedButton
from services.subtitle_service import SubtitleService
from services.translator_service import TranslatorService
from utils.logger import log


class SubtitleTranslatorTab(QWidget):
    """Subtitle translator tab with multi-engine support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []
        self._translated = []
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Subtitle Translator")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Load SRT
        load_group = QGroupBox("Load Subtitle File")
        load_layout = QVBoxLayout(load_group)

        btn_row = QHBoxLayout()
        self.btn_load = AnimatedButton("Load SRT File", color="#4A90D9")
        self.btn_load.clicked.connect(self._load_srt)
        btn_row.addWidget(self.btn_load)

        self.btn_validate = QPushButton("Validate Format")
        self.btn_validate.clicked.connect(self._validate)
        btn_row.addWidget(self.btn_validate)
        btn_row.addStretch()
        load_layout.addLayout(btn_row)

        self.lbl_file = QLabel("No file loaded")
        self.lbl_file.setObjectName("subtitleLabel")
        load_layout.addWidget(self.lbl_file)

        layout.addWidget(load_group)

        # Translation settings
        settings_group = QGroupBox("Translation Settings")
        settings_layout = QVBoxLayout(settings_group)

        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("Engine:"))
        self.cmb_engine = QComboBox()
        for key, info in TranslatorService.get_engines().items():
            self.cmb_engine.addItem(info["name"], key)
        engine_row.addWidget(self.cmb_engine)
        settings_layout.addLayout(engine_row)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Source:"))
        self.cmb_source = QComboBox()
        for code, name in TranslatorService.get_languages():
            self.cmb_source.addItem(name, code)
        lang_row.addWidget(self.cmb_source)

        lang_row.addWidget(QLabel("Target:"))
        self.cmb_target = QComboBox()
        for code, name in TranslatorService.get_languages():
            self.cmb_target.addItem(name, code)
        # Default target to Vietnamese
        idx = self.cmb_target.findData("vi")
        if idx >= 0:
            self.cmb_target.setCurrentIndex(idx)
        lang_row.addWidget(self.cmb_target)
        settings_layout.addLayout(lang_row)

        batch_row = QHBoxLayout()
        batch_row.addWidget(QLabel("Batch Size:"))
        self.spin_batch = QSpinBox()
        self.spin_batch.setMinimum(1)
        self.spin_batch.setMaximum(50)
        self.spin_batch.setValue(10)
        batch_row.addWidget(self.spin_batch)
        batch_row.addStretch()
        settings_layout.addLayout(batch_row)

        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("API Key:"))
        from PySide6.QtWidgets import QLineEdit
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setPlaceholderText("Enter API key (optional for mock)...")
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_row.addWidget(self.txt_api_key)
        settings_layout.addLayout(api_row)

        layout.addWidget(settings_group)

        # Translate button
        action_row = QHBoxLayout()
        self.btn_translate = AnimatedButton("Translate", color="#4AD97A",
                                             style_id="successButton")
        self.btn_translate.clicked.connect(self._translate)
        action_row.addWidget(self.btn_translate)

        self.btn_save = AnimatedButton("Save Translated SRT", color="#F5A623")
        self.btn_save.clicked.connect(self._save_translated)
        self.btn_save.setEnabled(False)
        action_row.addWidget(self.btn_save)
        layout.addLayout(action_row)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("subtitleLabel")
        layout.addWidget(self.lbl_status)

        # Preview splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Original text
        orig_widget = QWidget()
        orig_layout = QVBoxLayout(orig_widget)
        orig_layout.setContentsMargins(0, 0, 4, 0)
        orig_layout.addWidget(QLabel("Original"))
        self.txt_original = QTextEdit()
        self.txt_original.setReadOnly(True)
        self.txt_original.setPlaceholderText("Original subtitles...")
        orig_layout.addWidget(self.txt_original)
        splitter.addWidget(orig_widget)

        # Translated text
        trans_widget = QWidget()
        trans_layout = QVBoxLayout(trans_widget)
        trans_layout.setContentsMargins(4, 0, 0, 0)
        trans_layout.addWidget(QLabel("Translated"))
        self.txt_translated = QTextEdit()
        self.txt_translated.setReadOnly(True)
        self.txt_translated.setPlaceholderText("Translated subtitles...")
        trans_layout.addWidget(self.txt_translated)
        splitter.addWidget(trans_widget)

        layout.addWidget(splitter)

    def _load_srt(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load SRT", "", "SRT Files (*.srt);;All Files (*)"
        )
        if file_path:
            try:
                self._entries = SubtitleService.load_srt(file_path)
                self.lbl_file.setText(f"Loaded: {file_path} ({len(self._entries)} entries)")
                srt_text = SubtitleService.entries_to_srt(self._entries)
                self.txt_original.setPlainText(srt_text)
            except Exception as e:
                self.lbl_file.setText(f"Error: {e}")

    def _validate(self):
        text = self.txt_original.toPlainText()
        if not text:
            self.lbl_status.setText("No subtitle text to validate")
            return
        errors = SubtitleService.validate_srt(text)
        if errors:
            self.lbl_status.setText(f"Found {len(errors)} format errors")
            self.txt_translated.setPlainText("Format Errors:\n" + "\n".join(errors))
        else:
            self.lbl_status.setText("SRT format is valid")

    def _translate(self):
        if not self._entries:
            self.lbl_status.setText("Please load an SRT file first")
            return

        self.btn_translate.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)

        engine = self.cmb_engine.currentData()
        source = self.cmb_source.currentData()
        target = self.cmb_target.currentData()
        api_key = self.txt_api_key.text().strip()

        self._worker = TranslatorService.create_worker(
            self._entries, engine, source, target, api_key,
            batch_size=self.spin_batch.value()
        )
        self._worker.finished.connect(self._on_translated)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(self._on_progress)
        self._worker.start()

    def _on_progress(self, value: int, status: str):
        self.progress.setValue(value)
        self.lbl_status.setText(status)

    def _on_translated(self, entries: list):
        self._translated = entries
        srt_text = SubtitleService.entries_to_srt(entries)
        self.txt_translated.setPlainText(srt_text)
        self.progress.setVisible(False)
        self.btn_translate.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.lbl_status.setText(f"Translation complete! {len(entries)} entries")

    def _on_error(self, error: str):
        self.lbl_status.setText(f"Error: {error}")
        self.progress.setVisible(False)
        self.btn_translate.setEnabled(True)

    def _save_translated(self):
        if not self._translated:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Translated SRT", "", "SRT Files (*.srt)"
        )
        if file_path:
            SubtitleService.save_srt(self._translated, file_path)
            self.lbl_status.setText(f"Saved: {file_path}")
