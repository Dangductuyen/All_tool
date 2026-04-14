"""
Timeline widget with video, audio, and subtitle tracks.
Supports drag & drop, time ruler, and markers.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSlider, QSplitter
)
from PySide6.QtCore import Qt, QRect, Signal, QPoint, QSize
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QLinearGradient

from core.timeline_model import TimelineModel, TimelineClip


class TimeRuler(QWidget):
    """Time ruler widget showing time markers."""

    position_changed = Signal(float)

    def __init__(self, timeline_model: TimelineModel, parent=None):
        super().__init__(parent)
        self.model = timeline_model
        self.setFixedHeight(30)
        self.setMinimumWidth(800)
        self._pixels_per_second = 50
        self._dragging = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#0f0f23"))

        # Ticks and labels
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.setFont(QFont("Segoe UI", 8))

        pps = self._pixels_per_second * self.model.zoom_level
        total_seconds = max(self.model.duration, w / pps)

        # Draw second markers
        for sec in range(int(total_seconds) + 1):
            x = int(sec * pps)
            if x > w:
                break

            if sec % 5 == 0:
                painter.setPen(QPen(QColor("#888888"), 1))
                painter.drawLine(x, h - 20, x, h)
                minutes = sec // 60
                secs = sec % 60
                painter.drawText(x + 3, h - 22, f"{minutes}:{secs:02d}")
            else:
                painter.setPen(QPen(QColor("#444444"), 1))
                painter.drawLine(x, h - 10, x, h)

        # Draw markers
        painter.setPen(QPen(QColor("#F5A623"), 2))
        for marker_time in self.model.markers:
            x = int(marker_time * pps)
            painter.drawLine(x, 0, x, h)
            painter.setBrush(QColor("#F5A623"))
            painter.drawPolygon([
                QPoint(x - 4, 0), QPoint(x + 4, 0), QPoint(x, 6)
            ])

        # Cursor line
        cursor_x = int(self.model.cursor_position * pps)
        painter.setPen(QPen(QColor("#FF4444"), 2))
        painter.drawLine(cursor_x, 0, cursor_x, h)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._update_position(event.position().x())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_position(event.position().x())

    def mouseReleaseEvent(self, event):
        self._dragging = False

    def _update_position(self, x: float):
        pps = self._pixels_per_second * self.model.zoom_level
        time = max(0, x / pps)
        self.model.cursor_position = time
        self.position_changed.emit(time)
        self.update()


class TrackWidget(QWidget):
    """Single track widget showing clips."""

    def __init__(self, track_index: int, track_name: str, track_color: str,
                 timeline_model: TimelineModel, parent=None):
        super().__init__(parent)
        self.track_index = track_index
        self.track_name = track_name
        self.track_color = QColor(track_color)
        self.model = timeline_model
        self.setFixedHeight(50)
        self.setMinimumWidth(800)
        self.setAcceptDrops(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        bg = QColor("#12122e")
        painter.fillRect(0, 0, w, h, bg)

        # Border
        painter.setPen(QPen(QColor("#2a2a5e"), 1))
        painter.drawLine(0, h - 1, w, h - 1)

        pps = 50 * self.model.zoom_level

        # Draw clips
        track = self.model.tracks[self.track_index]
        for clip in track.clips:
            x = int(clip.start_time * pps)
            clip_w = int(clip.duration * pps)
            clip_h = h - 8

            # Clip background with gradient
            gradient = QLinearGradient(x, 4, x, clip_h + 4)
            color = QColor(clip.color)
            gradient.setColorAt(0, color.lighter(120))
            gradient.setColorAt(1, color)
            painter.setBrush(QBrush(gradient))
            painter.setPen(QPen(color.darker(130), 1))
            painter.drawRoundedRect(x, 4, clip_w, clip_h, 4, 4)

            # Clip text
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 9))
            text = clip.text or clip.file_path.split("/")[-1] if clip.file_path else f"Clip {clip.id}"
            painter.drawText(
                QRect(x + 6, 4, clip_w - 12, clip_h),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                text[:30]
            )

        # Cursor line
        cursor_x = int(self.model.cursor_position * pps)
        painter.setPen(QPen(QColor("#FF4444"), 2))
        painter.drawLine(cursor_x, 0, cursor_x, h)

        painter.end()

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        pps = 50 * self.model.zoom_level
        x = event.position().x()
        time = max(0, x / pps)
        self.model.add_clip(self.track_index, time, 5.0, text="Dropped clip")
        self.update()


class TrackHeader(QWidget):
    """Track header with name and controls."""

    def __init__(self, name: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedWidth(120)
        self.setFixedHeight(50)
        self._name = name
        self._color = QColor(color)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#1a1a3e"))

        # Color indicator
        painter.fillRect(0, 0, 4, h, self._color)

        # Border
        painter.setPen(QPen(QColor("#2a2a5e"), 1))
        painter.drawLine(0, h - 1, w, h - 1)
        painter.drawLine(w - 1, 0, w - 1, h)

        # Name
        painter.setPen(QColor("#c0c0c0"))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        painter.drawText(QRect(12, 0, w - 16, h),
                         Qt.AlignmentFlag.AlignVCenter, self._name)

        painter.end()


class TimelineWidget(QWidget):
    """Full timeline widget with tracks, ruler, and controls."""

    position_changed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = TimelineModel()
        self._setup_ui()

        # Add some demo clips
        self.model.add_clip(0, 0, 8.0, text="Video Clip 1")
        self.model.add_clip(0, 10, 5.0, text="Video Clip 2")
        self.model.add_clip(1, 0, 15.0, text="Audio Track")
        self.model.add_clip(2, 1, 3.0, text="Hello World")
        self.model.add_clip(2, 5, 4.0, text="Subtitle 2")
        self.model.add_marker(5.0)
        self.model.add_marker(12.0)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Controls bar
        controls = QWidget()
        controls.setFixedHeight(36)
        controls.setStyleSheet("background-color: #16163a; border-bottom: 1px solid #2a2a5e;")
        ctrl_layout = QHBoxLayout(controls)
        ctrl_layout.setContentsMargins(8, 4, 8, 4)

        # Play controls
        self.btn_play = QPushButton("▶")
        self.btn_play.setFixedSize(30, 28)
        self.btn_play.setToolTip("Play/Pause")
        self.btn_play.clicked.connect(self._toggle_play)
        ctrl_layout.addWidget(self.btn_play)

        self.btn_stop = QPushButton("⏹")
        self.btn_stop.setFixedSize(30, 28)
        self.btn_stop.setToolTip("Stop")
        ctrl_layout.addWidget(self.btn_stop)

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.setFixedSize(30, 28)
        self.btn_prev.setToolTip("Previous")
        ctrl_layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton("⏭")
        self.btn_next.setFixedSize(30, 28)
        self.btn_next.setToolTip("Next")
        ctrl_layout.addWidget(self.btn_next)

        ctrl_layout.addSpacing(16)

        # Time display
        self.lbl_time = QLabel("00:00:00 / 00:00:15")
        self.lbl_time.setStyleSheet("color: #4A90D9; font-family: monospace; font-size: 13px; background: transparent;")
        ctrl_layout.addWidget(self.lbl_time)

        ctrl_layout.addStretch()

        # Zoom
        ctrl_layout.addWidget(QLabel("Zoom:"))
        self.slider_zoom = QSlider(Qt.Orientation.Horizontal)
        self.slider_zoom.setFixedWidth(120)
        self.slider_zoom.setMinimum(10)
        self.slider_zoom.setMaximum(500)
        self.slider_zoom.setValue(100)
        self.slider_zoom.valueChanged.connect(self._on_zoom)
        ctrl_layout.addWidget(self.slider_zoom)

        self.lbl_zoom = QLabel("100%")
        self.lbl_zoom.setFixedWidth(45)
        self.lbl_zoom.setStyleSheet("background: transparent;")
        ctrl_layout.addWidget(self.lbl_zoom)

        # Marker button
        self.btn_marker = QPushButton("🔖 Marker")
        self.btn_marker.setFixedHeight(28)
        self.btn_marker.clicked.connect(self._add_marker)
        ctrl_layout.addWidget(self.btn_marker)

        main_layout.addWidget(controls)

        # Timeline content area
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Track headers
        headers_widget = QWidget()
        headers_layout = QVBoxLayout(headers_widget)
        headers_layout.setContentsMargins(0, 30, 0, 0)
        headers_layout.setSpacing(0)

        track_info = [
            ("Video 1", "#4A90D9"),
            ("Audio 1", "#7ED321"),
            ("Subtitle", "#F5A623"),
        ]

        for name, color in track_info:
            header = TrackHeader(name, color)
            headers_layout.addWidget(header)
        headers_layout.addStretch()

        content_layout.addWidget(headers_widget)

        # Scrollable track area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        tracks_container = QWidget()
        tracks_layout = QVBoxLayout(tracks_container)
        tracks_layout.setContentsMargins(0, 0, 0, 0)
        tracks_layout.setSpacing(0)

        # Time ruler
        self.ruler = TimeRuler(self.model)
        self.ruler.position_changed.connect(self._on_position_changed)
        tracks_layout.addWidget(self.ruler)

        # Tracks
        colors = ["#4A90D9", "#7ED321", "#F5A623"]
        self._tracks = []
        for i, (name, color) in enumerate(track_info):
            track = TrackWidget(i, name, color, self.model)
            self._tracks.append(track)
            tracks_layout.addWidget(track)

        tracks_layout.addStretch()

        scroll.setWidget(tracks_container)
        content_layout.addWidget(scroll)

        main_layout.addWidget(content)

        self._playing = False

    def _toggle_play(self):
        self._playing = not self._playing
        self.btn_play.setText("⏸" if self._playing else "▶")

    def _on_zoom(self, value: int):
        self.model.set_zoom(value / 100.0)
        self.lbl_zoom.setText(f"{value}%")
        self.ruler.update()
        for track in self._tracks:
            track.update()

    def _on_position_changed(self, time: float):
        minutes = int(time // 60)
        secs = int(time % 60)
        ms = int((time % 1) * 100)
        total = self.model.duration
        t_min = int(total // 60)
        t_sec = int(total % 60)
        self.lbl_time.setText(f"{minutes:02d}:{secs:02d}:{ms:02d} / {t_min:02d}:{t_sec:02d}:00")
        self.position_changed.emit(time)
        for track in self._tracks:
            track.update()

    def _add_marker(self):
        self.model.add_marker(self.model.cursor_position)
        self.ruler.update()
