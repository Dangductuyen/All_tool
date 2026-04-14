"""
Project manager for handling video editor projects.
"""
import json
import os
import shutil
from datetime import datetime
from typing import List, Optional

from utils.config import ConfigManager
from utils.logger import log


class Project:
    """Represents a video editor project."""
    def __init__(self, name: str, path: str, resolution: str = "1920x1080",
                 created: str = None, modified: str = None):
        self.name = name
        self.path = path
        self.resolution = resolution
        self.created = created or datetime.now().isoformat()
        self.modified = modified or datetime.now().isoformat()
        self.media_files: List[str] = []
        self.subtitle_file: Optional[str] = None
        self.audio_files: List[str] = []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "path": self.path,
            "resolution": self.resolution,
            "created": self.created,
            "modified": self.modified,
            "media_files": self.media_files,
            "subtitle_file": self.subtitle_file,
            "audio_files": self.audio_files,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Project":
        proj = cls(
            name=data["name"],
            path=data["path"],
            resolution=data.get("resolution", "1920x1080"),
            created=data.get("created"),
            modified=data.get("modified"),
        )
        proj.media_files = data.get("media_files", [])
        proj.subtitle_file = data.get("subtitle_file")
        proj.audio_files = data.get("audio_files", [])
        return proj


class ProjectManager:
    """Manages all projects."""

    def __init__(self):
        self.config = ConfigManager()
        self.projects_dir = self.config.get("paths", "projects_dir")
        os.makedirs(self.projects_dir, exist_ok=True)
        self.projects: List[Project] = []
        self._load_projects()

    def _load_projects(self):
        """Load all projects from disk."""
        self.projects.clear()
        if not os.path.exists(self.projects_dir):
            return
        for name in os.listdir(self.projects_dir):
            proj_dir = os.path.join(self.projects_dir, name)
            meta_file = os.path.join(proj_dir, "project.json")
            if os.path.isdir(proj_dir) and os.path.exists(meta_file):
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.projects.append(Project.from_dict(data))
                except Exception as e:
                    log.warning(f"Error loading project {name}: {e}")

    def create_project(self, name: str, resolution: str = "1920x1080") -> Project:
        """Create a new project."""
        safe_name = "".join(c for c in name if c.isalnum() or c in " _-").strip()
        if not safe_name:
            safe_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        proj_path = os.path.join(self.projects_dir, safe_name)
        os.makedirs(proj_path, exist_ok=True)
        os.makedirs(os.path.join(proj_path, "media"), exist_ok=True)
        os.makedirs(os.path.join(proj_path, "audio"), exist_ok=True)
        os.makedirs(os.path.join(proj_path, "subtitles"), exist_ok=True)
        os.makedirs(os.path.join(proj_path, "output"), exist_ok=True)

        project = Project(name=safe_name, path=proj_path, resolution=resolution)
        self._save_project_meta(project)
        self.projects.append(project)
        log.info(f"Project created: {safe_name}")
        return project

    def delete_project(self, project: Project):
        """Delete a project."""
        if os.path.exists(project.path):
            shutil.rmtree(project.path)
        self.projects.remove(project)
        log.info(f"Project deleted: {project.name}")

    def _save_project_meta(self, project: Project):
        """Save project metadata."""
        meta_file = os.path.join(project.path, "project.json")
        project.modified = datetime.now().isoformat()
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(project.to_dict(), f, indent=2, ensure_ascii=False)

    def get_projects(self, sort_by: str = "date") -> List[Project]:
        """Get sorted list of projects."""
        if sort_by == "name":
            return sorted(self.projects, key=lambda p: p.name.lower())
        elif sort_by == "resolution":
            return sorted(self.projects, key=lambda p: p.resolution)
        else:  # date
            return sorted(self.projects, key=lambda p: p.modified, reverse=True)

    def search_projects(self, query: str) -> List[Project]:
        """Search projects by name."""
        query = query.lower()
        return [p for p in self.projects if query in p.name.lower()]
