"""Unit tests for Pydantic models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from mcp_server.models import MemoryEntry, MemorySearchParams, MemoryUpdateRequest


class TestMemoryEntry:
    """Test MemoryEntry model validation and behavior."""

    def test_valid_memory_entry(self):
        """Test creating a valid memory entry."""
        entry = MemoryEntry(
            project="test-project",
            category="testing",
            content="Test content",
            tags=["test"],
            references=["file.py"],
        )

        assert entry.project == "test-project"
        assert entry.category == "testing"
        assert entry.content == "Test content"
        assert entry.tags == ["test"]
        assert entry.references == ["file.py"]
        assert entry.outdated is False
        assert entry.timestamp is None

    def test_minimal_memory_entry(self):
        """Test creating memory entry with minimal required fields."""
        entry = MemoryEntry(
            project="minimal", category="test", content="Minimal content"
        )

        assert entry.project == "minimal"
        assert entry.category == "test"
        assert entry.content == "Minimal content"
        assert entry.tags == []
        assert entry.references == []
        assert entry.outdated is False

    def test_memory_entry_with_timestamp(self):
        """Test memory entry with explicit timestamp."""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        entry = MemoryEntry(
            project="test", category="test", content="Test", timestamp=timestamp
        )

        assert entry.timestamp == timestamp

    def test_missing_required_fields(self):
        """Test validation errors for missing required fields."""
        # Missing project
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(category="test", content="test")
        assert "project" in str(exc_info.value)

        # Missing category
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(project="test", content="test")
        assert "category" in str(exc_info.value)

        # Missing content
        with pytest.raises(ValidationError) as exc_info:
            MemoryEntry(project="test", category="test")
        assert "content" in str(exc_info.value)

    def test_empty_string_validation(self):
        """Test validation of empty strings."""
        with pytest.raises(ValidationError):
            MemoryEntry(project="", category="test", content="test")

        with pytest.raises(ValidationError):
            MemoryEntry(project="test", category="", content="test")

        with pytest.raises(ValidationError):
            MemoryEntry(project="test", category="test", content="")


class TestMemorySearchParams:
    """Test MemorySearchParams model validation."""

    def test_valid_search_params(self):
        """Test creating valid search parameters."""
        params = MemorySearchParams(
            query="test query", project="test-project", tags=["tag1", "tag2"], top=5
        )

        assert params.query == "test query"
        assert params.project == "test-project"
        assert params.tags == ["tag1", "tag2"]
        assert params.top == 5

    def test_minimal_search_params(self):
        """Test search params with only required fields."""
        params = MemorySearchParams(query="test")

        assert params.query == "test"
        assert params.project is None
        assert params.tags is None
        assert params.top == 3  # default value

    def test_top_validation(self):
        """Test validation of top parameter."""
        # Valid range
        params = MemorySearchParams(query="test", top=1)
        assert params.top == 1

        params = MemorySearchParams(query="test", top=10)
        assert params.top == 10

        # Invalid range
        with pytest.raises(ValidationError):
            MemorySearchParams(query="test", top=0)

        with pytest.raises(ValidationError):
            MemorySearchParams(query="test", top=11)

    def test_empty_query_validation(self):
        """Test validation of empty query."""
        with pytest.raises(ValidationError):
            MemorySearchParams(query="")


class TestMemoryUpdateRequest:
    """Test MemoryUpdateRequest model validation."""

    def test_valid_update_request(self):
        """Test creating valid update request."""
        request = MemoryUpdateRequest(outdated=True)
        assert request.outdated is True

        request = MemoryUpdateRequest(outdated=False)
        assert request.outdated is False

    def test_missing_outdated_field(self):
        """Test validation error for missing outdated field."""
        with pytest.raises(ValidationError) as exc_info:
            MemoryUpdateRequest()
        assert "outdated" in str(exc_info.value)
