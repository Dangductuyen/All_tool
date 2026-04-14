"""
Timeline model for video, audio, and subtitle tracks.
"""
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class TimelineClip:
    """A clip on the timeline."""
    id: str
    track: str  # "video", "audio", "subtitle"
    start_time: float  # seconds
    duration: float  # seconds
    file_path: str = ""
    text: str = ""  # for subtitle clips
    color: str = "#4A90D9"

    @property
    def end_time(self) -> float:
        return self.start_time + self.duration


@dataclass
class TimelineTrack:
    """A single track on the timeline."""
    name: str
    track_type: str  # "video", "audio", "subtitle"
    clips: List[TimelineClip] = field(default_factory=list)
    muted: bool = False
    locked: bool = False
    visible: bool = True


class TimelineModel:
    """Model for the entire timeline."""

    def __init__(self):
        self.tracks: List[TimelineTrack] = [
            TimelineTrack("Video 1", "video"),
            TimelineTrack("Audio 1", "audio"),
            TimelineTrack("Subtitle", "subtitle"),
        ]
        self.duration: float = 0.0  # total timeline duration
        self.cursor_position: float = 0.0
        self.zoom_level: float = 1.0
        self.markers: List[float] = []
        self._clip_counter = 0

    def add_clip(self, track_index: int, start_time: float, duration: float,
                 file_path: str = "", text: str = "") -> Optional[TimelineClip]:
        """Add a clip to a track."""
        if 0 <= track_index < len(self.tracks):
            self._clip_counter += 1
            track = self.tracks[track_index]
            colors = {"video": "#4A90D9", "audio": "#7ED321", "subtitle": "#F5A623"}
            clip = TimelineClip(
                id=f"clip_{self._clip_counter}",
                track=track.track_type,
                start_time=start_time,
                duration=duration,
                file_path=file_path,
                text=text,
                color=colors.get(track.track_type, "#4A90D9"),
            )
            track.clips.append(clip)
            self._update_duration()
            return clip
        return None

    def remove_clip(self, clip_id: str):
        """Remove a clip by ID."""
        for track in self.tracks:
            track.clips = [c for c in track.clips if c.id != clip_id]
        self._update_duration()

    def move_clip(self, clip_id: str, new_start: float):
        """Move a clip to a new start time."""
        for track in self.tracks:
            for clip in track.clips:
                if clip.id == clip_id:
                    clip.start_time = max(0, new_start)
                    self._update_duration()
                    return

    def add_marker(self, time: float):
        """Add a marker at a specific time."""
        if time not in self.markers:
            self.markers.append(time)
            self.markers.sort()

    def remove_marker(self, time: float):
        """Remove a marker."""
        self.markers = [m for m in self.markers if abs(m - time) > 0.01]

    def _update_duration(self):
        """Update total timeline duration."""
        max_end = 0.0
        for track in self.tracks:
            for clip in track.clips:
                max_end = max(max_end, clip.end_time)
        self.duration = max(max_end, 10.0)  # minimum 10 seconds

    def set_zoom(self, level: float):
        """Set zoom level (0.1 to 10.0)."""
        self.zoom_level = max(0.1, min(10.0, level))

    def get_clips_at_time(self, time: float) -> List[TimelineClip]:
        """Get all clips at a specific time position."""
        clips = []
        for track in self.tracks:
            for clip in track.clips:
                if clip.start_time <= time <= clip.end_time:
                    clips.append(clip)
        return clips
