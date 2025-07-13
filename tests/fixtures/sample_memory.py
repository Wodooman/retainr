"""Test fixtures for memory entries."""

from datetime import datetime
from mcp_server.models import MemoryEntry


def sample_memory_entry() -> MemoryEntry:
    """Create a sample memory entry for testing."""
    return MemoryEntry(
        project="test-project",
        category="testing",
        tags=["test", "sample", "fixture"],
        references=["tests/test_file.py"],
        content="# Test Memory\n\nThis is a sample memory entry for testing purposes.",
        outdated=False,
        timestamp=datetime(2024, 1, 15, 10, 30, 0)
    )


def sample_memory_json() -> dict:
    """Sample memory entry as JSON for API testing."""
    return {
        "project": "test-project",
        "category": "testing",
        "tags": ["test", "api", "json"],
        "references": ["tests/api_test.py"],
        "content": "# API Test Memory\n\nThis memory was created via API for testing.",
        "outdated": False
    }


def sample_memories_list() -> list[MemoryEntry]:
    """Create a list of sample memory entries."""
    return [
        MemoryEntry(
            project="project-a",
            category="architecture",
            tags=["database", "design"],
            references=["src/models.py"],
            content="# Database Architecture\n\nUsing PostgreSQL for data persistence.",
            outdated=False,
            timestamp=datetime(2024, 1, 10, 9, 0, 0)
        ),
        MemoryEntry(
            project="project-a",
            category="implementation",
            tags=["auth", "security"],
            references=["src/auth.py"],
            content="# Authentication System\n\nImplemented JWT-based authentication.",
            outdated=False,
            timestamp=datetime(2024, 1, 12, 14, 15, 0)
        ),
        MemoryEntry(
            project="project-b",
            category="debugging",
            tags=["performance", "optimization"],
            references=["src/utils.py"],
            content="# Performance Issue Fix\n\nOptimized query performance by adding indexes.",
            outdated=True,
            timestamp=datetime(2024, 1, 5, 16, 45, 0)
        )
    ]