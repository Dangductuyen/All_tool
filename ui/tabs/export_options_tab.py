"""
Export Options tab - configure and export final video.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QCheckBox, QProgressBar, QFileDialog,
    QSpinBox
)
from PySide6.QtCore import Qt

from ui.widgets.animated_button import AnimatedButton


class ExportOptionsTab(QWidget):
    """Export options tab for final video rendering."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Export Options")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Format settings
        format_group = QGroupBox("Output Format")
        format_layout = QVBoxLayout(format_group)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Format:"))
        self.cmb_format = QComboBox()
        self.cmb_format.addItems(["MP4", "AVI", "MKV", "MOV", "WebM", "GIF"])
        fmt_row.addWidget(self.cmb_format)
        format_layout.addLayout(fmt_row)

        codec_row = QHBoxLayout()
        codec_row.addWidget(QLabel("Video Codec:"))
        self.cmb_video_codec = QComboBox()
        self.cmb_video_codec.addItems(["H.264", "H.265 (HEVC)", "VP9", "AV1", "ProRes"])
        codec_row.addWidget(self.cmb_video_codec)
        format_layout.addLayout(codec_row)

        acodec_row = QHBoxLayout()
        acodec_row.addWidget(QLabel("Audio Codec:"))
        self.cmb_audio_codec = QComboBox()
        self.cmb_audio_codec.addItems(["AAC", "MP3", "FLAC", "Opus", "PCM"])
        acodec_row.addWidget(self.cmb_audio_codec)
        format_layout.addLayout(acodec_row)

        layout.addWidget(format_group)

        # Quality settings
        quality_group = QGroupBox("Quality Settings")
        quality_layout = QVBoxLayout(quality_group)

        res_row = QHBoxLayout()
        res_row.addWidget(QLabel("Resolution:"))
        self.cmb_resolution = QComboBox()
        self.cmb_resolution.addItems([
            "3840x2160 (4K)", "2560x1440 (2K)", "1920x1080 (Full HD)",
            "1280x720 (HD)", "854x480 (SD)", "640x360"
        ])
        self.cmb_resolution.setCurrentIndex(2)
        res_row.addWidget(self.cmb_resolution)
        quality_layout.addLayout(res_row)

        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("Frame Rate:"))
        self.cmb_fps = QComboBox()
        self.cmb_fps.addItems(["24", "25", "30", "50", "60"])
        self.cmb_fps.setCurrentText("30")
        fps_row.addWidget(self.cmb_fps)
        quality_layout.addLayout(fps_row)

        bitrate_row = QHBoxLayout()
        bitrate_row.addWidget(QLabel("Bitrate (Mbps):"))
        self.spin_bitrate = QSpinBox()
        self.spin_bitrate.setMinimum(1)
        self.spin_bitrate.setMaximum(100)
        self.spin_bitrate.setValue(8)
        bitrate_row.addWidget(self.spin_bitrate)
        quality_layout.addLayout(bitrate_row)

        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Quality Preset:"))
        self.cmb_quality = QComboBox()
        self.cmb_quality.addItems(["Ultra", "High", "Medium", "Low", "Custom"])
        self.cmb_quality.setCurrentText("High")
        quality_row.addWidget(self.cmb_quality)
        quality_layout.addLayout(quality_row)

        layout.addWidget(quality_group)

        # Options
        options_group = QGroupBox("Additional Options")
        options_layout = QVBoxLayout(options_group)

        self.chk_burn_subs = QCheckBox("Burn subtitles into video")
        options_layout.addWidget(self.chk_burn_subs)

        self.chk_normalize_audio = QCheckBox("Normalize audio levels")
        self.chk_normalize_audio.setChecked(True)
        options_layout.addWidget(self.chk_normalize_audio)

        self.chk_two_pass = QCheckBox("Two-pass encoding (better quality)")
        options_layout.addWidget(self.chk_two_pass)

        self.chk_fast_start = QCheckBox("Fast start (web optimized)")
        self.chk_fast_start.setChecked(True)
        options_layout.addWidget(self.chk_fast_start)

        layout.addWidget(options_group)

        # Output path
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)

        path_row = QHBoxLayout()
        self.lbl_output = QLabel("~/VideoEditorProjects/output/")
        self.lbl_output.setObjectName("subtitleLabel")
        path_row.addWidget(self.lbl_output)

        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self._browse_output)
        path_row.addWidget(self.btn_browse)
        output_layout.addLayout(path_row)

        layout.addWidget(output_group)

        # Export button
        self.btn_export = AnimatedButton("Export Video", color="#4AD97A",
                                          style_id="successButton")
        self.btn_export.setMinimumHeight(44)
        layout.addWidget(self.btn_export)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.lbl_status = QLabel("")
        self.lbl_status.setObjectName("subtitleLabel")
        layout.addWidget(self.lbl_status)

        layout.addStretch()

    def _browse_output(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.lbl_output.setText(dir_path)
