"""
Cloud TTS tab - multi-engine voice synthesis.
Supports: OpenAI TTS, Edge TTS, Vbee, Minimax
"""
import os
import time

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QTextEdit, QListWidget, QListWidgetItem,
    QGroupBox, QProgressBar, QSplitter, QFileDialog
)
from PySide6.QtCore import Qt, Signal

from ui.widgets.animated_button import AnimatedButton
from ui.widgets.loading_spinner import LoadingSpinner
from services.tts_service import TTSService, TTSWorker
from utils.config import ConfigManager
from utils.logger import log


class VoiceListItem(QListWidgetItem):
    """Custom list item for voice display."""
    def __init__(self, voice: dict):
        display = f"{voice['name']}"
        super().__init__(display)
        self.voice_data = voice
        tags_str = " | ".join(voice.get("tags", []))
        self.setToolTip(f"Engine: {voice['engine']} | Lang: {voice['lang']} | Tags: {tags_str}")


class CloudTTSTab(QWidget):
    """Cloud TTS tab with multi-engine voice support."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = ConfigManager()
        self.tts_service = TTSService()
        self._worker = None
        self._history = []
        self._setup_ui()
        self._load_voices()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("Cloud TTS")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT: Engine & Voice selection
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 8, 0)

        # Engine selection
        engine_group = QGroupBox("TTS Engine")
        engine_layout = QVBoxLayout(engine_group)

        self.cmb_engine = QComboBox()
        self.cmb_engine.addItems(["All Engines", "edge_tts", "openai", "vbee", "minimax"])
        self.cmb_engine.currentTextChanged.connect(self._filter_voices)
        engine_layout.addWidget(self.cmb_engine)
        left_layout.addWidget(engine_group)

        # Language selection
        lang_group = QGroupBox("Language")
        lang_layout = QVBoxLayout(lang_group)

        self.cmb_language = QComboBox()
        self.cmb_language.addItem("All Languages", "")
        for code, name in TTSService.get_languages():
            self.cmb_language.addItem(f"{name} ({code})", code)
        self.cmb_language.currentIndexChanged.connect(self._filter_voices)
        lang_layout.addWidget(self.cmb_language)
        left_layout.addWidget(lang_group)

        # Tag filter
        tag_group = QGroupBox("Filter by Tag")
        tag_layout = QHBoxLayout(tag_group)
        self.btn_tag_female = QPushButton("female")
        self.btn_tag_female.setCheckable(True)
        self.btn_tag_female.clicked.connect(self._filter_voices)
        tag_layout.addWidget(self.btn_tag_female)

        self.btn_tag_male = QPushButton("male")
        self.btn_tag_male.setCheckable(True)
        self.btn_tag_male.clicked.connect(self._filter_voices)
        tag_layout.addWidget(self.btn_tag_male)

        self.btn_tag_tiktok = QPushButton("tiktok")
        self.btn_tag_tiktok.setCheckable(True)
        self.btn_tag_tiktok.clicked.connect(self._filter_voices)
        tag_layout.addWidget(self.btn_tag_tiktok)

        self.btn_tag_natural = QPushButton("natural")
        self.btn_tag_natural.setCheckable(True)
        self.btn_tag_natural.clicked.connect(self._filter_voices)
        tag_layout.addWidget(self.btn_tag_natural)

        left_layout.addWidget(tag_group)

        # Voice list
        voice_group = QGroupBox("Voices")
        voice_layout = QVBoxLayout(voice_group)
        self.voice_list = QListWidget()
        self.voice_list.setMinimumHeight(200)
        voice_layout.addWidget(self.voice_list)

        self.lbl_voice_count = QLabel("0 voices")
        self.lbl_voice_count.setObjectName("subtitleLabel")
        voice_layout.addWidget(self.lbl_voice_count)

        left_layout.addWidget(voice_group)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # RIGHT: Text input & controls
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 0, 0, 0)

        # Speed control
        speed_group = QGroupBox("Speed")
        speed_layout = QHBoxLayout(speed_group)
        self.lbl_speed = QLabel("1.0x")
        self.lbl_speed.setMinimumWidth(40)
        speed_layout.addWidget(self.lbl_speed)

        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setMinimum(50)
        self.slider_speed.setMaximum(200)
        self.slider_speed.setValue(100)
        self.slider_speed.setTickInterval(25)
        self.slider_speed.valueChanged.connect(
            lambda v: self.lbl_speed.setText(f"{v / 100:.1f}x")
        )
        speed_layout.addWidget(self.slider_speed)
        right_layout.addWidget(speed_group)

        # Text input
        text_group = QGroupBox("Text Input")
        text_layout = QVBoxLayout(text_group)

        self.txt_input = QTextEdit()
        self.txt_input.setPlaceholderText("Enter text to convert to speech...")
        self.txt_input.setMinimumHeight(150)
        text_layout.addWidget(self.txt_input)

        char_layout = QHBoxLayout()
        self.lbl_chars = QLabel("0 characters")
        self.lbl_chars.setObjectName("subtitleLabel")
        self.txt_input.textChanged.connect(
            lambda: self.lbl_chars.setText(f"{len(self.txt_input.toPlainText())} characters")
        )
        char_layout.addWidget(self.lbl_chars)
        char_layout.addStretch()
        text_layout.addLayout(char_layout)

        right_layout.addWidget(text_group)

        # Action buttons
        btn_layout = QHBoxLayout()
        self.btn_preview = AnimatedButton("Preview Voice", color="#F5A623")
        self.btn_preview.clicked.connect(self._preview_voice)
        btn_layout.addWidget(self.btn_preview)

        self.btn_generate = AnimatedButton("Generate Speech", color="#4AD97A",
                                           style_id="successButton")
        self.btn_generate.clicked.connect(self._generate_speech)
        btn_layout.addWidget(self.btn_generate)
        right_layout.addLayout(btn_layout)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        right_layout.addWidget(self.progress)

        # Spinner
        self.spinner = LoadingSpinner(self)
        right_layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        # Generated audio history
        history_group = QGroupBox("Generated Audio History")
        history_layout = QVBoxLayout(history_group)
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(150)
        history_layout.addWidget(self.history_list)
        right_layout.addWidget(history_group)

        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([350, 450])

        layout.addWidget(splitter)

    def _load_voices(self):
        """Load all voices into the list."""
        self._filter_voices()

    def _filter_voices(self):
        """Filter voices based on current selections."""
        self.voice_list.clear()

        engine = self.cmb_engine.currentText()
        if engine == "All Engines":
            engine = None

        lang_code = self.cmb_language.currentData()

        tag = None
        for btn, tag_name in [
            (self.btn_tag_female, "female"),
            (self.btn_tag_male, "male"),
            (self.btn_tag_tiktok, "tiktok"),
            (self.btn_tag_natural, "natural"),
        ]:
            if btn.isChecked():
                tag = tag_name
                break

        voices = self.tts_service.get_voices(engine=engine, language=lang_code, tag=tag)

        for voice in voices:
            item = VoiceListItem(voice)
            self.voice_list.addItem(item)

        self.lbl_voice_count.setText(f"{len(voices)} voices")

        if voices:
            self.voice_list.setCurrentRow(0)

    def _get_selected_voice(self):
        """Get currently selected voice data."""
        item = self.voice_list.currentItem()
        if item and isinstance(item, VoiceListItem):
            return item.voice_data
        return None

    def _preview_voice(self):
        """Preview selected voice with sample text."""
        voice = self._get_selected_voice()
        if not voice:
            return

        text = self.txt_input.toPlainText().strip()
        if not text:
            text = "Hello, this is a voice preview. Xin chào, đây là bản xem trước giọng nói."

        self._start_generation(voice, text[:100])

    def _generate_speech(self):
        """Generate full speech with selected voice."""
        voice = self._get_selected_voice()
        if not voice:
            return

        text = self.txt_input.toPlainText().strip()
        if not text:
            return

        self._start_generation(voice, text)

    def _start_generation(self, voice: dict, text: str):
        """Start TTS generation in background thread."""
        if self._worker and self._worker.isRunning():
            return

        output_dir = self.config.get("paths", "output_dir")
        os.makedirs(output_dir, exist_ok=True)

        speed = self.slider_speed.value() / 100.0

        self._worker = self.tts_service.create_worker(
            engine=voice["engine"],
            voice=voice["name"],
            text=text,
            speed=speed,
            output_dir=output_dir,
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)

        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.btn_generate.setEnabled(False)
        self.btn_preview.setEnabled(False)
        self.spinner.start()

        self._worker.start()

    def _on_progress(self, value: int):
        self.progress.setValue(value)

    def _on_finished(self, output_path: str):
        self.progress.setValue(100)
        self.spinner.stop()
        self.btn_generate.setEnabled(True)
        self.btn_preview.setEnabled(True)

        self._history.append(output_path)
        self.history_list.addItem(f"[{len(self._history)}] {os.path.basename(output_path)}")

        log.info(f"TTS generated: {output_path}")

    def _on_error(self, error: str):
        self.progress.setVisible(False)
        self.spinner.stop()
        self.btn_generate.setEnabled(True)
        self.btn_preview.setEnabled(True)
        log.error(f"TTS error: {error}")
