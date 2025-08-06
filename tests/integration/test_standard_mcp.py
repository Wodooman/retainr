"""Integration tests for standard MCP server implementation."""

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio


class MCPStdioClient:
    """Simple MCP client for testing stdio transport."""

    def __init__(self, command: list[str], cwd: str = None):
        self.command = command
        self.cwd = cwd
        self.process = None

    async def __aenter__(self):
        """Start the MCP server process."""
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.cwd,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the MCP server process."""
        if self.process:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()

    async def send_request(self, method: str, params: dict = None) -> dict:
        """Send a JSON-RPC request and get response."""
        if not self.process:
            raise RuntimeError("Process not started")

        request = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        # Read response
        response_line = await self.process.stdout.readline()
        if not response_line:
            stderr_output = await self.process.stderr.read()
            raise RuntimeError(
                f"No response from server. Stderr: {stderr_output.decode()}"
            )

        try:
            response = json.loads(response_line.decode().strip())

            # If this is an initialize response, send the initialized notification
            if method == "initialize" and "result" in response:
                notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
                notification_json = json.dumps(notification) + "\n"
                self.process.stdin.write(notification_json.encode())
                await self.process.stdin.drain()

            return response
        except json.JSONDecodeError as e:
            stderr_output = await self.process.stderr.read()
            raise RuntimeError(
                f"Invalid JSON response: {response_line.decode()}. Stderr: {stderr_output.decode()}"
            ) from e


@pytest.mark.asyncio
class TestStandardMCPServer:
    """Test suite for standard MCP server."""

    @pytest_asyncio.fixture
    async def mcp_client(self) -> AsyncIterator[MCPStdioClient]:
        """Create MCP client connected to native MCP server."""
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent

        # Use native MCP server command
        command = [sys.executable, "-m", "mcp_server"]

        async with MCPStdioClient(command=command, cwd=str(project_root)) as client:
            yield client

    async def test_server_initialization(self, mcp_client: MCPStdioClient):
        """Test MCP server initialization."""
        response = await mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
                "capabilities": {},
            },
        )

        assert "error" not in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert response["result"]["serverInfo"]["name"] == "retainr"
        assert "capabilities" in response["result"]

    async def test_tools_list(self, mcp_client: MCPStdioClient):
        """Test listing available tools."""
        # Initialize first
        await mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        )

        response = await mcp_client.send_request("tools/list")

        assert "error" not in response
        tools = response["result"]["tools"]

        # Check expected tools
        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "save_memory",
            "search_memories",
            "list_memories",
            "update_memory",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

        # Check tool schemas
        save_memory_tool = next(tool for tool in tools if tool["name"] == "save_memory")
        assert "inputSchema" in save_memory_tool
        assert save_memory_tool["inputSchema"]["type"] == "object"
        assert "project" in save_memory_tool["inputSchema"]["properties"]
        assert "category" in save_memory_tool["inputSchema"]["properties"]
        assert "content" in save_memory_tool["inputSchema"]["properties"]

    async def test_resources_list(self, mcp_client: MCPStdioClient):
        """Test listing available resources."""
        # Initialize first
        await mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        )

        response = await mcp_client.send_request("resources/list")

        assert "error" not in response
        assert "resources" in response["result"]
        # Resources list might be empty initially, which is fine

    async def test_save_memory_tool(self, mcp_client: MCPStdioClient):
        """Test saving a memory through the tool interface."""
        # Initialize first
        await mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        )

        response = await mcp_client.send_request(
            "tools/call",
            {
                "name": "save_memory",
                "arguments": {
                    "project": "test-project",
                    "category": "testing",
                    "content": "This is a test memory for MCP integration testing",
                    "tags": ["test", "mcp"],
                },
            },
        )

        assert "error" not in response
        result = response["result"]
        assert "content" in result
        content_text = result["content"][0]["text"]
        assert "Memory saved successfully!" in content_text
        assert "test-project" in content_text

    async def test_list_memories_tool(self, mcp_client: MCPStdioClient):
        """Test listing memories through the tool interface."""
        # Initialize first
        await mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        )

        # First save a memory
        await mcp_client.send_request(
            "tools/call",
            {
                "name": "save_memory",
                "arguments": {
                    "project": "test-list",
                    "category": "testing",
                    "content": "Memory for list testing",
                },
            },
        )

        # Then list memories
        response = await mcp_client.send_request(
            "tools/call", {"name": "list_memories", "arguments": {"limit": 5}}
        )

        assert "error" not in response
        result = response["result"]
        content_text = result["content"][0]["text"]
        assert "Recent memories" in content_text

    async def test_search_memories_tool(self, mcp_client: MCPStdioClient):
        """Test searching memories through the tool interface."""
        # Initialize first
        await mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        )

        # First save a memory
        await mcp_client.send_request(
            "tools/call",
            {
                "name": "save_memory",
                "arguments": {
                    "project": "search-test",
                    "category": "testing",
                    "content": "This memory is about Python programming and unit testing",
                },
            },
        )

        # Wait a moment for indexing
        await asyncio.sleep(1)

        # Then search for it
        response = await mcp_client.send_request(
            "tools/call",
            {
                "name": "search_memories",
                "arguments": {"query": "Python programming", "top": 3},
            },
        )

        assert "error" not in response
        result = response["result"]
        content_text = result["content"][0]["text"]

        # Should find our memory or indicate no results
        assert (
            "Found" in content_text and "Python programming" in content_text
        ) or "No memories found" in content_text

    async def test_error_handling(self, mcp_client: MCPStdioClient):
        """Test error handling for invalid requests."""
        # Initialize first
        await mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        )

        # Test invalid tool name
        response = await mcp_client.send_request(
            "tools/call", {"name": "nonexistent_tool", "arguments": {}}
        )

        # Handle both standard JSON-RPC errors and FastMCP tool result errors
        if "error" in response:
            assert response["error"]["code"] == -32601  # Method not found
        else:
            # FastMCP returns tool results with isError=True for unknown tools
            assert "result" in response
            assert response["result"].get("isError") is True

    async def test_tool_with_missing_args(self, mcp_client: MCPStdioClient):
        """Test tool call with missing required arguments."""
        # Initialize first
        await mcp_client.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "test", "version": "1.0"},
                "capabilities": {},
            },
        )

        # Test missing required arguments
        response = await mcp_client.send_request(
            "tools/call",
            {
                "name": "save_memory",
                "arguments": {
                    "project": "test"
                    # Missing category and content
                },
            },
        )

        # Should return an error or handle gracefully
        assert "error" in response or (
            "result" in response and response["result"].get("isError", False)
        )
