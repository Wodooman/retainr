"""Unit tests for configuration management."""

import os
import tempfile
from pathlib import Path

from mcp_server.config import Settings


class TestSettings:
    """Test Settings configuration and validation."""

    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()

        assert settings.mode == "native"
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000
        assert settings.memory_dir == Path("memory")
        assert settings.chroma_host == "localhost"
        assert settings.chroma_port == 8000
        assert settings.chroma_collection == "retainr_memories"
        assert settings.mcp_transport == "stdio"
        assert settings.embedding_model == "all-MiniLM-L6-v2"
        assert not settings.debug

    def test_native_mode_detection(self):
        """Test native mode helper methods."""
        settings = Settings(mode="native")

        assert settings.is_native_mode()
        assert not settings.is_docker_mode()

    def test_docker_mode_detection(self):
        """Test docker mode helper methods."""
        settings = Settings(mode="docker")

        assert not settings.is_native_mode()
        assert settings.is_docker_mode()

    def test_chroma_url_generation(self):
        """Test ChromaDB URL generation."""
        settings = Settings(chroma_host="localhost", chroma_port=8000)
        assert settings.chroma_url == "http://localhost:8000"

        settings = Settings(chroma_host="192.168.1.100", chroma_port=9000)
        assert settings.chroma_url == "http://192.168.1.100:9000"

    def test_environment_variable_override(self):
        """Test that environment variables override defaults."""
        # Save original environment
        original_env = os.environ.copy()

        try:
            # Set test environment variables
            os.environ["RETAINR_MODE"] = "docker"
            os.environ["RETAINR_CHROMA_HOST"] = "test-host"
            os.environ["RETAINR_CHROMA_PORT"] = "9001"
            os.environ["RETAINR_DEBUG"] = "true"

            settings = Settings()

            assert settings.mode == "docker"
            assert settings.chroma_host == "test-host"
            assert settings.chroma_port == 9001
            assert settings.debug is True
            assert settings.chroma_url == "http://test-host:9001"

        finally:
            # Restore original environment
            os.environ.clear()
            os.environ.update(original_env)

    def test_memory_dir_path_conversion(self):
        """Test memory directory path conversion."""
        # Test string path conversion
        settings = Settings(memory_dir="./test-memory")
        assert isinstance(settings.memory_dir, Path)
        assert settings.memory_dir == Path("./test-memory")

        # Test Path object
        test_path = Path("/tmp/test-memory")
        settings = Settings(memory_dir=test_path)
        assert settings.memory_dir == test_path

    def test_model_cache_dir_expansion(self):
        """Test model cache directory path expansion."""
        with tempfile.TemporaryDirectory():
            # Test with home directory expansion - the expanduser happens during init
            settings = Settings(model_cache_dir="~/test-cache")
            # Path expansion should happen in the constructor
            assert "~" not in str(settings.model_cache_dir)
            assert settings.model_cache_dir.is_absolute()

    def test_directory_creation(self):
        """Test that directories are created during initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            memory_dir = temp_path / "test-memory"
            cache_dir = temp_path / "test-cache"

            # Directories shouldn't exist yet
            assert not memory_dir.exists()
            assert not cache_dir.exists()

            # Initialize settings
            Settings(memory_dir=str(memory_dir), model_cache_dir=str(cache_dir))

            # Directories should be created
            assert memory_dir.exists()
            assert cache_dir.exists()
            assert memory_dir.is_dir()
            assert cache_dir.is_dir()

    def test_auto_mode_detection_with_venv(self):
        """Test auto mode detection when virtual environment exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                # Create a fake venv directory
                venv_dir = Path(temp_dir) / "venv"
                venv_dir.mkdir()

                settings = Settings(mode="auto")

                # Should detect native mode due to venv presence
                assert settings.mode == "native"

            finally:
                os.chdir(original_cwd)

    def test_auto_mode_detection_without_venv(self):
        """Test auto mode detection when no virtual environment exists."""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as temp_dir:
            # Change to temp directory without venv
            original_cwd = os.getcwd()
            os.chdir(temp_dir)

            try:
                # Mock shutil.which to return None (no docker)
                with patch("shutil.which", return_value=None):
                    settings = Settings(mode="auto")

                    # Should default to native mode when no docker available
                    assert settings.mode == "native"

            finally:
                os.chdir(original_cwd)

    def test_invalid_mode_handling(self):
        """Test handling of invalid mode values."""
        # Invalid modes should still be accepted (for forward compatibility)
        settings = Settings(mode="invalid-mode")
        assert settings.mode == "invalid-mode"

        # But helper methods should handle them gracefully
        assert not settings.is_native_mode()
        assert not settings.is_docker_mode()
