"""
Music tab - background music management.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QListWidget, QListWidgetItem, QGroupBox,
    QFileDialog, QComboBox
)
from PySide6.QtCore import Qt

from ui.widgets.animated_button import AnimatedButton


class MusicTab(QWidget):
    """Music management tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Music")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Import music
        import_group = QGroupBox("Import Music")
        import_layout = QVBoxLayout(import_group)

        btn_row = QHBoxLayout()
        self.btn_import = AnimatedButton("Import Audio File", color="#4A90D9")
        self.btn_import.clicked.connect(self._import_music)
        btn_row.addWidget(self.btn_import)
        import_layout.addLayout(btn_row)

        layout.addWidget(import_group)

        # Music library
        lib_group = QGroupBox("Music Library")
        lib_layout = QVBoxLayout(lib_group)

        category_row = QHBoxLayout()
        category_row.addWidget(QLabel("Category:"))
        self.cmb_category = QComboBox()
        self.cmb_category.addItems(["All", "BGM", "SFX", "Ambient", "Imported"])
        category_row.addWidget(self.cmb_category)
        lib_layout.addLayout(category_row)

        self.music_list = QListWidget()
        # Add sample items
        samples = [
            "Upbeat Corporate - 2:30",
            "Chill Lo-fi Beat - 3:15",
            "Epic Cinematic - 4:00",
            "Soft Piano - 2:45",
            "Electronic Dance - 3:30",
            "Acoustic Guitar - 2:00",
        ]
        for sample in samples:
            self.music_list.addItem(QListWidgetItem(sample))
        lib_layout.addWidget(self.music_list)

        layout.addWidget(lib_group)

        # Volume control
        vol_group = QGroupBox("Volume Control")
        vol_layout = QVBoxLayout(vol_group)

        music_vol_row = QHBoxLayout()
        music_vol_row.addWidget(QLabel("Music Volume:"))
        self.slider_music_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_music_vol.setMinimum(0)
        self.slider_music_vol.setMaximum(100)
        self.slider_music_vol.setValue(70)
        self.lbl_music_vol = QLabel("70%")
        self.slider_music_vol.valueChanged.connect(
            lambda v: self.lbl_music_vol.setText(f"{v}%")
        )
        music_vol_row.addWidget(self.slider_music_vol)
        music_vol_row.addWidget(self.lbl_music_vol)
        vol_layout.addLayout(music_vol_row)

        voice_vol_row = QHBoxLayout()
        voice_vol_row.addWidget(QLabel("Voice Volume:"))
        self.slider_voice_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_voice_vol.setMinimum(0)
        self.slider_voice_vol.setMaximum(100)
        self.slider_voice_vol.setValue(100)
        self.lbl_voice_vol = QLabel("100%")
        self.slider_voice_vol.valueChanged.connect(
            lambda v: self.lbl_voice_vol.setText(f"{v}%")
        )
        voice_vol_row.addWidget(self.slider_voice_vol)
        voice_vol_row.addWidget(self.lbl_voice_vol)
        vol_layout.addLayout(voice_vol_row)

        layout.addWidget(vol_group)

        # Actions
        action_row = QHBoxLayout()
        self.btn_add_to_timeline = AnimatedButton("Add to Timeline", color="#4AD97A",
                                                    style_id="successButton")
        action_row.addWidget(self.btn_add_to_timeline)

        self.btn_preview = QPushButton("Preview")
        action_row.addWidget(self.btn_preview)

        action_row.addStretch()
        layout.addLayout(action_row)

        layout.addStretch()

    def _import_music(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Music", "",
            "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a *.aac);;All Files (*)"
        )
        if file_path:
            import os
            name = os.path.basename(file_path)
            self.music_list.addItem(QListWidgetItem(f"[Imported] {name}"))
