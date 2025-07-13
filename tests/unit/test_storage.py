"""Unit tests for memory storage functionality."""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from mcp_server.storage import MemoryStorage
from tests.fixtures.sample_memory import sample_memory_entry


class TestMemoryStorage:
    """Test file-based memory storage operations."""

    @pytest.fixture
    def temp_storage(self):
        """Create a temporary storage directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        storage = MemoryStorage(temp_dir)
        yield storage
        # Cleanup
        shutil.rmtree(temp_dir)

    def test_save_memory(self, temp_storage):
        """Test saving a memory entry to file."""
        entry = sample_memory_entry()

        memory_id, file_path = temp_storage.save_memory(entry)

        # Check return values
        assert memory_id is not None
        assert isinstance(memory_id, str)
        assert len(memory_id) == 12  # MD5 hash truncated to 12 chars
        assert file_path.exists()

        # Check file location
        expected_dir = temp_storage.memory_dir / entry.project
        assert file_path.parent == expected_dir
        assert file_path.suffix == ".md"

    def test_save_memory_creates_project_directory(self, temp_storage):
        """Test that saving memory creates project directory if it doesn't exist."""
        entry = sample_memory_entry()

        project_dir = temp_storage.memory_dir / entry.project
        assert not project_dir.exists()

        memory_id, file_path = temp_storage.save_memory(entry)

        assert project_dir.exists()
        assert project_dir.is_dir()

    def test_filename_generation(self, temp_storage):
        """Test that filename follows expected pattern."""
        entry = sample_memory_entry()
        entry.timestamp = datetime(2024, 1, 15, 10, 30, 45)

        memory_id, file_path = temp_storage.save_memory(entry)

        filename = file_path.name
        assert filename.startswith("2024-01-15T10-30-45")
        assert entry.category in filename
        assert filename.endswith(".md")

    def test_load_memory(self, temp_storage):
        """Test loading a memory entry from file."""
        original_entry = sample_memory_entry()

        # Save first
        memory_id, file_path = temp_storage.save_memory(original_entry)

        # Load back
        loaded_entry = temp_storage.load_memory(file_path)

        assert loaded_entry is not None
        assert loaded_entry.project == original_entry.project
        assert loaded_entry.category == original_entry.category
        assert loaded_entry.content == original_entry.content
        assert loaded_entry.tags == original_entry.tags
        assert loaded_entry.references == original_entry.references
        assert loaded_entry.outdated == original_entry.outdated

    def test_load_nonexistent_file(self, temp_storage):
        """Test loading from non-existent file returns None."""
        nonexistent_file = temp_storage.memory_dir / "nonexistent.md"
        result = temp_storage.load_memory(nonexistent_file)
        assert result is None

    def test_update_memory(self, temp_storage):
        """Test updating memory entry."""
        entry = sample_memory_entry()
        memory_id, file_path = temp_storage.save_memory(entry)

        # Update memory
        success = temp_storage.update_memory(file_path, outdated=True)
        assert success is True

        # Verify update
        updated_entry = temp_storage.load_memory(file_path)
        assert updated_entry.outdated is True

    def test_update_nonexistent_memory(self, temp_storage):
        """Test updating non-existent memory returns False."""
        nonexistent_file = temp_storage.memory_dir / "nonexistent.md"
        success = temp_storage.update_memory(nonexistent_file, outdated=True)
        assert success is False

    def test_list_memory_files(self, temp_storage):
        """Test listing memory files."""
        # Create multiple memories
        entries = [sample_memory_entry(), sample_memory_entry(), sample_memory_entry()]

        # Modify entries to be different
        entries[1].project = "different-project"
        entries[2].category = "different-category"

        saved_files = []
        for entry in entries:
            _, file_path = temp_storage.save_memory(entry)
            saved_files.append(file_path)

        # List all files
        all_files = temp_storage.list_memory_files()
        assert len(all_files) == 3

        # Check that all saved files are in the list
        for saved_file in saved_files:
            assert saved_file in all_files

    def test_list_memory_files_by_project(self, temp_storage):
        """Test listing memory files filtered by project."""
        from datetime import datetime

        # Create memories for different projects with unique timestamps and content
        entry1 = sample_memory_entry()
        entry1.project = "project-a"
        entry1.content = "# First Memory\n\nThis is the first memory."
        entry1.timestamp = datetime(2024, 1, 15, 10, 30, 0)

        entry2 = sample_memory_entry()
        entry2.project = "project-b"
        entry2.content = "# Second Memory\n\nThis is the second memory."
        entry2.timestamp = datetime(2024, 1, 15, 11, 30, 0)

        entry3 = sample_memory_entry()
        entry3.project = "project-a"
        entry3.content = "# Third Memory\n\nThis is the third memory."
        entry3.timestamp = datetime(2024, 1, 15, 12, 30, 0)

        temp_storage.save_memory(entry1)
        temp_storage.save_memory(entry2)
        temp_storage.save_memory(entry3)

        # List files for project-a
        project_a_files = temp_storage.list_memory_files("project-a")
        assert len(project_a_files) == 2

        # List files for project-b
        project_b_files = temp_storage.list_memory_files("project-b")
        assert len(project_b_files) == 1

        # List files for non-existent project
        empty_files = temp_storage.list_memory_files("nonexistent")
        assert len(empty_files) == 0

    def test_find_memory_by_id(self, temp_storage):
        """Test finding memory file by ID."""
        entry = sample_memory_entry()
        memory_id, file_path = temp_storage.save_memory(entry)

        found_path = temp_storage.find_memory_by_id(memory_id)
        assert found_path == file_path

    def test_find_nonexistent_memory_id(self, temp_storage):
        """Test finding non-existent memory ID returns None."""
        found_path = temp_storage.find_memory_by_id("nonexistent-id")
        assert found_path is None

    def test_get_memory_id(self, temp_storage):
        """Test getting memory ID from file path."""
        entry = sample_memory_entry()
        memory_id, file_path = temp_storage.save_memory(entry)

        retrieved_id = temp_storage.get_memory_id(file_path)
        assert retrieved_id == memory_id

    def test_memory_id_consistency(self, temp_storage):
        """Test that memory ID is consistent for the same file path."""
        entry = sample_memory_entry()
        memory_id, file_path = temp_storage.save_memory(entry)

        # Get ID multiple times
        id1 = temp_storage.get_memory_id(file_path)
        id2 = temp_storage.get_memory_id(file_path)
        id3 = temp_storage.find_memory_by_id(memory_id)

        assert id1 == id2 == memory_id
        assert id3 == file_path
