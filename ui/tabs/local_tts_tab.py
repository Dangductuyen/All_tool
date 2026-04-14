"""
Local TTS tab - offline text-to-speech.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSlider, QTextEdit, QGroupBox, QCheckBox,
    QProgressBar
)
from PySide6.QtCore import Qt

from ui.widgets.animated_button import AnimatedButton


class LocalTTSTab(QWidget):
    """Local TTS tab for offline speech synthesis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Local TTS (Offline)")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Engine selection
        engine_group = QGroupBox("TTS Engine")
        engine_layout = QVBoxLayout(engine_group)

        eng_row = QHBoxLayout()
        eng_row.addWidget(QLabel("Engine:"))
        self.cmb_engine = QComboBox()
        self.cmb_engine.addItems(["pyttsx3", "Coqui TTS", "Bark"])
        eng_row.addWidget(self.cmb_engine)
        engine_layout.addLayout(eng_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self.cmb_model = QComboBox()
        self.cmb_model.addItems(["Default", "Fast", "High Quality"])
        model_row.addWidget(self.cmb_model)
        engine_layout.addLayout(model_row)

        self.chk_gpu = QCheckBox("Use GPU acceleration")
        engine_layout.addWidget(self.chk_gpu)

        layout.addWidget(engine_group)

        # Voice settings
        voice_group = QGroupBox("Voice Settings")
        voice_layout = QVBoxLayout(voice_group)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("Language:"))
        self.cmb_lang = QComboBox()
        self.cmb_lang.addItems(["Vietnamese", "English", "Chinese", "Japanese", "Korean"])
        lang_row.addWidget(self.cmb_lang)
        voice_layout.addLayout(lang_row)

        # Speed
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        self.lbl_speed = QLabel("1.0x")
        self.slider_speed = QSlider(Qt.Orientation.Horizontal)
        self.slider_speed.setMinimum(50)
        self.slider_speed.setMaximum(200)
        self.slider_speed.setValue(100)
        self.slider_speed.valueChanged.connect(
            lambda v: self.lbl_speed.setText(f"{v/100:.1f}x")
        )
        speed_row.addWidget(self.slider_speed)
        speed_row.addWidget(self.lbl_speed)
        voice_layout.addLayout(speed_row)

        # Pitch
        pitch_row = QHBoxLayout()
        pitch_row.addWidget(QLabel("Pitch:"))
        self.lbl_pitch = QLabel("1.0")
        self.slider_pitch = QSlider(Qt.Orientation.Horizontal)
        self.slider_pitch.setMinimum(50)
        self.slider_pitch.setMaximum(200)
        self.slider_pitch.setValue(100)
        self.slider_pitch.valueChanged.connect(
            lambda v: self.lbl_pitch.setText(f"{v/100:.1f}")
        )
        pitch_row.addWidget(self.slider_pitch)
        pitch_row.addWidget(self.lbl_pitch)
        voice_layout.addLayout(pitch_row)

        layout.addWidget(voice_group)

        # Text input
        text_group = QGroupBox("Text Input")
        text_layout = QVBoxLayout(text_group)
        self.txt_input = QTextEdit()
        self.txt_input.setPlaceholderText("Enter text for local TTS...")
        self.txt_input.setMinimumHeight(120)
        text_layout.addWidget(self.txt_input)
        layout.addWidget(text_group)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_preview = AnimatedButton("Preview", color="#F5A623")
        btn_layout.addWidget(self.btn_preview)

        self.btn_generate = AnimatedButton("Generate", color="#4AD97A",
                                           style_id="successButton")
        btn_layout.addWidget(self.btn_generate)
        layout.addLayout(btn_layout)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        layout.addStretch()
