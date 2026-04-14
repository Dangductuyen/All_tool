"""
Dark theme stylesheet for the application (CapCut / Premiere Pro style).
"""

DARK_THEME = """
/* ======================== GLOBAL ======================== */
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", "Noto Sans", Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #4A90D9;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #0f0f23;
}

/* ======================== MENU BAR ======================== */
QMenuBar {
    background-color: #16163a;
    color: #c0c0c0;
    border-bottom: 1px solid #2a2a5e;
    padding: 2px;
    font-size: 13px;
}

QMenuBar::item {
    padding: 6px 16px;
    border-radius: 4px;
    margin: 2px;
}

QMenuBar::item:selected {
    background-color: #4A90D9;
    color: #ffffff;
}

QMenu {
    background-color: #1e1e42;
    border: 1px solid #3a3a6e;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 30px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #4A90D9;
    color: #ffffff;
}

/* ======================== BUTTONS ======================== */
QPushButton {
    background-color: #2a2a5e;
    color: #e0e0e0;
    border: 1px solid #3a3a6e;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 500;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #3a3a7e;
    border-color: #4A90D9;
}

QPushButton:pressed {
    background-color: #4A90D9;
    color: #ffffff;
}

QPushButton:disabled {
    background-color: #1a1a3e;
    color: #555555;
    border-color: #252550;
}

QPushButton#primaryButton {
    background-color: #4A90D9;
    color: #ffffff;
    border: none;
    font-weight: 600;
}

QPushButton#primaryButton:hover {
    background-color: #5AA0E9;
}

QPushButton#primaryButton:pressed {
    background-color: #3A80C9;
}

QPushButton#dangerButton {
    background-color: #D94A4A;
    color: #ffffff;
    border: none;
}

QPushButton#dangerButton:hover {
    background-color: #E95A5A;
}

QPushButton#successButton {
    background-color: #4AD97A;
    color: #1a1a2e;
    border: none;
    font-weight: 600;
}

QPushButton#successButton:hover {
    background-color: #5AE98A;
}

/* ======================== INPUT FIELDS ======================== */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #12122e;
    color: #e0e0e0;
    border: 1px solid #2a2a5e;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #4A90D9;
}

/* ======================== COMBO BOX ======================== */
QComboBox {
    background-color: #2a2a5e;
    color: #e0e0e0;
    border: 1px solid #3a3a6e;
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 24px;
}

QComboBox:hover {
    border-color: #4A90D9;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #e0e0e0;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e42;
    color: #e0e0e0;
    border: 1px solid #3a3a6e;
    border-radius: 4px;
    selection-background-color: #4A90D9;
    outline: 0;
}

/* ======================== SLIDERS ======================== */
QSlider::groove:horizontal {
    height: 6px;
    background: #2a2a5e;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #4A90D9;
    border: 2px solid #5AA0E9;
    width: 16px;
    height: 16px;
    margin: -6px 0;
    border-radius: 9px;
}

QSlider::handle:horizontal:hover {
    background: #5AA0E9;
    border-color: #6AB0F9;
}

QSlider::sub-page:horizontal {
    background: #4A90D9;
    border-radius: 3px;
}

/* ======================== SCROLL BARS ======================== */
QScrollBar:vertical {
    background: #12122e;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #3a3a6e;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #4A90D9;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #12122e;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #3a3a6e;
    border-radius: 5px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background: #4A90D9;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ======================== TAB WIDGET ======================== */
QTabWidget::pane {
    border: 1px solid #2a2a5e;
    border-radius: 6px;
    background-color: #16163a;
}

QTabBar::tab {
    background-color: #1a1a3e;
    color: #888888;
    border: 1px solid #2a2a5e;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: 500;
}

QTabBar::tab:selected {
    background-color: #16163a;
    color: #4A90D9;
    border-bottom-color: #16163a;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background-color: #22224e;
    color: #c0c0c0;
}

/* ======================== TABLE VIEW ======================== */
QTableWidget, QTableView {
    background-color: #12122e;
    alternate-background-color: #16163a;
    border: 1px solid #2a2a5e;
    border-radius: 6px;
    gridline-color: #2a2a5e;
}

QHeaderView::section {
    background-color: #1a1a3e;
    color: #888888;
    border: 1px solid #2a2a5e;
    padding: 8px;
    font-weight: 600;
}

QTableWidget::item:selected {
    background-color: #4A90D9;
    color: #ffffff;
}

/* ======================== LIST WIDGET ======================== */
QListWidget {
    background-color: #12122e;
    border: 1px solid #2a2a5e;
    border-radius: 6px;
    padding: 4px;
    outline: 0;
}

QListWidget::item {
    padding: 8px 12px;
    border-radius: 4px;
    margin: 2px 0;
}

QListWidget::item:selected {
    background-color: #4A90D9;
    color: #ffffff;
}

QListWidget::item:hover:!selected {
    background-color: #22224e;
}

/* ======================== SPLITTER ======================== */
QSplitter::handle {
    background-color: #2a2a5e;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QSplitter::handle:hover {
    background-color: #4A90D9;
}

/* ======================== PROGRESS BAR ======================== */
QProgressBar {
    background-color: #1a1a3e;
    border: 1px solid #2a2a5e;
    border-radius: 6px;
    text-align: center;
    color: #e0e0e0;
    height: 20px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #4A90D9, stop:1 #7ED321);
    border-radius: 5px;
}

/* ======================== TOOL TIP ======================== */
QToolTip {
    background-color: #1e1e42;
    color: #e0e0e0;
    border: 1px solid #4A90D9;
    border-radius: 4px;
    padding: 6px;
    font-size: 12px;
}

/* ======================== GROUP BOX ======================== */
QGroupBox {
    border: 1px solid #2a2a5e;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #4A90D9;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* ======================== CHECK BOX / RADIO ======================== */
QCheckBox, QRadioButton {
    color: #e0e0e0;
    spacing: 8px;
}

QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #3a3a6e;
    border-radius: 4px;
    background-color: #12122e;
}

QRadioButton::indicator {
    border-radius: 10px;
}

QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background-color: #4A90D9;
    border-color: #4A90D9;
}

QCheckBox::indicator:hover, QRadioButton::indicator:hover {
    border-color: #4A90D9;
}

/* ======================== SPIN BOX ======================== */
QSpinBox, QDoubleSpinBox {
    background-color: #12122e;
    color: #e0e0e0;
    border: 1px solid #2a2a5e;
    border-radius: 6px;
    padding: 4px 8px;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #4A90D9;
}

/* ======================== LABELS ======================== */
QLabel {
    color: #c0c0c0;
    background: transparent;
}

QLabel#titleLabel {
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
}

QLabel#subtitleLabel {
    color: #888888;
    font-size: 11px;
}

QLabel#accentLabel {
    color: #4A90D9;
    font-weight: 600;
}

/* ======================== FRAME ======================== */
QFrame#separator {
    background-color: #2a2a5e;
    max-height: 1px;
}

QFrame#panelFrame {
    background-color: #16163a;
    border: 1px solid #2a2a5e;
    border-radius: 8px;
}

/* ======================== STACKED WIDGET ======================== */
QStackedWidget {
    background-color: #16163a;
}

/* ======================== STATUS BAR ======================== */
QStatusBar {
    background-color: #0f0f23;
    color: #888888;
    border-top: 1px solid #2a2a5e;
}
"""
