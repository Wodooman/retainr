#!/usr/bin/env python3
"""
Comprehensive MCP Protocol Compliance Tests for retainr

Tests the MCP server against the official MCP protocol specification
to ensure standards compliance and compatibility with MCP clients.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio


class MCPTestClient:
    """Test client for MCP protocol validation."""

    def __init__(self, command: list[str], cwd: str = None):
        self.command = command
        self.cwd = cwd
        self.process = None
        self.initialized = False

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

    async def send_request(
        self, method: str, params: dict[str, Any] = None, request_id: int = 1
    ) -> dict[str, Any]:
        """Send a JSON-RPC request and get response."""
        if not self.process:
            raise RuntimeError("Process not started")

        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        # Send request
        request_json = json.dumps(request) + "\n"
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        # Read response
        response_line = await asyncio.wait_for(
            self.process.stdout.readline(), timeout=10.0
        )

        if not response_line:
            stderr_output = await self.process.stderr.read()
            raise RuntimeError(
                f"No response from server. Stderr: {stderr_output.decode()}"
            )

        try:
            response = json.loads(response_line.decode().strip())
            return response
        except json.JSONDecodeError as e:
            stderr_output = await self.process.stderr.read()
            raise RuntimeError(
                f"Invalid JSON response: {response_line.decode()}. Stderr: {stderr_output.decode()}"
            ) from e

    async def initialize(self) -> dict[str, Any]:
        """Initialize the MCP session."""
        if self.initialized:
            return {"status": "already_initialized"}

        response = await self.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "MCP Test Client", "version": "1.0.0"},
                "capabilities": {},
            },
        )

        if "result" in response:
            # Send initialized notification
            notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            notification_json = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_json.encode())
            await self.process.stdin.drain()

            self.initialized = True

        return response


@pytest_asyncio.fixture
async def mcp_client():
    """Create MCP client connected to the native MCP server."""
    project_root = Path(__file__).parent.parent

    # Use native MCP server command
    command = [sys.executable, "-m", "mcp_server"]

    # Create a fresh client for each test
    client = MCPTestClient(command, cwd=str(project_root))
    async with client:
        yield client


@pytest.mark.asyncio
class TestMCPProtocolCompliance:
    """Test MCP protocol compliance."""

    async def test_initialization(self, mcp_client: MCPTestClient):
        """Test MCP server initialization according to protocol."""
        response = await mcp_client.initialize()

        # Check response structure
        assert "result" in response, f"Expected 'result' in response: {response}"
        result = response["result"]

        # Required fields per MCP spec
        assert "protocolVersion" in result
        assert "serverInfo" in result
        assert "capabilities" in result

        # Check server info
        server_info = result["serverInfo"]
        assert "name" in server_info
        assert "version" in server_info
        assert server_info["name"] == "retainr"

        # Check capabilities
        capabilities = result["capabilities"]
        assert isinstance(capabilities, dict)
        assert "tools" in capabilities
        assert "resources" in capabilities

    async def test_tools_list(self, mcp_client: MCPTestClient):
        """Test tools/list method."""
        await mcp_client.initialize()

        response = await mcp_client.send_request("tools/list", {}, 2)

        assert "result" in response
        result = response["result"]
        assert "tools" in result

        tools = result["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 0

        # Check each tool has required fields
        expected_tools = {
            "save_memory",
            "search_memories",
            "list_memories",
            "update_memory",
        }
        found_tools = {tool["name"] for tool in tools}

        assert expected_tools.issubset(
            found_tools
        ), f"Missing tools: {expected_tools - found_tools}"

        # Check tool schema structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

            schema = tool["inputSchema"]
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema

    async def test_resources_list(self, mcp_client: MCPTestClient):
        """Test resources/list method."""
        await mcp_client.initialize()

        response = await mcp_client.send_request("resources/list", {}, 3)

        assert "result" in response
        result = response["result"]
        assert "resources" in result

        # Resources list might be empty initially
        resources = result["resources"]
        assert isinstance(resources, list)

    async def test_save_memory_tool(self, mcp_client: MCPTestClient):
        """Test save_memory tool functionality."""
        await mcp_client.initialize()

        response = await mcp_client.send_request(
            "tools/call",
            {
                "name": "save_memory",
                "arguments": {
                    "project": "test-protocol",
                    "category": "testing",
                    "content": "# MCP Protocol Test\n\nThis memory tests the MCP protocol compliance.",
                    "tags": ["test", "mcp", "protocol"],
                    "references": ["test_mcp_protocol.py"],
                },
            },
            4,
        )

        assert "result" in response
        result = response["result"]

        # Check tool response structure
        assert "content" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) > 0

        content_item = result["content"][0]
        assert "type" in content_item
        assert "text" in content_item
        assert content_item["type"] == "text"
        assert "Memory saved successfully" in content_item["text"]

    async def test_search_memories_tool(self, mcp_client: MCPTestClient):
        """Test search_memories tool functionality."""
        await mcp_client.initialize()

        # First save a memory to search for
        await mcp_client.send_request(
            "tools/call",
            {
                "name": "save_memory",
                "arguments": {
                    "project": "search-test",
                    "category": "testing",
                    "content": "Memory about Python MCP testing framework",
                    "tags": ["python", "testing"],
                },
            },
            5,
        )

        # Wait a moment for indexing
        await asyncio.sleep(2)

        # Now search for it
        response = await mcp_client.send_request(
            "tools/call",
            {
                "name": "search_memories",
                "arguments": {"query": "Python testing", "top": 3},
            },
            6,
        )

        assert "result" in response
        result = response["result"]
        assert "content" in result

        content_text = result["content"][0]["text"]
        # Should find results or indicate no results
        assert ("Found" in content_text) or ("No memories found" in content_text)

    async def test_list_memories_tool(self, mcp_client: MCPTestClient):
        """Test list_memories tool functionality."""
        await mcp_client.initialize()

        response = await mcp_client.send_request(
            "tools/call", {"name": "list_memories", "arguments": {"limit": 5}}, 7
        )

        assert "result" in response
        result = response["result"]
        assert "content" in result

        content_text = result["content"][0]["text"]
        assert ("Recent memories" in content_text) or (
            "No memories found" in content_text
        )

    async def test_update_memory_tool(self, mcp_client: MCPTestClient):
        """Test update_memory tool functionality."""
        await mcp_client.initialize()

        # First save a memory
        save_response = await mcp_client.send_request(
            "tools/call",
            {
                "name": "save_memory",
                "arguments": {
                    "project": "update-test",
                    "category": "testing",
                    "content": "Memory to be updated",
                    "tags": ["update", "test"],
                },
            },
            8,
        )

        # Extract memory ID from response
        save_text = save_response["result"]["content"][0]["text"]
        memory_id = None
        for line in save_text.split("\n"):
            if line.startswith("ID:"):
                memory_id = line.split(":", 1)[1].strip()
                break

        if memory_id:
            # Try to update the memory
            response = await mcp_client.send_request(
                "tools/call",
                {
                    "name": "update_memory",
                    "arguments": {"memory_id": memory_id, "outdated": True},
                },
                9,
            )

            assert "result" in response
            result = response["result"]
            assert "content" in result

            content_text = result["content"][0]["text"]
            assert "marked as outdated" in content_text or "not found" in content_text

    async def test_error_handling(self, mcp_client: MCPTestClient):
        """Test error handling for invalid requests."""
        await mcp_client.initialize()

        # Test invalid tool name
        response = await mcp_client.send_request(
            "tools/call", {"name": "nonexistent_tool", "arguments": {}}, 10
        )

        # FastMCP returns tool results with isError flag rather than JSON-RPC errors
        # for application-level errors like unknown tools
        if "error" in response:
            # Standard JSON-RPC error format
            error = response["error"]
            assert "code" in error
            assert "message" in error
        else:
            # FastMCP error format - tool result with isError flag
            assert "result" in response
            result = response["result"]
            assert "content" in result
            # Should indicate it's an error
            assert result.get("isError", False) or "Unknown tool" in str(result)

    async def test_json_rpc_compliance(self, mcp_client: MCPTestClient):
        """Test JSON-RPC 2.0 protocol compliance."""
        await mcp_client.initialize()

        # Test standard request with ID - should get response with same ID
        request_id = 42
        response = await mcp_client.send_request("tools/list", {}, request_id)

        # Should have correct JSON-RPC structure
        assert response.get("jsonrpc") == "2.0"
        assert response.get("id") == request_id
        assert "result" in response or "error" in response

        # Test that response contains expected fields for tools/list
        if "result" in response:
            result = response["result"]
            assert "tools" in result
            assert isinstance(result["tools"], list)


@pytest.mark.asyncio
async def test_mcp_server_startup():
    """Test that MCP server can start and respond to basic requests."""
    project_root = Path(__file__).parent.parent

    # Use native MCP server command
    command = [sys.executable, "-m", "mcp_server"]

    async with MCPTestClient(command, cwd=str(project_root)) as client:
        # Test basic initialization
        response = await client.initialize()
        assert "result" in response
        assert response["result"]["serverInfo"]["name"] == "retainr"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
