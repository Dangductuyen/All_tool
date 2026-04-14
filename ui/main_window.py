"""
Main window - assembles all panels and tabs into the complete layout.
Layout: Top Bar | Left Panel (Projects) | Center (Preview) | Right Panel (Tabs) | Bottom (Timeline)
"""
import os
import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QLineEdit, QSplitter, QTabWidget, QFrame, QMenuBar,
    QMenu, QStackedWidget, QSizePolicy, QScrollArea,
    QApplication, QFileDialog
)
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtGui import QAction, QFont, QIcon, QColor, QPalette

from ui.styles.dark_theme import DARK_THEME
from ui.widgets.toast import Toast
from ui.widgets.animated_button import AnimatedButton
from ui.timeline_widget import TimelineWidget
from ui.tabs.editor_tab import EditorTab
from ui.tabs.cloud_tts_tab import CloudTTSTab
from ui.tabs.local_tts_tab import LocalTTSTab
from ui.tabs.download_tab import DownloadTab
from ui.tabs.ocr_setting_tab import OCRSettingTab
from ui.tabs.audio_panel import AudioPanel
from ui.tabs.subtitle_translator_tab import SubtitleTranslatorTab
from ui.tabs.inspector_tab import InspectorTab
from ui.tabs.captions_tab import CaptionsTab
from ui.tabs.ai_agent_tab import AIAgentTab
from ui.tabs.music_tab import MusicTab
from ui.tabs.export_options_tab import ExportOptionsTab
from core.project_manager import ProjectManager
from utils.logger import log


class TopBar(QWidget):
    """Custom top bar with menu tabs and window controls."""

    tab_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet("""
            QWidget {
                background-color: #0f0f23;
                border-bottom: 1px solid #2a2a5e;
            }
        """)
        self._setup_ui()
        self._active_tab = "Editor"

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(4)

        # App icon/name
        app_label = QLabel("VideoEditor Pro")
        app_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        app_label.setStyleSheet("color: #4A90D9; background: transparent; border: none;")
        layout.addWidget(app_label)

        layout.addSpacing(24)

        # Main navigation tabs
        self._tab_buttons = {}
        tabs = ["Editor", "Local TTS", "Cloud TTS", "Download"]
        for tab_name in tabs:
            btn = QPushButton(tab_name)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(36)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #888888;
                    border: none;
                    border-bottom: 2px solid transparent;
                    padding: 6px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    color: #c0c0c0;
                }
                QPushButton:checked {
                    color: #4A90D9;
                    border-bottom: 2px solid #4A90D9;
                    font-weight: 600;
                }
            """)
            btn.clicked.connect(lambda checked, name=tab_name: self._on_tab_clicked(name))
            self._tab_buttons[tab_name] = btn
            layout.addWidget(btn)

        # Set Editor as default active
        self._tab_buttons["Editor"].setChecked(True)

        layout.addStretch()

        # Social icons (fake)
        social_icons = ["🌐", "📺", "💬"]
        for icon in social_icons:
            lbl = QLabel(icon)
            lbl.setStyleSheet("font-size: 16px; background: transparent; border: none; padding: 0 4px;")
            lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            layout.addWidget(lbl)

        layout.addSpacing(12)

        # Language dropdown
        self.cmb_language = QComboBox()
        self.cmb_language.addItems(["ENG", "VIE", "CHN", "JPN", "KOR"])
        self.cmb_language.setFixedWidth(80)
        self.cmb_language.setStyleSheet("""
            QComboBox {
                background: #1a1a3e;
                color: #c0c0c0;
                border: 1px solid #2a2a5e;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.cmb_language)

        layout.addSpacing(12)

        # Window controls
        for text, color, action in [
            ("─", "#F5A623", "minimize"),
            ("□", "#4A90D9", "maximize"),
            ("✕", "#D94A4A", "close"),
        ]:
            btn = QPushButton(text)
            btn.setFixedSize(32, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {color};
                    border: none;
                    font-size: 14px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {color}30;
                    border-radius: 4px;
                }}
            """)
            if action == "minimize":
                btn.clicked.connect(lambda: self.window().showMinimized())
            elif action == "maximize":
                btn.clicked.connect(self._toggle_maximize)
            elif action == "close":
                btn.clicked.connect(lambda: self.window().close())
            layout.addWidget(btn)

    def _toggle_maximize(self):
        win = self.window()
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()

    def _on_tab_clicked(self, name: str):
        for tab_name, btn in self._tab_buttons.items():
            btn.setChecked(tab_name == name)
        self._active_tab = name
        self.tab_changed.emit(name)


class LeftPanel(QWidget):
    """Left panel - Project list with search and sort."""

    project_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_manager = ProjectManager()
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)
        self._setup_ui()
        self._refresh_projects()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("Projects")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        title.setStyleSheet("color: #ffffff; background: transparent;")
        header.addWidget(title)

        header.addStretch()

        self.btn_new = AnimatedButton("+ New", color="#4AD97A")
        self.btn_new.setFixedHeight(30)
        self.btn_new.setFixedWidth(70)
        self.btn_new.clicked.connect(self._new_project)
        header.addWidget(self.btn_new)

        layout.addLayout(header)

        # Search
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search projects...")
        self.txt_search.textChanged.connect(self._on_search)
        layout.addWidget(self.txt_search)

        # Sort
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Sort:"))
        self.cmb_sort = QComboBox()
        self.cmb_sort.addItems(["Date", "Name", "Resolution"])
        self.cmb_sort.currentTextChanged.connect(lambda: self._refresh_projects())
        sort_layout.addWidget(self.cmb_sort)
        layout.addLayout(sort_layout)

        # Project list
        self.project_list = QListWidget()
        self.project_list.setStyleSheet("""
            QListWidget::item {
                padding: 10px 8px;
                border-radius: 6px;
                margin: 2px 0;
            }
        """)
        self.project_list.currentItemChanged.connect(self._on_project_selected)
        layout.addWidget(self.project_list)

    def _refresh_projects(self):
        self.project_list.clear()
        sort_by = self.cmb_sort.currentText().lower()
        projects = self.project_manager.get_projects(sort_by=sort_by)
        for proj in projects:
            item = QListWidgetItem(f"📁 {proj.name}")
            item.setData(Qt.ItemDataRole.UserRole, proj)
            item.setToolTip(f"Resolution: {proj.resolution}\nCreated: {proj.created[:10]}")
            self.project_list.addItem(item)

    def _new_project(self):
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Project", "Project name:")
        if ok and name:
            self.project_manager.create_project(name)
            self._refresh_projects()

    def _on_search(self, text: str):
        for i in range(self.project_list.count()):
            item = self.project_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def _on_project_selected(self, current, previous):
        if current:
            proj = current.data(Qt.ItemDataRole.UserRole)
            if proj:
                self.project_selected.emit(proj.name)


class CenterPreview(QWidget):
    """Center panel - video preview area."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video preview area
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet("""
            QFrame {
                background-color: #000000;
                border: 1px solid #2a2a5e;
                border-radius: 4px;
            }
        """)
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_preview = QLabel("No Video Loaded")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_preview.setFont(QFont("Segoe UI", 16))
        self.lbl_preview.setStyleSheet("color: #555555; background: transparent; border: none;")
        preview_layout.addWidget(self.lbl_preview)

        self.lbl_hint = QLabel("Import a video file to start editing")
        self.lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hint.setStyleSheet("color: #333333; font-size: 12px; background: transparent; border: none;")
        preview_layout.addWidget(self.lbl_hint)

        layout.addWidget(self.preview_frame)

        # Control bar
        control_bar = QWidget()
        control_bar.setFixedHeight(44)
        control_bar.setStyleSheet("background-color: #16163a; border-top: 1px solid #2a2a5e;")
        ctrl_layout = QHBoxLayout(control_bar)
        ctrl_layout.setContentsMargins(12, 4, 12, 4)

        # Play controls
        self.btn_prev_frame = QPushButton("⏮")
        self.btn_prev_frame.setFixedSize(32, 30)
        ctrl_layout.addWidget(self.btn_prev_frame)

        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(40, 30)
        self.btn_play.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 16px;
            }
            QPushButton:hover { background-color: #5AA0E9; }
        """)
        ctrl_layout.addWidget(self.btn_play)

        self.btn_next_frame = QPushButton("⏭")
        self.btn_next_frame.setFixedSize(32, 30)
        ctrl_layout.addWidget(self.btn_next_frame)

        ctrl_layout.addSpacing(16)

        # Time display
        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setStyleSheet("color: #4A90D9; font-family: monospace; font-size: 14px; background: transparent;")
        ctrl_layout.addWidget(self.lbl_time)

        ctrl_layout.addStretch()

        # Volume
        from PySide6.QtWidgets import QSlider
        ctrl_layout.addWidget(QLabel("🔊"))
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setFixedWidth(80)
        self.slider_volume.setMinimum(0)
        self.slider_volume.setMaximum(100)
        self.slider_volume.setValue(75)
        ctrl_layout.addWidget(self.slider_volume)

        # Fullscreen
        self.btn_fullscreen = QPushButton("⛶")
        self.btn_fullscreen.setFixedSize(32, 30)
        self.btn_fullscreen.setToolTip("Fullscreen")
        ctrl_layout.addWidget(self.btn_fullscreen)

        layout.addWidget(control_bar)


class RightPanel(QWidget):
    """Right panel with tab system for all editing tools."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(350)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # Create all tabs
        self.inspector_tab = InspectorTab()
        self.captions_tab = CaptionsTab()
        self.subtitle_translator_tab = SubtitleTranslatorTab()
        self.ai_agent_tab = AIAgentTab()
        self.ocr_setting_tab = OCRSettingTab()
        self.music_tab = MusicTab()
        self.export_options_tab = ExportOptionsTab()

        # Add tabs
        self.tab_widget.addTab(self.inspector_tab, "Inspector")
        self.tab_widget.addTab(self.captions_tab, "Captions")
        self.tab_widget.addTab(self.subtitle_translator_tab, "Translator")
        self.tab_widget.addTab(self.ai_agent_tab, "AI Agent")
        self.tab_widget.addTab(self.ocr_setting_tab, "OCR")
        self.tab_widget.addTab(self.music_tab, "Music")
        self.tab_widget.addTab(self.export_options_tab, "Export")

        layout.addWidget(self.tab_widget)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("VideoEditor Pro")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)

        # Apply dark theme
        self.setStyleSheet(DARK_THEME)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        self.top_bar = TopBar()
        self.top_bar.tab_changed.connect(self._on_main_tab_changed)
        main_layout.addWidget(self.top_bar)

        # Main content area (stacked for main tabs)
        self.content_stack = QStackedWidget()

        # ===== EDITOR PAGE =====
        editor_page = QWidget()
        editor_layout = QVBoxLayout(editor_page)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(0)

        # Top content splitter (left panel, center preview, right panel)
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.left_panel = LeftPanel()
        top_splitter.addWidget(self.left_panel)

        self.center_preview = CenterPreview()
        top_splitter.addWidget(self.center_preview)

        self.right_panel = RightPanel()
        top_splitter.addWidget(self.right_panel)

        top_splitter.setSizes([240, 580, 380])

        # Main vertical splitter (content + timeline)
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.addWidget(top_splitter)

        self.timeline = TimelineWidget()
        self.timeline.setMinimumHeight(150)
        v_splitter.addWidget(self.timeline)

        v_splitter.setSizes([550, 200])

        editor_layout.addWidget(v_splitter)
        self.content_stack.addWidget(editor_page)

        # ===== LOCAL TTS PAGE =====
        local_tts_page = QWidget()
        local_tts_layout = QHBoxLayout(local_tts_page)
        local_tts_layout.setContentsMargins(0, 0, 0, 0)

        local_tts_scroll = QScrollArea()
        local_tts_scroll.setWidgetResizable(True)
        self.local_tts_tab = LocalTTSTab()
        local_tts_scroll.setWidget(self.local_tts_tab)
        local_tts_layout.addWidget(local_tts_scroll)

        self.content_stack.addWidget(local_tts_page)

        # ===== CLOUD TTS PAGE =====
        cloud_tts_page = QWidget()
        cloud_tts_layout = QHBoxLayout(cloud_tts_page)
        cloud_tts_layout.setContentsMargins(0, 0, 0, 0)

        cloud_tts_scroll = QScrollArea()
        cloud_tts_scroll.setWidgetResizable(True)
        self.cloud_tts_tab = CloudTTSTab()
        cloud_tts_scroll.setWidget(self.cloud_tts_tab)
        cloud_tts_layout.addWidget(cloud_tts_scroll)

        self.content_stack.addWidget(cloud_tts_page)

        # ===== DOWNLOAD PAGE =====
        download_page = QWidget()
        download_layout = QHBoxLayout(download_page)
        download_layout.setContentsMargins(0, 0, 0, 0)

        self.download_tab = DownloadTab()
        download_layout.addWidget(self.download_tab)

        self.content_stack.addWidget(download_page)

        # ===== AUDIO PAGE (accessed from menu) =====
        audio_page = QWidget()
        audio_layout = QHBoxLayout(audio_page)
        audio_layout.setContentsMargins(0, 0, 0, 0)

        audio_scroll = QScrollArea()
        audio_scroll.setWidgetResizable(True)
        self.audio_panel = AudioPanel()
        audio_scroll.setWidget(self.audio_panel)
        audio_layout.addWidget(audio_scroll)

        self.content_stack.addWidget(audio_page)

        main_layout.addWidget(self.content_stack)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Toast notification
        self.toast = Toast(central)

        # Tab mapping
        self._tab_map = {
            "Editor": 0,
            "Local TTS": 1,
            "Cloud TTS": 2,
            "Download": 3,
            "Audio": 4,
        }

        log.info("Main window initialized")

    def _on_main_tab_changed(self, tab_name: str):
        idx = self._tab_map.get(tab_name, 0)
        self.content_stack.setCurrentIndex(idx)
        self.statusBar().showMessage(f"Switched to {tab_name}")
        log.info(f"Tab changed: {tab_name}")

    def show_toast(self, message: str, level: str = "info"):
        """Show a toast notification."""
        self.toast.show_message(message, level)
