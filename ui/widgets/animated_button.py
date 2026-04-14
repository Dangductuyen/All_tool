"""
Animated button with hover glow effect.
"""
from PySide6.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QFont


class AnimatedButton(QPushButton):
    """Button with hover glow animation."""

    def __init__(self, text: str = "", parent=None, color: str = "#4A90D9",
                 style_id: str = "primaryButton"):
        super().__init__(text, parent)
        self._glow_color = QColor(color)
        self._glow_radius = 0

        self.setObjectName(style_id)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 12, QFont.Weight.DemiBold))

        # Glow effect
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(0)
        self._shadow.setColor(self._glow_color)
        self._shadow.setOffset(0, 0)
        self.setGraphicsEffect(self._shadow)

        # Animation
        self._anim = QPropertyAnimation(self, b"glowRadius")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _get_glow_radius(self) -> float:
        return self._glow_radius

    def _set_glow_radius(self, value: float):
        self._glow_radius = value
        self._shadow.setBlurRadius(value)

    glowRadius = Property(float, _get_glow_radius, _set_glow_radius)

    def enterEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self._glow_radius)
        self._anim.setEndValue(20)
        self._anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._anim.stop()
        self._anim.setStartValue(self._glow_radius)
        self._anim.setEndValue(0)
        self._anim.start()
        super().leaveEvent(event)
