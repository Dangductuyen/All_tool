"""
Inspector tab - displays media file properties and metadata.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QFormLayout, QLineEdit
)
from PySide6.QtCore import Qt


class InspectorTab(QWidget):
    """Inspector tab showing media properties."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Inspector")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # File info
        file_group = QGroupBox("File Information")
        file_form = QFormLayout(file_group)

        self.lbl_filename = QLineEdit("No file loaded")
        self.lbl_filename.setReadOnly(True)
        file_form.addRow("Filename:", self.lbl_filename)

        self.lbl_path = QLineEdit("-")
        self.lbl_path.setReadOnly(True)
        file_form.addRow("Path:", self.lbl_path)

        self.lbl_size = QLineEdit("-")
        self.lbl_size.setReadOnly(True)
        file_form.addRow("File Size:", self.lbl_size)

        self.lbl_format = QLineEdit("-")
        self.lbl_format.setReadOnly(True)
        file_form.addRow("Format:", self.lbl_format)

        layout.addWidget(file_group)

        # Video properties
        video_group = QGroupBox("Video Properties")
        video_form = QFormLayout(video_group)

        self.lbl_resolution = QLineEdit("-")
        self.lbl_resolution.setReadOnly(True)
        video_form.addRow("Resolution:", self.lbl_resolution)

        self.lbl_fps = QLineEdit("-")
        self.lbl_fps.setReadOnly(True)
        video_form.addRow("Frame Rate:", self.lbl_fps)

        self.lbl_duration = QLineEdit("-")
        self.lbl_duration.setReadOnly(True)
        video_form.addRow("Duration:", self.lbl_duration)

        self.lbl_codec = QLineEdit("-")
        self.lbl_codec.setReadOnly(True)
        video_form.addRow("Video Codec:", self.lbl_codec)

        self.lbl_bitrate = QLineEdit("-")
        self.lbl_bitrate.setReadOnly(True)
        video_form.addRow("Bitrate:", self.lbl_bitrate)

        layout.addWidget(video_group)

        # Audio properties
        audio_group = QGroupBox("Audio Properties")
        audio_form = QFormLayout(audio_group)

        self.lbl_audio_codec = QLineEdit("-")
        self.lbl_audio_codec.setReadOnly(True)
        audio_form.addRow("Audio Codec:", self.lbl_audio_codec)

        self.lbl_sample_rate = QLineEdit("-")
        self.lbl_sample_rate.setReadOnly(True)
        audio_form.addRow("Sample Rate:", self.lbl_sample_rate)

        self.lbl_channels = QLineEdit("-")
        self.lbl_channels.setReadOnly(True)
        audio_form.addRow("Channels:", self.lbl_channels)

        self.lbl_audio_bitrate = QLineEdit("-")
        self.lbl_audio_bitrate.setReadOnly(True)
        audio_form.addRow("Audio Bitrate:", self.lbl_audio_bitrate)

        layout.addWidget(audio_group)
        layout.addStretch()

    def update_info(self, info: dict):
        """Update inspector with media info."""
        self.lbl_filename.setText(info.get("filename", "-"))
        self.lbl_path.setText(info.get("path", "-"))
        self.lbl_size.setText(info.get("size", "-"))
        self.lbl_format.setText(info.get("format", "-"))
        self.lbl_resolution.setText(info.get("resolution", "-"))
        self.lbl_fps.setText(info.get("fps", "-"))
        self.lbl_duration.setText(info.get("duration", "-"))
        self.lbl_codec.setText(info.get("video_codec", "-"))
        self.lbl_bitrate.setText(info.get("bitrate", "-"))
        self.lbl_audio_codec.setText(info.get("audio_codec", "-"))
        self.lbl_sample_rate.setText(info.get("sample_rate", "-"))
        self.lbl_channels.setText(info.get("channels", "-"))
        self.lbl_audio_bitrate.setText(info.get("audio_bitrate", "-"))
