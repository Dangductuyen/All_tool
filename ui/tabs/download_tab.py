"""
Download tab - video downloader for multiple platforms.
Supports: Douyin, TikTok, Kuaishou, Facebook Reels, Instagram Reels, Bilibili
"""
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal

from ui.widgets.animated_button import AnimatedButton
from ui.widgets.loading_spinner import LoadingSpinner
from services.download_service import DownloadService, PLATFORMS
from utils.config import ConfigManager
from utils.logger import log


class PlatformPage(QWidget):
    """Single platform download page."""

    scan_requested = Signal(str, str)  # url, platform
    stop_requested = Signal()

    def __init__(self, platform_key: str, platform_info: dict, parent=None):
        super().__init__(parent)
        self.platform_key = platform_key
        self.platform_info = platform_info
        self._scan_worker = None
        self._download_workers = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)

        # URL input
        input_layout = QHBoxLayout()
        self.txt_url = QLineEdit()
        self.txt_url.setPlaceholderText(f"Enter {self.platform_info['name']} URL...")
        input_layout.addWidget(self.txt_url)

        self.btn_scan = AnimatedButton("Scan", color="#4A90D9")
        self.btn_scan.setFixedWidth(100)
        self.btn_scan.clicked.connect(self._on_scan)
        input_layout.addWidget(self.btn_scan)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("dangerButton")
        self.btn_stop.setFixedWidth(80)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop)
        input_layout.addWidget(self.btn_stop)

        layout.addLayout(input_layout)

        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Thumbnail", "ID", "Description", "Likes", "Views", "Author", "Status"
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Download buttons
        btn_layout = QHBoxLayout()
        self.btn_download_selected = AnimatedButton("Download Selected", color="#4AD97A",
                                                     style_id="successButton")
        self.btn_download_selected.clicked.connect(self._download_selected)
        btn_layout.addWidget(self.btn_download_selected)

        self.btn_download_all = AnimatedButton("Download All", color="#F5A623")
        self.btn_download_all.clicked.connect(self._download_all)
        btn_layout.addWidget(self.btn_download_all)

        btn_layout.addStretch()

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setObjectName("subtitleLabel")
        btn_layout.addWidget(self.lbl_status)

        layout.addLayout(btn_layout)

    def _on_scan(self):
        url = self.txt_url.text().strip()
        if not url:
            return

        self.btn_scan.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.lbl_status.setText("Scanning...")

        self._scan_worker = DownloadService.create_scan_worker(url, self.platform_key)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.progress.connect(self.progress.setValue)
        self._scan_worker.start()

    def _on_stop(self):
        if self._scan_worker and self._scan_worker.isRunning():
            self._scan_worker.stop()
        self.btn_scan.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setVisible(False)
        self.lbl_status.setText("Stopped")

    def _on_scan_finished(self, videos: list):
        self.btn_scan.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setVisible(False)

        self.table.setRowCount(len(videos))
        for row, video in enumerate(videos):
            self.table.setItem(row, 0, QTableWidgetItem("[IMG]"))
            self.table.setItem(row, 1, QTableWidgetItem(str(video.get("id", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(video.get("description", "")[:80]))
            self.table.setItem(row, 3, QTableWidgetItem(str(video.get("like_count", 0))))
            self.table.setItem(row, 4, QTableWidgetItem(str(video.get("view_count", 0))))
            self.table.setItem(row, 5, QTableWidgetItem(video.get("author", "")))
            self.table.setItem(row, 6, QTableWidgetItem(video.get("status", "Ready")))

        self.lbl_status.setText(f"Found {len(videos)} videos")

    def _on_scan_error(self, error: str):
        self.btn_scan.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setVisible(False)
        self.lbl_status.setText(f"Error: {error[:50]}")

    def _download_selected(self):
        rows = set(item.row() for item in self.table.selectedItems())
        if rows:
            self.lbl_status.setText(f"Downloading {len(rows)} selected...")
            for row in rows:
                self.table.setItem(row, 6, QTableWidgetItem("Downloading..."))

    def _download_all(self):
        count = self.table.rowCount()
        if count > 0:
            self.lbl_status.setText(f"Downloading all {count} videos...")
            for row in range(count):
                self.table.setItem(row, 6, QTableWidgetItem("Downloading..."))


class DownloadTab(QWidget):
    """Download tab with platform sub-tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("Video Downloader")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Platform tabs
        self.tab_widget = QTabWidget()
        for key, info in PLATFORMS.items():
            page = PlatformPage(key, info)
            self.tab_widget.addTab(page, f"{info['name']}")

        layout.addWidget(self.tab_widget)
