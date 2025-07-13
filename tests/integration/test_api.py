"""Integration tests for the FastAPI application."""

import pytest
import httpx
from tests.fixtures.sample_memory import sample_memory_json


class TestAPIIntegration:
    """Test API endpoints integration."""
    
    @pytest.fixture
    def base_url(self):
        """Base URL for API testing."""
        return "http://localhost:8000"
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, base_url):
        """Test health check endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert "memory_dir" in data
            assert "chroma_url" in data
            assert "embedding_model" in data
            assert "chroma_stats" in data
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, base_url):
        """Test root endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["message"] == "retainr MCP Server"
            assert data["version"] == "0.1.0"
            assert data["status"] == "running"
    
    @pytest.mark.asyncio
    async def test_create_memory(self, base_url):
        """Test creating a memory via API."""
        memory_data = sample_memory_json()
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/memory/",
                json=memory_data,
                timeout=30.0
            )
            
            assert response.status_code == 201
            data = response.json()
            
            assert "id" in data
            assert "file_path" in data
            assert "message" in data
            assert len(data["id"]) == 12  # Memory ID length
    
    @pytest.mark.asyncio
    async def test_search_memories(self, base_url):
        """Test searching memories."""
        # First create a memory
        memory_data = sample_memory_json()
        
        async with httpx.AsyncClient() as client:
            # Create memory
            create_response = await client.post(
                f"{base_url}/memory/",
                json=memory_data,
                timeout=30.0
            )
            assert create_response.status_code == 201
            
            # Search for the memory
            search_response = await client.get(
                f"{base_url}/memory/search",
                params={"query": "API test", "top": 3},
                timeout=30.0
            )
            
            assert search_response.status_code == 200
            data = search_response.json()
            
            assert "query" in data
            assert "results" in data
            assert "total" in data
            assert data["query"] == "API test"
            assert isinstance(data["results"], list)
            assert data["total"] >= 0
    
    @pytest.mark.asyncio
    async def test_list_memories(self, base_url):
        """Test listing memories."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/memory/",
                params={"limit": 10},
                timeout=30.0
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "memories" in data
            assert "total" in data
            assert isinstance(data["memories"], list)
            assert isinstance(data["total"], int)
    
    @pytest.mark.asyncio
    async def test_memory_lifecycle(self, base_url):
        """Test complete memory lifecycle: create, get, update."""
        memory_data = sample_memory_json()
        
        async with httpx.AsyncClient() as client:
            # Create memory
            create_response = await client.post(
                f"{base_url}/memory/",
                json=memory_data,
                timeout=30.0
            )
            assert create_response.status_code == 201
            memory_id = create_response.json()["id"]
            
            # Get memory
            get_response = await client.get(
                f"{base_url}/memory/{memory_id}",
                timeout=30.0
            )
            assert get_response.status_code == 200
            
            get_data = get_response.json()
            assert get_data["id"] == memory_id
            assert "entry" in get_data
            assert get_data["entry"]["project"] == memory_data["project"]
            
            # Update memory
            update_response = await client.patch(
                f"{base_url}/memory/{memory_id}",
                json={"outdated": True},
                timeout=30.0
            )
            assert update_response.status_code == 200
            
            # Verify update
            verify_response = await client.get(
                f"{base_url}/memory/{memory_id}",
                timeout=30.0
            )
            assert verify_response.status_code == 200
            assert verify_response.json()["entry"]["outdated"] is True
    
    @pytest.mark.asyncio
    async def test_memory_not_found(self, base_url):
        """Test getting non-existent memory returns 404."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/memory/nonexistent-id",
                timeout=30.0
            )
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_memory(self, base_url):
        """Test updating non-existent memory returns 404."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{base_url}/memory/nonexistent-id",
                json={"outdated": True},
                timeout=30.0
            )
            assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_invalid_memory_data(self, base_url):
        """Test creating memory with invalid data returns 422."""
        invalid_data = {
            "project": "",  # Empty project name
            "category": "test",
            "content": "test"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/memory/",
                json=invalid_data,
                timeout=30.0
            )
            assert response.status_code == 422