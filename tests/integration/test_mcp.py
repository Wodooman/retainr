"""Integration tests for MCP protocol endpoints."""

import pytest
import httpx


class TestMCPIntegration:
    """Test MCP protocol integration."""
    
    @pytest.fixture
    def base_url(self):
        """Base URL for MCP testing."""
        return "http://localhost:8000/mcp"
    
    @pytest.mark.asyncio
    async def test_mcp_initialize(self, base_url):
        """Test MCP initialization endpoint."""
        init_data = {
            "protocolVersion": "1.0",
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/initialize",
                json=init_data,
                timeout=30.0
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["protocolVersion"] == "1.0"
            assert "serverInfo" in data
            assert data["serverInfo"]["name"] == "retainr"
            assert "capabilities" in data
    
    @pytest.mark.asyncio
    async def test_mcp_tools_list(self, base_url):
        """Test MCP tools list endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/tools/list",
                json={},
                timeout=30.0
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "tools" in data
            tools = data["tools"]
            assert isinstance(tools, list)
            assert len(tools) > 0
            
            # Check expected tools
            tool_names = [tool["name"] for tool in tools]
            expected_tools = ["save_memory", "search_memories", "list_memories", "update_memory"]
            
            for expected_tool in expected_tools:
                assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    async def test_mcp_tool_call_save_memory(self, base_url):
        """Test MCP save_memory tool call."""
        tool_call = {
            "name": "save_memory",
            "arguments": {
                "project": "test-mcp",
                "category": "testing",
                "content": "# MCP Test Memory\n\nThis memory was created via MCP tool call.",
                "tags": ["mcp", "test"],
                "references": ["test_mcp.py"]
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/tools/call",
                json=tool_call,
                timeout=30.0
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "content" in data
            assert "isError" in data
            assert data["isError"] is False
            assert len(data["content"]) > 0
            assert data["content"][0]["type"] == "text"
    
    @pytest.mark.asyncio
    async def test_mcp_tool_call_search_memories(self, base_url):
        """Test MCP search_memories tool call."""
        # First save a memory to search for
        save_call = {
            "name": "save_memory",
            "arguments": {
                "project": "search-test",
                "category": "testing",
                "content": "# Searchable Memory\n\nThis memory should be findable via search.",
                "tags": ["searchable", "test"]
            }
        }
        
        async with httpx.AsyncClient() as client:
            # Save memory
            save_response = await client.post(
                f"{base_url}/tools/call",
                json=save_call,
                timeout=30.0
            )
            assert save_response.status_code == 200
            
            # Search for memory
            search_call = {
                "name": "search_memories",
                "arguments": {
                    "query": "searchable memory",
                    "top": 3
                }
            }
            
            search_response = await client.post(
                f"{base_url}/tools/call",
                json=search_call,
                timeout=30.0
            )
            
            assert search_response.status_code == 200
            data = search_response.json()
            
            assert "content" in data
            assert data["isError"] is False
            assert len(data["content"]) > 0
    
    @pytest.mark.asyncio
    async def test_mcp_tool_call_list_memories(self, base_url):
        """Test MCP list_memories tool call."""
        tool_call = {
            "name": "list_memories",
            "arguments": {
                "limit": 5
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/tools/call",
                json=tool_call,
                timeout=30.0
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "content" in data
            assert data["isError"] is False
            assert len(data["content"]) > 0
            assert data["content"][0]["type"] == "text"
    
    @pytest.mark.asyncio
    async def test_mcp_tool_call_invalid_tool(self, base_url):
        """Test MCP tool call with invalid tool name."""
        tool_call = {
            "name": "invalid_tool",
            "arguments": {}
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/tools/call",
                json=tool_call,
                timeout=30.0
            )
            
            assert response.status_code == 400
    
    @pytest.mark.asyncio
    async def test_mcp_resources_list(self, base_url):
        """Test MCP resources list endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/resources/list",
                json={},
                timeout=30.0
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "resources" in data
            assert isinstance(data["resources"], list)
    
    @pytest.mark.asyncio
    async def test_mcp_full_workflow(self, base_url):
        """Test complete MCP workflow."""
        async with httpx.AsyncClient() as client:
            # 1. Initialize
            init_response = await client.post(
                f"{base_url}/initialize",
                json={
                    "protocolVersion": "1.0",
                    "clientInfo": {"name": "workflow-test"}
                },
                timeout=30.0
            )
            assert init_response.status_code == 200
            
            # 2. List tools
            tools_response = await client.post(
                f"{base_url}/tools/list",
                json={},
                timeout=30.0
            )
            assert tools_response.status_code == 200
            
            # 3. Save memory
            save_response = await client.post(
                f"{base_url}/tools/call",
                json={
                    "name": "save_memory",
                    "arguments": {
                        "project": "workflow-test",
                        "category": "testing",
                        "content": "# Workflow Test\n\nTesting complete MCP workflow.",
                        "tags": ["workflow", "test"]
                    }
                },
                timeout=30.0
            )
            assert save_response.status_code == 200
            assert save_response.json()["isError"] is False
            
            # 4. Search memories
            search_response = await client.post(
                f"{base_url}/tools/call",
                json={
                    "name": "search_memories",
                    "arguments": {
                        "query": "workflow test",
                        "project": "workflow-test"
                    }
                },
                timeout=30.0
            )
            assert search_response.status_code == 200
            assert search_response.json()["isError"] is False
            
            # 5. List resources
            resources_response = await client.post(
                f"{base_url}/resources/list",
                json={},
                timeout=30.0
            )
            assert resources_response.status_code == 200