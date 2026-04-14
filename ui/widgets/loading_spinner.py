"""
Loading spinner widget with rotation animation.
"""
import math

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QPen


class LoadingSpinner(QWidget):
    """Animated loading spinner."""

    def __init__(self, parent=None, size: int = 40, color: str = "#4A90D9"):
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self._angle = 0
        self._num_dots = 12
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(QSize(size, size))
        self.hide()

    def start(self):
        """Start spinning animation."""
        self._angle = 0
        self._timer.start(80)
        self.show()

    def stop(self):
        """Stop spinning animation."""
        self._timer.stop()
        self.hide()

    def _rotate(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self._size / 2, self._size / 2)
        painter.rotate(self._angle)

        dot_radius = self._size * 0.06
        orbit_radius = self._size * 0.35

        for i in range(self._num_dots):
            angle = (360 / self._num_dots) * i
            alpha = int(255 * (1 - i / self._num_dots))
            color = QColor(self._color)
            color.setAlpha(max(40, alpha))

            x = orbit_radius * math.cos(math.radians(angle))
            y = orbit_radius * math.sin(math.radians(angle))

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            r = dot_radius * (1 + (self._num_dots - i) / self._num_dots * 0.5)
            painter.drawEllipse(int(x - r), int(y - r), int(2 * r), int(2 * r))

        painter.end()
