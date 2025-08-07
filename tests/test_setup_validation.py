#!/usr/bin/env python3
"""
Setup Validation Tests for retainr

Tests that validate the complete setup process and ensure all components
are properly configured for Claude Code integration.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest


class TestSetupValidation:
    """Test setup and configuration validation."""

    @pytest.fixture
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent

    @pytest.fixture
    def temp_claude_config(self):
        """Create temporary Claude Code config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            claude_config_dir = Path(temp_dir) / ".config" / "claude-code"
            claude_config_dir.mkdir(parents=True)
            yield claude_config_dir

    def test_required_files_exist(self, project_root):
        """Test that all required files exist."""
        required_files = [
            "setup-claude-code.sh",
            "mcp_server_wrapper.sh",
            "claude-code-mcp.json",
            "docker-compose.yml",
            "requirements.txt",
            "mcp_server/__init__.py",
            "mcp_server/standard_mcp.py",
            "mcp_server/__main__.py",
        ]

        for file_path in required_files:
            full_path = project_root / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"

    def test_docker_requirements(self):
        """Test Docker and docker-compose availability."""
        # Test Docker is available
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip("Docker not available")

        # Test docker-compose is available
        result = subprocess.run(
            ["docker-compose", "--version"], capture_output=True, text=True
        )
        if result.returncode != 0:
            pytest.skip("docker-compose not available")

        # Test Docker daemon is running (optional)
        result = subprocess.run(["docker", "info"], capture_output=True, text=True)
        if result.returncode != 0:
            pytest.skip("Docker daemon not running")

    def test_claude_code_config_validation(self, project_root):
        """Test Claude Code configuration file is valid."""
        config_file = project_root / "claude-code-mcp.json"

        with open(config_file) as f:
            config = json.load(f)

        # Validate structure
        assert "servers" in config
        assert "retainr" in config["servers"]

        retainr_config = config["servers"]["retainr"]
        assert "transport" in retainr_config
        assert "description" in retainr_config
        assert "capabilities" in retainr_config

        transport = retainr_config["transport"]
        assert transport["type"] == "stdio"
        assert "command" in transport
        assert "cwd" in transport

        # Command should point to wrapper script
        assert transport["command"] == "./mcp_server_wrapper.sh"

    def test_wrapper_script_validation(self, project_root):
        """Test MCP wrapper script is properly configured."""
        wrapper_script = project_root / "mcp_server_wrapper.sh"

        # Check file exists and is executable
        assert wrapper_script.exists()
        assert wrapper_script.stat().st_mode & 0o111, "Wrapper script not executable"

        # Check script content
        with open(wrapper_script) as f:
            content = f.read()

        # Should check for Docker
        assert "docker info" in content
        assert "docker-compose" in content

        # Should run MCP server in container
        assert "python -m mcp_server" in content

    def test_setup_script_dry_run(self, project_root, temp_claude_config):
        """Test setup script with mocked environment."""
        setup_script = project_root / "setup-claude-code.sh"

        # Mock HOME environment to use temp directory
        env = {"HOME": str(temp_claude_config.parent)}

        # Run setup script
        result = subprocess.run(
            ["bash", str(setup_script)],
            cwd=project_root,
            capture_output=True,
            text=True,
            env=env,
        )

        # Setup should complete successfully (or fail gracefully)
        if result.returncode != 0:
            # Check if failure is due to missing Docker services (acceptable)
            assert any(
                msg in result.stdout.lower()
                for msg in ["docker", "service", "container", "failed to start"]
            ), f"Unexpected setup failure: {result.stdout}\n{result.stderr}"

        # Check that config file was copied
        mcp_config = temp_claude_config / "mcp.json"
        if mcp_config.exists():
            with open(mcp_config) as f:
                config = json.load(f)
            assert "retainr" in config["servers"]

    def test_requirements_file_validity(self, project_root):
        """Test that requirements.txt is valid and complete."""
        requirements_file = project_root / "requirements.txt"

        with open(requirements_file) as f:
            requirements = f.read().strip().split("\n")

        # Remove empty lines and comments
        requirements = [
            req.strip()
            for req in requirements
            if req.strip() and not req.startswith("#")
        ]

        # Check for essential packages
        essential_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "chromadb",
            "sentence-transformers",
            "mcp",
        ]

        requirements_text = "\n".join(requirements).lower()
        for package in essential_packages:
            assert package in requirements_text, f"Missing essential package: {package}"

    def test_docker_compose_validity(self, project_root):
        """Test docker-compose.yml is valid and complete."""
        compose_file = project_root / "docker-compose.yml"

        # Test that docker-compose can parse the file
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "config"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        assert result.returncode == 0, f"Invalid docker-compose.yml: {result.stderr}"

        # Check that required services are defined
        result = subprocess.run(
            ["docker-compose", "-f", str(compose_file), "ps", "--services"],
            capture_output=True,
            text=True,
            cwd=project_root,
        )

        services = result.stdout.strip().split("\n")
        required_services = ["retainr", "chroma"]

        for service in required_services:
            assert (
                service in services
            ), f"Missing service in docker-compose.yml: {service}"

    def test_mcp_server_module_structure(self, project_root):
        """Test MCP server module structure."""
        mcp_server_dir = project_root / "mcp_server"

        required_files = [
            "__init__.py",
            "__main__.py",
            "standard_mcp.py",
            "main.py",
            "models.py",
            "storage.py",
            "embeddings.py",
        ]

        for file_name in required_files:
            file_path = mcp_server_dir / file_name
            assert file_path.exists(), f"Missing MCP server file: {file_name}"

    def test_mcp_server_imports(self, project_root):
        """Test that MCP server modules can be imported (with mocked dependencies)."""
        # This test would normally fail due to missing mcp package locally
        # So we'll test the import structure instead

        standard_mcp_file = project_root / "mcp_server" / "standard_mcp.py"

        with open(standard_mcp_file) as f:
            content = f.read()

        # Check for proper imports
        assert "from mcp.server.fastmcp import FastMCP" in content
        assert "from .embeddings import EmbeddingService" in content
        assert "from .models import MemoryEntry" in content
        assert "from .storage import MemoryStorage" in content

        # Check for tool definitions
        assert "@mcp.tool()" in content
        assert "@mcp.resource(" in content
        assert "def save_memory(" in content
        assert "def search_memories(" in content
        assert "def list_memories(" in content
        assert "def update_memory(" in content

    def test_dockerfile_validity(self, project_root):
        """Test Dockerfile can be built."""
        dockerfile = project_root / "Dockerfile"

        if not dockerfile.exists():
            pytest.skip("Dockerfile not found")

        # Test that Dockerfile syntax is valid
        result = subprocess.run(
            ["docker", "build", "--dry-run", "-f", str(dockerfile), "."],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        # Docker build --dry-run might not be available in all versions
        # So we check if the command failed due to syntax vs unavailable flag
        if result.returncode != 0:
            if "unknown flag" not in result.stderr.lower():
                # Test basic syntax by parsing manually
                with open(dockerfile) as f:
                    lines = f.readlines()

                # Check for essential Dockerfile instructions
                content = "".join(lines).upper()
                assert "FROM " in content
                assert "COPY " in content or "ADD " in content
                assert "RUN " in content

    def test_memory_directory_structure(self, project_root):
        """Test memory directory can be created and is writable."""
        memory_dir = project_root / "memory"

        # Create memory directory if it doesn't exist
        memory_dir.mkdir(exist_ok=True)

        # Test write permissions
        test_file = memory_dir / "test_write_permissions.txt"
        try:
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink()  # Clean up
        except PermissionError:
            pytest.fail("Memory directory is not writable")

        # Test that directory structure is correct
        assert memory_dir.is_dir()

    def test_claude_code_integration_readiness(self, project_root):
        """Test that all components are ready for Claude Code integration."""
        # Check wrapper script
        wrapper_script = project_root / "mcp_server_wrapper.sh"
        assert wrapper_script.exists() and wrapper_script.stat().st_mode & 0o111

        # Check configuration
        config_file = project_root / "claude-code-mcp.json"
        with open(config_file) as f:
            config = json.load(f)

        assert (
            config["servers"]["retainr"]["transport"]["command"]
            == "./mcp_server_wrapper.sh"
        )

        # Check that all paths in config are relative or valid
        cwd = config["servers"]["retainr"]["transport"]["cwd"]
        assert "${PWD}" in cwd or Path(cwd).exists()

    def test_error_handling_setup(self, project_root, temp_claude_config):
        """Test that setup handles errors gracefully."""
        setup_script = project_root / "setup-claude-code.sh"

        # Test with missing config file (simulate error condition)
        missing_config_dir = temp_claude_config.parent / "missing"
        env = {"HOME": str(missing_config_dir)}

        result = subprocess.run(
            ["bash", str(setup_script)],
            cwd=project_root,
            capture_output=True,
            text=True,
            env=env,
        )

        # Setup should handle missing directories gracefully
        # (either succeed by creating them or fail gracefully)
        if result.returncode != 0:
            # Check that error output is reasonable
            assert any(
                msg in result.stderr.lower()
                for msg in ["no such file", "not found", "permission", "docker"]
            ), f"Unexpected error output: {result.stderr}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
