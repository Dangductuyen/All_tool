"""
Subtitle service for loading, parsing, and managing SRT files.
"""
import os
import re
from typing import List, Optional

from utils.logger import log


class SubtitleEntry:
    """Single subtitle entry."""
    def __init__(self, index: int, start: str, end: str, text: str):
        self.index = index
        self.start = start
        self.end = end
        self.text = text

    def to_srt(self) -> str:
        return f"{self.index}\n{self.start} --> {self.end}\n{self.text}\n"

    def __repr__(self):
        return f"SubtitleEntry({self.index}, {self.start}->{self.end}, '{self.text[:30]}')"


class SubtitleService:
    """Service for subtitle file operations."""

    @staticmethod
    def parse_srt(content: str) -> List[SubtitleEntry]:
        """Parse SRT content into subtitle entries."""
        entries = []
        blocks = re.split(r'\n\s*\n', content.strip())
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    index = int(lines[0].strip())
                    time_match = re.match(
                        r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})',
                        lines[1].strip()
                    )
                    if time_match:
                        start = time_match.group(1)
                        end = time_match.group(2)
                        text = '\n'.join(lines[2:])
                        entries.append(SubtitleEntry(index, start, end, text))
                except (ValueError, IndexError) as e:
                    log.warning(f"Skipping malformed subtitle block: {e}")
        return entries

    @staticmethod
    def load_srt(file_path: str) -> List[SubtitleEntry]:
        """Load and parse SRT file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"SRT file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return SubtitleService.parse_srt(content)

    @staticmethod
    def save_srt(entries: List[SubtitleEntry], file_path: str):
        """Save subtitle entries to SRT file."""
        with open(file_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(entry.to_srt() + "\n")
        log.info(f"Subtitle saved: {file_path}")

    @staticmethod
    def entries_to_srt(entries: List[SubtitleEntry]) -> str:
        """Convert entries to SRT string."""
        return "\n".join(entry.to_srt() for entry in entries)

    @staticmethod
    def validate_srt(content: str) -> List[str]:
        """Validate SRT format and return list of errors."""
        errors = []
        blocks = re.split(r'\n\s*\n', content.strip())
        for i, block in enumerate(blocks):
            lines = block.strip().split('\n')
            if len(lines) < 3:
                errors.append(f"Block {i+1}: Not enough lines (need at least 3)")
                continue
            try:
                idx = int(lines[0].strip())
                if idx != i + 1:
                    errors.append(f"Block {i+1}: Index mismatch (got {idx})")
            except ValueError:
                errors.append(f"Block {i+1}: Invalid index '{lines[0].strip()}'")
            time_match = re.match(
                r'(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})',
                lines[1].strip()
            )
            if not time_match:
                errors.append(f"Block {i+1}: Invalid time format '{lines[1].strip()}'")
        return errors
