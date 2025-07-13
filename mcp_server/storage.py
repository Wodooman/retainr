"""File-based memory storage with markdown files."""

import hashlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import frontmatter
from slugify import slugify

from .config import settings
from .models import MemoryEntry


class MemoryStorage:
    """Handles file-based storage of memory entries as markdown files."""

    def __init__(self, memory_dir: Optional[Path] = None):
        self.memory_dir = memory_dir or settings.memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _generate_filename(self, entry: MemoryEntry) -> str:
        """Generate filename for memory entry."""
        timestamp = entry.timestamp or datetime.utcnow()
        timestamp_str = timestamp.strftime("%Y-%m-%dT%H-%M-%S")

        # Create slug from content title or first line
        content_lines = entry.content.strip().split("\n")
        first_line = content_lines[0] if content_lines else "memory"
        # Remove markdown header markers
        title = (
            first_line.lstrip("#").strip() if first_line.startswith("#") else first_line
        )
        slug = slugify(title[:50])  # Limit length

        return f"{timestamp_str}-{entry.category}-{slug}.md"

    def _generate_memory_id(self, file_path: Path) -> str:
        """Generate unique ID for memory entry based on file path."""
        return hashlib.sha256(str(file_path).encode()).hexdigest()[:12]

    def save_memory(self, entry: MemoryEntry) -> tuple[str, Path]:
        """Save memory entry as markdown file.

        Returns:
            tuple[str, Path]: Memory ID and file path
        """
        # Set timestamp if not provided
        if not entry.timestamp:
            entry.timestamp = datetime.utcnow()

        # Create project directory
        project_dir = self.memory_dir / entry.project
        project_dir.mkdir(exist_ok=True)

        # Generate filename and path
        filename = self._generate_filename(entry)
        file_path = project_dir / filename

        # Create frontmatter post
        post = frontmatter.Post(
            content=entry.content,
            project=entry.project,
            category=entry.category,
            tags=entry.tags,
            references=entry.references,
            timestamp=entry.timestamp.isoformat(),
            outdated=entry.outdated,
        )

        # Write to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(frontmatter.dumps(post))

        memory_id = self._generate_memory_id(file_path)
        return memory_id, file_path

    def load_memory(self, file_path: Path) -> Optional[MemoryEntry]:
        """Load memory entry from markdown file."""
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            # Parse timestamp
            timestamp = None
            if "timestamp" in post.metadata:
                timestamp = datetime.fromisoformat(post.metadata["timestamp"])

            return MemoryEntry(
                project=post.metadata.get("project", ""),
                category=post.metadata.get("category", ""),
                tags=post.metadata.get("tags", []),
                references=post.metadata.get("references", []),
                content=post.content,
                outdated=post.metadata.get("outdated", False),
                timestamp=timestamp,
            )
        except Exception as e:
            print(f"Error loading memory from {file_path}: {e}")
            return None

    def update_memory(self, file_path: Path, outdated: bool) -> bool:
        """Update memory entry (mark as outdated)."""
        entry = self.load_memory(file_path)
        if not entry:
            return False

        entry.outdated = outdated
        self.save_memory(entry)
        return True

    def list_memory_files(self, project: Optional[str] = None) -> List[Path]:
        """List all memory files, optionally filtered by project."""
        files = []

        if project:
            project_dir = self.memory_dir / project
            if project_dir.exists():
                files.extend(project_dir.glob("*.md"))
        else:
            # Search all project directories
            for project_dir in self.memory_dir.iterdir():
                if project_dir.is_dir():
                    files.extend(project_dir.glob("*.md"))

        return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)

    def find_memory_by_id(self, memory_id: str) -> Optional[Path]:
        """Find memory file by ID."""
        for file_path in self.list_memory_files():
            if self._generate_memory_id(file_path) == memory_id:
                return file_path
        return None

    def get_memory_id(self, file_path: Path) -> str:
        """Get memory ID for a file path."""
        return self._generate_memory_id(file_path)
