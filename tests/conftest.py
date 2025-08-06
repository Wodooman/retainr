"""Pytest configuration and shared fixtures."""

import asyncio
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
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


# Native testing fixtures
@pytest.fixture(scope="session")
def project_root():
    """Get the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def test_mode():
    """Determine test mode: native or docker."""
    mode = os.getenv("RETAINR_TEST_MODE", "auto")

    if mode == "auto":
        # Auto-detect based on available setup
        project_root = Path(__file__).parent.parent
        if (project_root / "venv").exists():
            return "native"
        else:
            return "docker"

    return mode


@pytest.fixture(scope="session")
def chromadb_service(test_mode, project_root):
    """Ensure ChromaDB service is running."""
    if test_mode == "native":
        # For native mode, check if ChromaDB is accessible
        try:
            response = httpx.get("http://localhost:8000/api/v2/heartbeat", timeout=5)
            if response.status_code == 200:
                yield "running"
                return
        except Exception:
            pass

        # Start ChromaDB if not running
        subprocess.run(
            ["docker-compose", "-f", "docker-compose.chromadb.yml", "up", "-d"],
            cwd=project_root,
            check=True,
        )

        # Wait for ChromaDB to be ready
        max_attempts = 30
        for _ in range(max_attempts):
            try:
                response = httpx.get(
                    "http://localhost:8000/api/v2/heartbeat", timeout=5
                )
                if response.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(2)
        else:
            pytest.fail("ChromaDB failed to start")

        yield "started"

    elif test_mode == "docker":
        # For Docker mode, use existing logic
        result = subprocess.run(
            ["docker-compose", "ps"], cwd=project_root, capture_output=True, text=True
        )

        if result.returncode != 0 or "Up" not in result.stdout:
            pytest.skip("Docker services not running. Run 'make up' first.")

        yield "running"


@pytest.fixture(scope="session")
def mcp_server_executable(test_mode, project_root):
    """Get the MCP server executable command for the current test mode."""
    if test_mode == "native":
        venv_python = project_root / "venv" / "bin" / "python"
        if not venv_python.exists():
            pytest.skip("Native virtual environment not found. Run 'make setup' first.")

        # Test that MCP server can be imported
        result = subprocess.run(
            [str(venv_python), "-c", "from mcp_server.standard_mcp import mcp"],
            cwd=project_root,
            capture_output=True,
        )

        if result.returncode != 0:
            pytest.skip("MCP server not available in native environment")

        return [str(venv_python), "-m", "mcp_server"]

    elif test_mode == "docker":
        wrapper_script = project_root / "mcp_server_wrapper.sh"
        if not wrapper_script.exists():
            pytest.skip("Docker wrapper script not found")

        return [str(wrapper_script)]

    else:
        pytest.fail(f"Unknown test mode: {test_mode}")


@pytest.fixture
def mcp_test_client(mcp_server_executable, project_root):
    """Create an MCP test client that can communicate with the server."""

    class MCPTestClient:
        def __init__(self, executable, cwd):
            self.executable = executable
            self.cwd = cwd

        def send_request(self, request, timeout=30):
            """Send a JSON-RPC request to the MCP server."""
            import json

            if isinstance(request, dict):
                request_data = json.dumps(request) + "\n"
            else:
                request_data = request + "\n"

            result = subprocess.run(
                self.executable,
                input=request_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.cwd,
            )

            if result.returncode != 0:
                raise Exception(f"MCP server failed: {result.stderr}")

            # Parse response lines
            lines = result.stdout.strip().split("\n")
            responses = []
            for line in lines:
                if line.strip():
                    try:
                        responses.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip non-JSON lines (like debug output)
                        continue

            return responses

        def send_requests(self, requests, timeout=30):
            """Send multiple JSON-RPC requests to the MCP server."""
            import json

            request_data = ""
            for request in requests:
                if isinstance(request, dict):
                    request_data += json.dumps(request) + "\n"
                else:
                    request_data += request + "\n"

            result = subprocess.run(
                self.executable,
                input=request_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.cwd,
            )

            if result.returncode != 0:
                raise Exception(f"MCP server failed: {result.stderr}")

            # Parse response lines
            lines = result.stdout.strip().split("\n")
            responses = []
            for line in lines:
                if line.strip():
                    try:
                        responses.append(json.loads(line))
                    except json.JSONDecodeError:
                        # Skip non-JSON lines
                        continue

            return responses

        def initialize_session(self):
            """Initialize an MCP session with standard handshake."""
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "test-client", "version": "1.0"},
                    "capabilities": {},
                },
            }

            init_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }

            responses = self.send_requests([init_request, init_notification])

            if not responses or "result" not in responses[0]:
                raise Exception("Failed to initialize MCP session")

            return responses[0]

    return MCPTestClient(mcp_server_executable, project_root)


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "docker: tests that require Docker services")
    config.addinivalue_line("markers", "native: tests that require native Python setup")
    config.addinivalue_line("markers", "slow: tests that take a long time to run")
    config.addinivalue_line("markers", "integration: integration tests")
    config.addinivalue_line("markers", "unit: unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on test mode."""
    test_mode = os.getenv("RETAINR_TEST_MODE", "auto")

    # Auto-detect test mode if not specified
    if test_mode == "auto":
        project_root = Path(__file__).parent.parent
        if (project_root / "venv").exists():
            test_mode = "native"
        else:
            test_mode = "docker"

    # Skip tests based on mode
    for item in items:
        if test_mode == "native" and "docker" in item.keywords:
            item.add_marker(
                pytest.mark.skip(reason="Docker tests skipped in native mode")
            )
        elif test_mode == "docker" and "native" in item.keywords:
            item.add_marker(
                pytest.mark.skip(reason="Native tests skipped in docker mode")
            )
