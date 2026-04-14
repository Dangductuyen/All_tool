"""
Editor tab - main video editing interface.
Import video, auto subtitle, hard sub, translate, voice over.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QGroupBox, QCheckBox, QComboBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal

from ui.widgets.animated_button import AnimatedButton


class EditorTab(QWidget):
    """Editor tab with video editing controls."""

    video_imported = Signal(str)  # file path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # Title
        title = QLabel("Video Editor")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Import section
        import_group = QGroupBox("Import")
        import_layout = QVBoxLayout(import_group)

        btn_layout = QHBoxLayout()
        self.btn_import = AnimatedButton("Import Video", color="#4A90D9")
        self.btn_import.clicked.connect(self._import_video)
        btn_layout.addWidget(self.btn_import)

        self.btn_import_audio = AnimatedButton("Import Audio", color="#7ED321")
        btn_layout.addWidget(self.btn_import_audio)
        import_layout.addLayout(btn_layout)

        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setObjectName("subtitleLabel")
        import_layout.addWidget(self.lbl_file)

        layout.addWidget(import_group)

        # Auto subtitle section
        subtitle_group = QGroupBox("Auto Subtitle")
        sub_layout = QVBoxLayout(subtitle_group)

        self.chk_auto_sub = QCheckBox("Enable Auto Subtitle (Whisper)")
        self.chk_auto_sub.setChecked(True)
        sub_layout.addWidget(self.chk_auto_sub)

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.cmb_model = QComboBox()
        self.cmb_model.addItems(["tiny", "base", "small", "medium", "large-v2"])
        model_layout.addWidget(self.cmb_model)
        sub_layout.addLayout(model_layout)

        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Language:"))
        self.cmb_language = QComboBox()
        self.cmb_language.addItems(["Auto Detect", "Vietnamese", "English", "Chinese", "Japanese", "Korean"])
        lang_layout.addWidget(self.cmb_language)
        sub_layout.addLayout(lang_layout)

        self.btn_auto_sub = AnimatedButton("Generate Subtitles", color="#F5A623")
        sub_layout.addWidget(self.btn_auto_sub)

        layout.addWidget(subtitle_group)

        # Hard sub section
        hardsub_group = QGroupBox("Hard Subtitle (Burn-in)")
        hardsub_layout = QVBoxLayout(hardsub_group)

        self.chk_hardsub = QCheckBox("Burn subtitles into video")
        hardsub_layout.addWidget(self.chk_hardsub)

        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("Font Size:"))
        self.cmb_fontsize = QComboBox()
        self.cmb_fontsize.addItems(["16", "20", "24", "28", "32", "36", "40", "48"])
        self.cmb_fontsize.setCurrentText("24")
        font_layout.addWidget(self.cmb_fontsize)
        hardsub_layout.addLayout(font_layout)

        pos_layout = QHBoxLayout()
        pos_layout.addWidget(QLabel("Position:"))
        self.cmb_position = QComboBox()
        self.cmb_position.addItems(["Bottom", "Top", "Center"])
        pos_layout.addWidget(self.cmb_position)
        hardsub_layout.addLayout(pos_layout)

        self.btn_hardsub = AnimatedButton("Apply Hard Subtitle", color="#D94A4A")
        hardsub_layout.addWidget(self.btn_hardsub)

        layout.addWidget(hardsub_group)

        # Translate section
        translate_group = QGroupBox("Translate")
        translate_layout = QVBoxLayout(translate_group)

        target_layout = QHBoxLayout()
        target_layout.addWidget(QLabel("Target Language:"))
        self.cmb_target = QComboBox()
        self.cmb_target.addItems(["Vietnamese", "English", "Chinese", "Japanese", "Korean", "French"])
        target_layout.addWidget(self.cmb_target)
        translate_layout.addLayout(target_layout)

        self.btn_translate = AnimatedButton("Translate Subtitles", color="#4A90D9")
        translate_layout.addWidget(self.btn_translate)

        layout.addWidget(translate_group)

        # Voice over section
        voiceover_group = QGroupBox("Voice Over")
        vo_layout = QVBoxLayout(voiceover_group)

        self.chk_voiceover = QCheckBox("Generate voice over from subtitles")
        vo_layout.addWidget(self.chk_voiceover)

        engine_layout = QHBoxLayout()
        engine_layout.addWidget(QLabel("TTS Engine:"))
        self.cmb_tts_engine = QComboBox()
        self.cmb_tts_engine.addItems(["Edge TTS", "OpenAI TTS", "Vbee", "Minimax"])
        engine_layout.addWidget(self.cmb_tts_engine)
        vo_layout.addLayout(engine_layout)

        self.btn_voiceover = AnimatedButton("Generate Voice Over", color="#7ED321")
        vo_layout.addWidget(self.btn_voiceover)

        layout.addWidget(voiceover_group)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        layout.addStretch()

    def _import_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Video", "",
            "Video Files (*.mp4 *.avi *.mkv *.mov *.wmv *.flv);;All Files (*)"
        )
        if file_path:
            self.lbl_file.setText(f"Loaded: {file_path}")
            self.video_imported.emit(file_path)
