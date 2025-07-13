"""Pytest configuration and shared fixtures."""

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_memory_data():
    """Sample memory data for testing."""
    return {
        "project": "test-project",
        "category": "testing",
        "tags": ["test", "pytest"],
        "references": ["conftest.py"],
        "content": "# Test Memory\n\nThis is a test memory for pytest.",
        "outdated": False,
    }
