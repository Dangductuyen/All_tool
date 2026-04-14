"""
Captions tab - manage and edit subtitle captions.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QComboBox, QAbstractItemView, QFileDialog
)
from PySide6.QtCore import Qt

from ui.widgets.animated_button import AnimatedButton
from services.subtitle_service import SubtitleService


class CaptionsTab(QWidget):
    """Captions editing tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Captions")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # Actions
        action_layout = QHBoxLayout()
        self.btn_load = AnimatedButton("Load SRT", color="#4A90D9")
        self.btn_load.clicked.connect(self._load_srt)
        action_layout.addWidget(self.btn_load)

        self.btn_save = QPushButton("Save SRT")
        self.btn_save.clicked.connect(self._save_srt)
        action_layout.addWidget(self.btn_save)

        self.btn_add = QPushButton("+ Add Entry")
        self.btn_add.clicked.connect(self._add_entry)
        action_layout.addWidget(self.btn_add)

        self.btn_delete = QPushButton("Delete Selected")
        self.btn_delete.setObjectName("dangerButton")
        self.btn_delete.clicked.connect(self._delete_selected)
        action_layout.addWidget(self.btn_delete)

        action_layout.addStretch()
        layout.addLayout(action_layout)

        # Caption style settings
        style_group = QGroupBox("Caption Style")
        style_layout = QHBoxLayout(style_group)

        style_layout.addWidget(QLabel("Font:"))
        self.cmb_font = QComboBox()
        self.cmb_font.addItems(["Arial", "Noto Sans", "Roboto", "Open Sans", "Montserrat"])
        style_layout.addWidget(self.cmb_font)

        style_layout.addWidget(QLabel("Size:"))
        self.cmb_size = QComboBox()
        self.cmb_size.addItems(["16", "20", "24", "28", "32", "36", "40"])
        self.cmb_size.setCurrentText("24")
        style_layout.addWidget(self.cmb_size)

        style_layout.addWidget(QLabel("Position:"))
        self.cmb_pos = QComboBox()
        self.cmb_pos.addItems(["Bottom", "Top", "Center"])
        style_layout.addWidget(self.cmb_pos)

        style_layout.addStretch()
        layout.addWidget(style_group)

        # Captions table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Start", "End", "Text"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Status
        self.lbl_status = QLabel("0 captions")
        self.lbl_status.setObjectName("subtitleLabel")
        layout.addWidget(self.lbl_status)

    def _load_srt(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load SRT", "", "SRT Files (*.srt);;All Files (*)"
        )
        if file_path:
            self._entries = SubtitleService.load_srt(file_path)
            self._refresh_table()

    def _refresh_table(self):
        self.table.setRowCount(len(self._entries))
        for row, entry in enumerate(self._entries):
            self.table.setItem(row, 0, QTableWidgetItem(str(entry.index)))
            self.table.setItem(row, 1, QTableWidgetItem(entry.start))
            self.table.setItem(row, 2, QTableWidgetItem(entry.end))
            self.table.setItem(row, 3, QTableWidgetItem(entry.text))
        self.lbl_status.setText(f"{len(self._entries)} captions")

    def _save_srt(self):
        if not self._entries:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save SRT", "", "SRT Files (*.srt)"
        )
        if file_path:
            # Read back edits from table
            for row in range(self.table.rowCount()):
                if row < len(self._entries):
                    text_item = self.table.item(row, 3)
                    if text_item:
                        self._entries[row].text = text_item.text()
            SubtitleService.save_srt(self._entries, file_path)

    def _add_entry(self):
        from services.subtitle_service import SubtitleEntry
        idx = len(self._entries) + 1
        entry = SubtitleEntry(idx, "00:00:00,000", "00:00:02,000", "New caption")
        self._entries.append(entry)
        self._refresh_table()

    def _delete_selected(self):
        rows = sorted(set(item.row() for item in self.table.selectedItems()), reverse=True)
        for row in rows:
            if row < len(self._entries):
                self._entries.pop(row)
        # Re-index
        for i, entry in enumerate(self._entries):
            entry.index = i + 1
        self._refresh_table()
