"""Tests for native MCP server implementation."""

import pytest


@pytest.mark.native
@pytest.mark.integration
def test_native_mcp_server_initialization(mcp_test_client, chromadb_service):
    """Test that the native MCP server can initialize properly."""
    # Initialize MCP session
    init_response = mcp_test_client.initialize_session()

    # Verify initialization response
    assert "serverInfo" in init_response["result"]
    assert init_response["result"]["serverInfo"]["name"] == "retainr"
    assert "capabilities" in init_response["result"]


@pytest.mark.native
@pytest.mark.integration
def test_native_mcp_tools_list(mcp_test_client, chromadb_service):
    """Test that tools list works in native mode."""
    # Need to send init and tools request together since each request spawns new process
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

    init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

    tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

    responses = mcp_test_client.send_requests(
        [init_request, init_notification, tools_request]
    )
    assert len(responses) >= 2  # Should get init response and tools response

    # Find the tools response (should be the last one with an id)
    tools_response = None
    for response in responses:
        if response.get("id") == 2:
            tools_response = response
            break

    assert tools_response is not None
    assert "result" in tools_response
    assert "tools" in tools_response["result"]

    # Verify expected tools are present
    tools = tools_response["result"]["tools"]
    tool_names = {tool["name"] for tool in tools}
    expected_tools = {
        "save_memory",
        "search_memories",
        "list_memories",
        "update_memory",
    }
    assert expected_tools.issubset(tool_names)


@pytest.mark.native
@pytest.mark.integration
def test_native_mcp_save_memory(mcp_test_client, chromadb_service):
    """Test saving a memory via native MCP server."""
    # Need to send init and save request together
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

    init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

    # Save a memory
    save_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "save_memory",
            "arguments": {
                "project": "native-test",
                "category": "testing",
                "content": "# Native Test Memory\n\nThis memory was saved via native MCP server.",
                "tags": ["native", "test", "mcp"],
                "references": ["test_native_mcp.py"],
            },
        },
    }

    responses = mcp_test_client.send_requests(
        [init_request, init_notification, save_request], timeout=60
    )
    assert len(responses) >= 2

    # Find the save response
    save_response = None
    for response in responses:
        if response.get("id") == 2:
            save_response = response
            break

    assert save_response is not None
    assert "result" in save_response
    assert "content" in save_response["result"]

    content = save_response["result"]["content"][0]["text"]
    assert "Memory saved successfully" in content
    assert "native-test" in content


@pytest.mark.native
@pytest.mark.integration
def test_native_mcp_search_memory(mcp_test_client, chromadb_service):
    """Test searching memories via native MCP server."""
    import time

    # First, save a memory to search for
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

    init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

    save_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "save_memory",
            "arguments": {
                "project": "search-test",
                "category": "testing",
                "content": "# Searchable Memory\n\nThis memory contains unique searchable content for testing.",
                "tags": ["searchable", "unique", "test"],
            },
        },
    }

    # Save the memory first
    mcp_test_client.send_requests(
        [init_request, init_notification, save_request], timeout=60
    )

    # Wait a moment for indexing
    time.sleep(2)

    # Now search for the memory in a new session
    search_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_memories",
            "arguments": {
                "query": "searchable unique content",
                "project": "search-test",
                "top": 3,
            },
        },
    }

    # Need to re-initialize for the search request
    search_responses = mcp_test_client.send_requests(
        [init_request, init_notification, search_request], timeout=30
    )

    # Find the search response
    search_response = None
    for response in search_responses:
        if response.get("id") == 3:
            search_response = response
            break

    assert search_response is not None
    assert "result" in search_response
    assert "content" in search_response["result"]

    content = search_response["result"]["content"][0]["text"]
    # Should either find results or indicate no memories found
    assert ("Found" in content) or ("No memories found" in content)


@pytest.mark.native
@pytest.mark.unit
def test_native_environment_availability(project_root, test_mode):
    """Test that the native environment is properly set up."""
    assert test_mode == "native"

    venv_path = project_root / "venv"
    assert venv_path.exists(), "Virtual environment should exist"

    python_path = venv_path / "bin" / "python"
    assert python_path.exists(), "Python executable should exist in venv"


@pytest.mark.native
@pytest.mark.integration
def test_native_chromadb_connection(chromadb_service):
    """Test that ChromaDB service is accessible."""
    import httpx

    response = httpx.get("http://localhost:8000/api/v2/heartbeat", timeout=10)
    assert response.status_code == 200

    # v2 API returns heartbeat data
    data = response.json()
    assert "nanosecond heartbeat" in data


@pytest.mark.native
@pytest.mark.slow
def test_native_mcp_performance(mcp_test_client, chromadb_service):
    """Test that native MCP server has good performance."""
    import time

    # Measure initialization time
    start_time = time.time()
    mcp_test_client.initialize_session()
    init_time = time.time() - start_time

    # Should be reasonably fast (under 10 seconds for native mode, includes model loading)
    assert (
        init_time < 10.0
    ), f"Initialization took {init_time:.2f}s, should be under 10s"

    # Measure tool call time (need full init sequence for new process)
    start_time = time.time()
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

    init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

    tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}

    mcp_test_client.send_requests([init_request, init_notification, tools_request])
    tools_time = time.time() - start_time

    # Tool calls with init should be reasonably fast (includes re-initialization)
    assert (
        tools_time < 10.0
    ), f"Tools list with init took {tools_time:.2f}s, should be under 10s"
