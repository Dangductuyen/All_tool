"""
SRT Translator Pro Tab - Full-featured subtitle translator with multi-AI support.

Features:
- Sidebar: AI selection, API key management, model selection, threads, batch size
- Main area: SRT preview (original vs translated) with drag & drop
- Log panel: Detailed debug logs with timestamps
- Format checking with strict mode
- Buttons: Load model, Get API key, Check format, Translate, Stop, Export, Exit
"""
import os
import webbrowser
from datetime import datetime
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QGroupBox, QFileDialog, QProgressBar,
    QSpinBox, QSplitter, QListWidget, QListWidgetItem, QLineEdit,
    QCheckBox, QFrame, QScrollArea, QMessageBox, QApplication,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QMimeData, QThread
from PySide6.QtGui import QFont, QColor, QDragEnterEvent, QDropEvent

from ui.widgets.animated_button import AnimatedButton
from services.subtitle_service import SubtitleService, SubtitleEntry
from services.translator_service import (
    TranslatorService, KeyStatus, FormatCheckResult,
    TRANSLATOR_ENGINES, SUPPORTED_LANGUAGES, API_KEY_LINKS,
    DEFAULT_MODELS,
)
from utils.logger import log


class APIKeyValidateWorker(QThread):
    """Worker to validate API key in background."""
    result = Signal(str, str, bool, str)  # engine, key, is_valid, message

    def __init__(self, engine: str, key: str, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.key = key

    def run(self):
        is_valid, message = TranslatorService.validate_key(self.engine, self.key)
        self.result.emit(self.engine, self.key, is_valid, message)


class ModelLoadWorker(QThread):
    """Worker to load models in background."""
    result = Signal(str, list)  # engine, model_list

    def __init__(self, engine: str, api_key: str, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.api_key = api_key

    def run(self):
        models = TranslatorService.load_models(self.engine, self.api_key)
        self.result.emit(self.engine, models)


class SubtitleTranslatorTab(QWidget):
    """Complete SRT Translator Pro tab with all features."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._entries: List[SubtitleEntry] = []
        self._translated: List[SubtitleEntry] = []
        self._worker = None
        self._validate_worker = None
        self._model_worker = None
        self._current_file = ""
        self._output_dir = ""
        self._strict_mode = False
        self._key_manager = TranslatorService.get_key_manager()
        self._setup_ui()
        self._refresh_key_list()

    # ================================================================
    # UI Setup
    # ================================================================

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ===== LEFT SIDEBAR =====
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)

        # ===== RIGHT CONTENT =====
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(8)

        # Title
        title = QLabel("SRT Translator Pro")
        title.setObjectName("titleLabel")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        content_layout.addWidget(title)

        # File info bar
        file_bar = self._create_file_bar()
        content_layout.addLayout(file_bar)

        # Main splitter: Preview + Log
        v_splitter = QSplitter(Qt.Orientation.Vertical)

        # Preview area (Original vs Translated)
        preview_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Original panel
        orig_widget = QWidget()
        orig_layout = QVBoxLayout(orig_widget)
        orig_layout.setContentsMargins(0, 0, 4, 0)
        orig_header = QHBoxLayout()
        orig_label = QLabel("Original")
        orig_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        orig_header.addWidget(orig_label)
        self.lbl_orig_count = QLabel("0 blocks")
        self.lbl_orig_count.setObjectName("subtitleLabel")
        orig_header.addStretch()
        orig_header.addWidget(self.lbl_orig_count)
        orig_layout.addLayout(orig_header)

        self.txt_original = QTextEdit()
        self.txt_original.setReadOnly(True)
        self.txt_original.setPlaceholderText("Keo tha file .srt vao day hoac click 'Load SRT'...")
        self.txt_original.setFont(QFont("Consolas", 11))
        orig_layout.addWidget(self.txt_original)
        preview_splitter.addWidget(orig_widget)

        # Translated panel
        trans_widget = QWidget()
        trans_layout = QVBoxLayout(trans_widget)
        trans_layout.setContentsMargins(4, 0, 0, 0)
        trans_header = QHBoxLayout()
        trans_label = QLabel("Translated")
        trans_label.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        trans_header.addWidget(trans_label)
        self.lbl_trans_count = QLabel("0 blocks")
        self.lbl_trans_count.setObjectName("subtitleLabel")
        trans_header.addStretch()
        trans_header.addWidget(self.lbl_trans_count)
        trans_layout.addLayout(trans_header)

        self.txt_translated = QTextEdit()
        self.txt_translated.setReadOnly(True)
        self.txt_translated.setPlaceholderText("Ban dich se hien thi o day...")
        self.txt_translated.setFont(QFont("Consolas", 11))
        trans_layout.addWidget(self.txt_translated)
        preview_splitter.addWidget(trans_widget)

        v_splitter.addWidget(preview_splitter)

        # Log panel
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        log_layout.setContentsMargins(0, 8, 0, 0)
        log_header = QHBoxLayout()
        log_label = QLabel("Debug Log")
        log_label.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        log_header.addWidget(log_label)
        log_header.addStretch()
        self.btn_clear_log = QPushButton("Clear")
        self.btn_clear_log.setFixedHeight(26)
        self.btn_clear_log.clicked.connect(lambda: self.txt_log.clear())
        log_header.addWidget(self.btn_clear_log)
        log_layout.addLayout(log_header)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(200)
        self.txt_log.setFont(QFont("Consolas", 10))
        self.txt_log.setPlaceholderText("Log debug se hien thi o day...")
        log_layout.addWidget(self.txt_log)
        v_splitter.addWidget(log_widget)

        v_splitter.setSizes([500, 180])
        content_layout.addWidget(v_splitter)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setFixedHeight(22)
        content_layout.addWidget(self.progress)

        # Status bar
        self.lbl_status = QLabel("San sang")
        self.lbl_status.setObjectName("subtitleLabel")
        content_layout.addWidget(self.lbl_status)

        # Action buttons bar
        action_bar = self._create_action_bar()
        content_layout.addLayout(action_bar)

        main_layout.addWidget(content, stretch=1)

    def _create_sidebar(self) -> QWidget:
        """Create the left sidebar with all controls."""
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFixedWidth(320)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        sidebar_inner = QWidget()
        layout = QVBoxLayout(sidebar_inner)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # ---- AI Engine Selection ----
        engine_group = QGroupBox("AI Engine")
        engine_layout = QVBoxLayout(engine_group)

        self.cmb_engine = QComboBox()
        for key, info in TRANSLATOR_ENGINES.items():
            self.cmb_engine.addItem(info["name"], key)
        self.cmb_engine.currentIndexChanged.connect(self._on_engine_changed)
        engine_layout.addWidget(self.cmb_engine)

        # Get API Key button
        self.btn_get_key = AnimatedButton("Get API Key", color="#F5A623")
        self.btn_get_key.setFixedHeight(32)
        self.btn_get_key.clicked.connect(self._open_api_key_link)
        engine_layout.addWidget(self.btn_get_key)

        layout.addWidget(engine_group)

        # ---- API Key Management ----
        key_group = QGroupBox("API Keys")
        key_layout = QVBoxLayout(key_group)

        # Key input
        key_input_row = QHBoxLayout()
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setPlaceholderText("Nhap API key...")
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        key_input_row.addWidget(self.txt_api_key)

        self.btn_add_key = QPushButton("+")
        self.btn_add_key.setFixedSize(32, 32)
        self.btn_add_key.setToolTip("Them API key")
        self.btn_add_key.clicked.connect(self._add_api_key)
        key_input_row.addWidget(self.btn_add_key)
        key_layout.addLayout(key_input_row)

        # Key list
        self.list_keys = QListWidget()
        self.list_keys.setMaximumHeight(120)
        self.list_keys.setFont(QFont("Consolas", 10))
        key_layout.addWidget(self.list_keys)

        # Key action buttons
        key_btn_row = QHBoxLayout()
        self.btn_validate_key = QPushButton("Validate")
        self.btn_validate_key.setFixedHeight(28)
        self.btn_validate_key.clicked.connect(self._validate_selected_key)
        key_btn_row.addWidget(self.btn_validate_key)

        self.btn_remove_key = QPushButton("Remove")
        self.btn_remove_key.setFixedHeight(28)
        self.btn_remove_key.setObjectName("dangerButton")
        self.btn_remove_key.clicked.connect(self._remove_selected_key)
        key_btn_row.addWidget(self.btn_remove_key)
        key_layout.addLayout(key_btn_row)

        layout.addWidget(key_group)

        # ---- Model Selection ----
        model_group = QGroupBox("Model")
        model_layout = QVBoxLayout(model_group)

        self.cmb_model = QComboBox()
        model_layout.addWidget(self.cmb_model)

        self.btn_load_model = AnimatedButton("Load Models from API", color="#4A90D9")
        self.btn_load_model.setFixedHeight(32)
        self.btn_load_model.clicked.connect(self._load_models_from_api)
        model_layout.addWidget(self.btn_load_model)

        self.lbl_model_status = QLabel("")
        self.lbl_model_status.setObjectName("subtitleLabel")
        self.lbl_model_status.setWordWrap(True)
        model_layout.addWidget(self.lbl_model_status)

        # Load default models after lbl_model_status is created
        self._load_default_models()

        layout.addWidget(model_group)

        # ---- Language Selection ----
        lang_group = QGroupBox("Language")
        lang_layout = QVBoxLayout(lang_group)

        lang_layout.addWidget(QLabel("Source:"))
        self.cmb_source = QComboBox()
        for code, name in SUPPORTED_LANGUAGES:
            self.cmb_source.addItem(name, code)
        lang_layout.addWidget(self.cmb_source)

        lang_layout.addWidget(QLabel("Target:"))
        self.cmb_target = QComboBox()
        for code, name in SUPPORTED_LANGUAGES:
            self.cmb_target.addItem(name, code)
        # Default to Vietnamese
        idx = self.cmb_target.findData("vi")
        if idx >= 0:
            self.cmb_target.setCurrentIndex(idx)
        lang_layout.addWidget(self.cmb_target)

        layout.addWidget(lang_group)

        # ---- Performance Settings ----
        perf_group = QGroupBox("Performance")
        perf_layout = QVBoxLayout(perf_group)

        perf_layout.addWidget(QLabel("Batch Size:"))
        self.spin_batch = QSpinBox()
        self.spin_batch.setMinimum(1)
        self.spin_batch.setMaximum(50)
        self.spin_batch.setValue(10)
        self.spin_batch.setToolTip("So dong subtitle gui cung 1 request (5-20 khuyen nghi)")
        perf_layout.addWidget(self.spin_batch)

        perf_layout.addWidget(QLabel("Threads:"))
        self.spin_threads = QSpinBox()
        self.spin_threads.setMinimum(1)
        self.spin_threads.setMaximum(20)
        self.spin_threads.setValue(1)
        self.spin_threads.setToolTip("So luong xu ly song song (1-20)")
        perf_layout.addWidget(self.spin_threads)

        layout.addWidget(perf_group)

        # ---- Format Options ----
        format_group = QGroupBox("Format Options")
        format_layout = QVBoxLayout(format_group)

        self.chk_strict = QCheckBox("Strict Mode")
        self.chk_strict.setToolTip("Sai format = khong cho export")
        self.chk_strict.toggled.connect(lambda v: setattr(self, '_strict_mode', v))
        format_layout.addWidget(self.chk_strict)

        layout.addWidget(format_group)

        layout.addStretch()

        sidebar_scroll.setWidget(sidebar_inner)
        return sidebar_scroll

    def _create_file_bar(self) -> QHBoxLayout:
        """Create the file info/load bar."""
        bar = QHBoxLayout()

        self.btn_load = AnimatedButton("Load SRT", color="#4A90D9")
        self.btn_load.setFixedHeight(36)
        self.btn_load.clicked.connect(self._load_srt)
        bar.addWidget(self.btn_load)

        self.btn_output_dir = QPushButton("Output Dir")
        self.btn_output_dir.setFixedHeight(36)
        self.btn_output_dir.clicked.connect(self._select_output_dir)
        bar.addWidget(self.btn_output_dir)

        self.lbl_file = QLabel("Chua load file")
        self.lbl_file.setObjectName("subtitleLabel")
        self.lbl_file.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bar.addWidget(self.lbl_file)

        return bar

    def _create_action_bar(self) -> QHBoxLayout:
        """Create the bottom action buttons bar."""
        bar = QHBoxLayout()

        self.btn_check_format = QPushButton("Check Format")
        self.btn_check_format.setFixedHeight(36)
        self.btn_check_format.clicked.connect(self._check_format)
        bar.addWidget(self.btn_check_format)

        self.btn_translate = AnimatedButton("Dich", color="#4AD97A", style_id="successButton")
        self.btn_translate.setFixedHeight(40)
        self.btn_translate.clicked.connect(self._start_translate)
        bar.addWidget(self.btn_translate)

        self.btn_stop = QPushButton("Dung")
        self.btn_stop.setFixedHeight(36)
        self.btn_stop.setObjectName("dangerButton")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_translate)
        bar.addWidget(self.btn_stop)

        self.btn_export = AnimatedButton("Xuat File", color="#F5A623")
        self.btn_export.setFixedHeight(36)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_srt)
        bar.addWidget(self.btn_export)

        return bar

    # ================================================================
    # Drag & Drop
    # ================================================================

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.srt'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.srt'):
                self._load_srt_file(file_path)
                break

    # ================================================================
    # File Operations
    # ================================================================

    def _load_srt(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load SRT File", "",
            "SRT Files (*.srt);;All Files (*)"
        )
        if file_path:
            self._load_srt_file(file_path)

    def _load_srt_file(self, file_path: str):
        """Load and display an SRT file."""
        try:
            self._entries = SubtitleService.load_srt(file_path)
            self._current_file = file_path
            self._translated = []

            srt_text = SubtitleService.entries_to_srt(self._entries)
            self.txt_original.setPlainText(srt_text)
            self.txt_translated.clear()
            self.lbl_file.setText(f"File: {os.path.basename(file_path)} ({len(self._entries)} blocks)")
            self.lbl_orig_count.setText(f"{len(self._entries)} blocks")
            self.lbl_trans_count.setText("0 blocks")
            self.btn_export.setEnabled(False)

            self._add_log(f"Da load file: {file_path} ({len(self._entries)} blocks)")
            self.lbl_status.setText(f"Da load {len(self._entries)} subtitle blocks")

            # Set default output dir
            if not self._output_dir:
                self._output_dir = os.path.dirname(file_path)

        except Exception as e:
            self._add_log(f"LOI load file: {e}", level="error")
            self.lbl_file.setText(f"Loi: {e}")
            QMessageBox.critical(self, "Loi Load File",
                                 f"Khong the load file SRT:\n\n{e}")

    def _select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self, "Chon thu muc output",
            self._output_dir or os.path.expanduser("~")
        )
        if dir_path:
            self._output_dir = dir_path
            self._add_log(f"Output dir: {dir_path}")
            self.lbl_status.setText(f"Output: {dir_path}")

    # ================================================================
    # API Key Management
    # ================================================================

    def _on_engine_changed(self, index: int):
        """Handle engine change."""
        self._load_default_models()
        self._refresh_key_list()

    def _get_current_engine(self) -> str:
        return self.cmb_engine.currentData() or "gemini"

    def _add_api_key(self):
        """Add a new API key for the current engine."""
        key = self.txt_api_key.text().strip()
        if not key:
            QMessageBox.warning(self, "API Key", "Vui long nhap API key")
            return

        engine = self._get_current_engine()
        if self._key_manager.add_key(engine, key):
            self.txt_api_key.clear()
            self._refresh_key_list()
            self._add_log(f"Da them API key cho {engine}")
        else:
            QMessageBox.warning(self, "API Key", "Key da ton tai hoac engine khong hop le")

    def _remove_selected_key(self):
        """Remove selected API key."""
        item = self.list_keys.currentItem()
        if not item:
            return
        key = item.data(Qt.ItemDataRole.UserRole)
        if not key:
            return

        engine = self._get_current_engine()
        if self._key_manager.remove_key(engine, key):
            self._refresh_key_list()
            self._add_log(f"Da xoa API key khoi {engine}")

    def _validate_selected_key(self):
        """Validate the selected API key."""
        item = self.list_keys.currentItem()
        if not item:
            # Try to validate the key in the input field
            key = self.txt_api_key.text().strip()
            if not key:
                QMessageBox.information(self, "Validate", "Chon key trong list hoac nhap key moi")
                return
        else:
            key = item.data(Qt.ItemDataRole.UserRole)
            if not key:
                return

        engine = self._get_current_engine()
        self.btn_validate_key.setEnabled(False)
        self.btn_validate_key.setText("Dang kiem tra...")

        self._validate_worker = APIKeyValidateWorker(engine, key)
        self._validate_worker.result.connect(self._on_key_validated)
        self._validate_worker.start()

    def _on_key_validated(self, engine: str, key: str, is_valid: bool, message: str):
        """Handle key validation result."""
        self.btn_validate_key.setEnabled(True)
        self.btn_validate_key.setText("Validate")

        if is_valid:
            self._key_manager.update_key_status(engine, key, KeyStatus.VALID)
            self._add_log(f"API key {engine}: VALID - {message}")
        else:
            self._key_manager.update_key_status(engine, key, KeyStatus.INVALID, message)
            self._add_log(f"API key {engine}: INVALID - {message}", level="error")

        self._refresh_key_list()

    def _refresh_key_list(self):
        """Refresh the API key list display."""
        self.list_keys.clear()
        engine = self._get_current_engine()
        keys = self._key_manager.get_keys(engine)

        for entry in keys:
            # Show masked key with status icon
            masked = entry.key[:8] + "..." + entry.key[-4:] if len(entry.key) > 12 else entry.key
            status_icons = {
                KeyStatus.VALID: "[OK]",
                KeyStatus.INVALID: "[X]",
                KeyStatus.QUOTA_EXCEEDED: "[!]",
                KeyStatus.UNCHECKED: "[?]",
            }
            icon = status_icons.get(entry.status, "[?]")
            display = f"{icon} {masked}"

            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, entry.key)

            # Color coding
            if entry.status == KeyStatus.VALID:
                item.setForeground(QColor("#4AD97A"))
            elif entry.status == KeyStatus.INVALID:
                item.setForeground(QColor("#D94A4A"))
            elif entry.status == KeyStatus.QUOTA_EXCEEDED:
                item.setForeground(QColor("#F5A623"))
            else:
                item.setForeground(QColor("#888888"))

            if entry.last_error:
                item.setToolTip(entry.last_error)

            self.list_keys.addItem(item)

    def _open_api_key_link(self):
        """Open the API key registration link for current engine."""
        engine = self._get_current_engine()
        url = API_KEY_LINKS.get(engine, "")
        if url:
            webbrowser.open(url)
            self._add_log(f"Mo link API key: {url}")

    # ================================================================
    # Model Loading
    # ================================================================

    def _load_default_models(self):
        """Load default models for the current engine."""
        engine = self._get_current_engine()
        models = DEFAULT_MODELS.get(engine, [])
        self.cmb_model.clear()
        for m in models:
            self.cmb_model.addItem(m)
        self.lbl_model_status.setText(f"Default models ({len(models)})")

    def _load_models_from_api(self):
        """Load models from API."""
        engine = self._get_current_engine()
        api_key = self._key_manager.get_best_key(engine)
        if not api_key:
            QMessageBox.warning(self, "Load Models",
                                "Can API key de load models. Them key truoc.")
            return

        self.btn_load_model.setEnabled(False)
        self.lbl_model_status.setText("Dang load models...")
        self._add_log(f"Loading models tu {engine} API...")

        self._model_worker = ModelLoadWorker(engine, api_key)
        self._model_worker.result.connect(self._on_models_loaded)
        self._model_worker.start()

    def _on_models_loaded(self, engine: str, models: list):
        """Handle loaded models."""
        self.btn_load_model.setEnabled(True)

        if models:
            self.cmb_model.clear()
            for m in models:
                self.cmb_model.addItem(m)
            self.lbl_model_status.setText(f"Da load {len(models)} models tu API")
            self._add_log(f"Loaded {len(models)} models tu {engine}: {', '.join(models[:5])}...")
        else:
            self.lbl_model_status.setText("Khong tim thay model, dung defaults")
            self._add_log(f"Khong load duoc models tu {engine}, dung defaults", level="warning")

    # ================================================================
    # Translation
    # ================================================================

    def _start_translate(self):
        """Start translation process."""
        if not self._entries:
            QMessageBox.information(self, "Dich", "Vui long load file SRT truoc")
            return

        engine = self._get_current_engine()
        api_key = self._key_manager.get_best_key(engine)
        if not api_key:
            QMessageBox.warning(self, "Dich",
                                f"Can API key cho {engine}.\n"
                                f"Them key trong phan 'API Keys' ben trai.")
            return

        model = self.cmb_model.currentText()
        if not model:
            QMessageBox.warning(self, "Dich", "Vui long chon model")
            return

        source = self.cmb_source.currentData()
        target = self.cmb_target.currentData()

        if source == target and source != "auto":
            QMessageBox.warning(self, "Dich", "Ngon ngu nguon va dich khong the giong nhau")
            return

        # Update UI state
        self.btn_translate.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_export.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.txt_translated.clear()

        batch_size = self.spin_batch.value()
        num_threads = self.spin_threads.value()

        self._add_log(f"Bat dau dich: {engine}/{model}, batch={batch_size}, threads={num_threads}")
        self._add_log(f"Ngon ngu: {source} -> {target}, {len(self._entries)} blocks")

        # Create and start worker
        self._worker = TranslatorService.create_worker(
            entries=self._entries,
            engine=engine,
            model=model,
            source_lang=source,
            target_lang=target,
            batch_size=batch_size,
            num_threads=num_threads,
        )
        self._worker.finished.connect(self._on_translated)
        self._worker.error.connect(self._on_error)
        self._worker.progress.connect(self._on_progress)
        self._worker.log_message.connect(lambda msg: self._add_log(msg))
        self._worker.block_error.connect(self._on_block_error)
        self._worker.start()

    def _stop_translate(self):
        """Stop translation."""
        if self._worker:
            self._worker.stop()
            self._add_log("Dang dung dich...")
            self.lbl_status.setText("Dang dung...")

    def _on_progress(self, value: int, status: str):
        """Handle progress update."""
        self.progress.setValue(value)
        self.lbl_status.setText(status)

    def _on_translated(self, entries: list):
        """Handle translation completion."""
        self._translated = entries

        # Display translated SRT
        srt_text = SubtitleService.entries_to_srt(entries)
        self.txt_translated.setPlainText(srt_text)
        self.lbl_trans_count.setText(f"{len(entries)} blocks")

        # Reset UI
        self.progress.setVisible(False)
        self.btn_translate.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_export.setEnabled(True)

        # Auto format check
        result = TranslatorService.check_format(self._entries, entries)
        if not result.is_valid:
            self._add_log(f"CANH BAO FORMAT: {len(result.errors)} loi", level="warning")
            for err in result.errors[:10]:
                self._add_log(f"  - {err}", level="warning")
            self.lbl_status.setText(f"Dich xong! {len(result.errors)} loi format")
            if self._strict_mode:
                self.btn_export.setEnabled(False)
                self._add_log("STRICT MODE: Khong cho export do loi format", level="error")
        else:
            self.lbl_status.setText(f"Dich thanh cong! {len(entries)} blocks")

        # Check for empty blocks
        if result.empty_blocks:
            self._add_log(f"Block rong: {result.empty_blocks}", level="warning")

        self._add_log(f"Hoan thanh! {len(entries)} blocks da dich")

    def _on_error(self, error: str):
        """Handle translation error."""
        self.lbl_status.setText(f"Loi: {error}")
        self.progress.setVisible(False)
        self.btn_translate.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self._add_log(f"LOI DICH: {error}", level="error")

        QMessageBox.critical(self, "Loi Dich",
                             f"Co loi xay ra khi dich:\n\n{error}")

    def _on_block_error(self, block_id: int, error_code: str, error_message: str):
        """Handle per-block translation error."""
        self._add_log(f"Block {block_id}: ERROR {error_code} - {error_message}", level="error")

    # ================================================================
    # Format Checking
    # ================================================================

    def _check_format(self):
        """Run format check on original or translated subtitles."""
        if self._translated and self._entries:
            result = TranslatorService.check_format(self._entries, self._translated)
            self._display_format_result(result)
        elif self._entries:
            # Validate original format
            srt_text = SubtitleService.entries_to_srt(self._entries)
            errors = SubtitleService.validate_srt(srt_text)
            if errors:
                self._add_log(f"Format check: {len(errors)} loi", level="warning")
                for err in errors:
                    self._add_log(f"  - {err}", level="warning")
                self.lbl_status.setText(f"Format: {len(errors)} loi")
            else:
                self._add_log("Format check: OK")
                self.lbl_status.setText("Format SRT hop le")
        else:
            QMessageBox.information(self, "Check Format", "Vui long load file SRT truoc")

    def _display_format_result(self, result: FormatCheckResult):
        """Display format check result."""
        self._add_log("=" * 50)
        self._add_log("KET QUA KIEM TRA FORMAT")
        self._add_log(f"  Input blocks: {result.input_block_count}")
        self._add_log(f"  Output blocks: {result.output_block_count}")
        self._add_log(f"  Hop le: {'CO' if result.is_valid else 'KHONG'}")

        if result.errors:
            self._add_log(f"  Loi ({len(result.errors)}):", level="error")
            for err in result.errors:
                self._add_log(f"    - {err}", level="error")

        if result.warnings:
            self._add_log(f"  Canh bao ({len(result.warnings)}):", level="warning")
            for w in result.warnings:
                self._add_log(f"    - {w}", level="warning")

        if result.missing_blocks:
            self._add_log(f"  Block thieu: {result.missing_blocks}", level="error")

        if result.empty_blocks:
            self._add_log(f"  Block rong: {result.empty_blocks}", level="warning")

        self._add_log("=" * 50)

        if result.is_valid:
            self.lbl_status.setText("Format OK!")
        else:
            self.lbl_status.setText(f"Format KHONG HOP LE: {len(result.errors)} loi")
            if self._strict_mode:
                self.btn_export.setEnabled(False)

    # ================================================================
    # Export
    # ================================================================

    def _export_srt(self):
        """Export translated SRT file."""
        if not self._translated:
            return

        # Strict mode check
        if self._strict_mode and self._entries:
            result = TranslatorService.check_format(self._entries, self._translated)
            if not result.is_valid:
                QMessageBox.critical(self, "Export",
                                     f"STRICT MODE: Khong the export do loi format.\n\n"
                                     f"Loi:\n" + "\n".join(result.errors[:5]))
                return

        # Determine default filename
        if self._current_file:
            base = os.path.splitext(os.path.basename(self._current_file))[0]
            target = self.cmb_target.currentData() or "translated"
            default_name = f"{base}_{target}.srt"
        else:
            default_name = "translated.srt"

        default_path = os.path.join(
            self._output_dir or os.path.expanduser("~"),
            default_name
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Xuat File SRT", default_path,
            "SRT Files (*.srt);;All Files (*)"
        )
        if file_path:
            try:
                SubtitleService.save_srt(self._translated, file_path)
                self._add_log(f"Da xuat file: {file_path}")
                self.lbl_status.setText(f"Da xuat: {file_path}")
                QMessageBox.information(self, "Export",
                                        f"Da xuat thanh cong!\n\n{file_path}")
            except Exception as e:
                self._add_log(f"LOI xuat file: {e}", level="error")
                QMessageBox.critical(self, "Loi Export",
                                     f"Khong the xuat file:\n\n{e}")

    # ================================================================
    # Log
    # ================================================================

    def _add_log(self, message: str, level: str = "info"):
        """Add a message to the debug log panel."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "info": "#c0c0c0",
            "warning": "#F5A623",
            "error": "#D94A4A",
            "success": "#4AD97A",
        }
        color = colors.get(level, "#c0c0c0")

        html = f'<span style="color: {color};">[{timestamp}] {message}</span>'
        self.txt_log.append(html)

        # Auto-scroll to bottom
        scrollbar = self.txt_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
