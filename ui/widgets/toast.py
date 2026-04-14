"""
Toast notification widget with fade animation.
"""
from PySide6.QtWidgets import QLabel, QWidget, QGraphicsOpacityEffect, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont


class Toast(QLabel):
    """Animated toast notification."""

    STYLES = {
        "info": "background-color: #4A90D9; color: #ffffff;",
        "success": "background-color: #4AD97A; color: #1a1a2e;",
        "warning": "background-color: #F5A623; color: #1a1a2e;",
        "error": "background-color: #D94A4A; color: #ffffff;",
    }

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))
        self.setFixedHeight(44)
        self.setMinimumWidth(250)
        self.setMaximumWidth(600)
        self.hide()

        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0.0)

        self._fade_in = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_in.setDuration(300)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(1.0)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._fade_out = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_out.setDuration(500)
        self._fade_out.setStartValue(1.0)
        self._fade_out.setEndValue(0.0)
        self._fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._fade_out.finished.connect(self.hide)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade_out)

    def show_message(self, message: str, level: str = "info", duration: int = 3000):
        """Show toast with message."""
        style = self.STYLES.get(level, self.STYLES["info"])
        self.setStyleSheet(
            f"{style} border-radius: 8px; padding: 8px 24px; font-size: 13px;"
        )
        self.setText(message)
        self.adjustSize()

        # Position at top-center of parent
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            self.move(x, 20)

        self.show()
        self.raise_()
        self._fade_in.start()
        self._timer.start(duration)

    def _start_fade_out(self):
        self._fade_out.start()
