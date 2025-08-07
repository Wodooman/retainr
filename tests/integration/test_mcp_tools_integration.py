#!/usr/bin/env python3
"""Integration tests for MCP tools with actual ChromaDB operations."""

import tempfile
import time
from pathlib import Path

import httpx
import pytest


@pytest.mark.integration
class TestMCPToolsIntegration:
    """Test MCP tools integration with ChromaDB and file storage."""

    @pytest.fixture(scope="class")
    def temp_memory_dir(self):
        """Create a temporary memory directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture(scope="class")
    def integration_settings(self, temp_memory_dir):
        """Create settings for integration testing."""
        from mcp_server.config import Settings

        settings = Settings()
        settings.memory_dir = temp_memory_dir
        settings.chroma_collection = "test_integration"
        return settings

    @pytest.fixture(scope="class")
    def chromadb_available(self):
        """Check if ChromaDB is available for testing."""
        try:
            response = httpx.get("http://localhost:8000/api/v2/heartbeat", timeout=5)
            if response.status_code == 200:
                return True
        except (httpx.RequestError, httpx.TimeoutException):
            pytest.skip("ChromaDB not available. Start with 'make start-chromadb'")
        return False

    @pytest.fixture
    def mcp_client(self, project_root):
        """Create MCP client for integration testing."""
        import sys

        from tests.conftest import MCPTestClient

        executable = [sys.executable, "-m", "mcp_server"]
        return MCPTestClient(executable, project_root)

    def test_save_memory_with_immediate_search_availability(self, mcp_client):
        """Test that saved memories are immediately available for search."""
        # Initialize MCP session
        init_response = mcp_client.initialize_session()
        assert "result" in init_response

        # Save a memory
        save_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "integration-test",
                    "category": "testing",
                    "content": "# Integration Test Memory\n\nThis memory tests immediate search availability after save.",
                    "tags": ["integration", "search", "availability"],
                    "references": ["test_mcp_tools_integration.py"],
                },
            },
        }

        save_responses = mcp_client.send_request(save_request)
        assert len(save_responses) > 0
        save_response = save_responses[0]
        assert "result" in save_response
        assert (
            "Memory saved successfully" in save_response["result"]["content"][0]["text"]
        )

        # Wait a moment for indexing
        time.sleep(2)

        # Search for the memory immediately
        search_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "integration test immediate availability",
                    "project": "integration-test",
                    "top": 5,
                },
            },
        }

        search_responses = mcp_client.send_request(search_request)
        assert len(search_responses) > 0
        search_response = search_responses[0]
        assert "result" in search_response

        search_content = search_response["result"]["content"][0]["text"]
        assert "Found" in search_content or "integration-test" in search_content

    def test_update_memory_search_consistency(self, mcp_client):
        """Test that memory updates are reflected in search results."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save initial memory
        save_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "update-test",
                    "category": "testing",
                    "content": "# Update Test Memory\n\nOriginal content for update testing.",
                    "tags": ["update", "consistency"],
                    "references": ["update_test.py"],
                },
            },
        }

        save_responses = mcp_client.send_request(save_request)
        save_response = save_responses[0]
        assert "result" in save_response

        # Extract memory ID from response
        save_text = save_response["result"]["content"][0]["text"]
        memory_id = None
        for line in save_text.split("\n"):
            if "ID:" in line:
                memory_id = line.split("ID:")[1].strip()
                break

        assert memory_id is not None

        # Wait for indexing
        time.sleep(2)

        # Update the memory to outdated
        update_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "update_memory",
                "arguments": {
                    "memory_id": memory_id,
                    "outdated": True,
                },
            },
        }

        update_responses = mcp_client.send_request(update_request)
        update_response = update_responses[0]
        assert "result" in update_response
        assert "marked as outdated" in update_response["result"]["content"][0]["text"]

        # Wait for update to propagate
        time.sleep(2)

        # List memories to verify status update
        list_request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "update-test",
                    "limit": 10,
                },
            },
        }

        list_responses = mcp_client.send_request(list_request)
        list_response = list_responses[0]
        assert "result" in list_response

        list_content = list_response["result"]["content"][0]["text"]
        assert "❌" in list_content or "outdated" in list_content

    def test_concurrent_save_search_operations(self, mcp_client):
        """Test concurrent save and search operations don't interfere."""
        import queue
        import threading

        # Initialize MCP session
        mcp_client.initialize_session()

        results_queue = queue.Queue()
        errors_queue = queue.Queue()

        def save_memory_operation(memory_id):
            try:
                save_request = {
                    "jsonrpc": "2.0",
                    "id": memory_id,
                    "method": "tools/call",
                    "params": {
                        "name": "save_memory",
                        "arguments": {
                            "project": "concurrent-test",
                            "category": "performance",
                            "content": f"# Concurrent Memory {memory_id}\n\nThis is memory number {memory_id} for concurrent testing.",
                            "tags": ["concurrent", f"memory-{memory_id}"],
                            "references": [f"concurrent_{memory_id}.py"],
                        },
                    },
                }

                responses = mcp_client.send_request(save_request)
                if responses and "result" in responses[0]:
                    results_queue.put(f"save_{memory_id}_success")
                else:
                    errors_queue.put(f"save_{memory_id}_failed")
            except Exception as e:
                errors_queue.put(f"save_{memory_id}_error: {str(e)}")

        def search_memory_operation(search_id):
            try:
                search_request = {
                    "jsonrpc": "2.0",
                    "id": search_id + 100,
                    "method": "tools/call",
                    "params": {
                        "name": "search_memories",
                        "arguments": {
                            "query": "concurrent testing performance",
                            "project": "concurrent-test",
                            "top": 3,
                        },
                    },
                }

                responses = mcp_client.send_request(search_request)
                if responses and "result" in responses[0]:
                    results_queue.put(f"search_{search_id}_success")
                else:
                    errors_queue.put(f"search_{search_id}_failed")
            except Exception as e:
                errors_queue.put(f"search_{search_id}_error: {str(e)}")

        # Create and start threads for concurrent operations
        threads = []

        # Start save operations
        for i in range(3):
            thread = threading.Thread(target=save_memory_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Add small delay then start search operations
        time.sleep(1)
        for i in range(2):
            thread = threading.Thread(target=search_memory_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)

        # Collect results
        success_count = 0
        errors = []

        while not results_queue.empty():
            success_count += 1
            results_queue.get()

        while not errors_queue.empty():
            errors.append(errors_queue.get())

        # Verify operations succeeded
        assert (
            success_count >= 3
        ), f"Expected at least 3 successful operations, got {success_count}"
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_large_batch_memory_operations(self, mcp_client):
        """Test handling of large batch memory operations."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save multiple memories in sequence
        memory_ids = []
        for i in range(10):
            save_request = {
                "jsonrpc": "2.0",
                "id": i + 10,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": {
                        "project": "batch-test",
                        "category": "scalability",
                        "content": f"# Batch Memory {i}\n\nThis is memory {i} in a large batch test with content that varies for each memory entry to ensure proper indexing.",
                        "tags": ["batch", f"item-{i}", "scalability"],
                        "references": [f"batch_item_{i}.py"],
                    },
                },
            }

            responses = mcp_client.send_request(save_request, timeout=60)
            assert len(responses) > 0
            response = responses[0]
            assert "result" in response

            # Extract memory ID
            save_text = response["result"]["content"][0]["text"]
            for line in save_text.split("\n"):
                if "ID:" in line:
                    memory_ids.append(line.split("ID:")[1].strip())
                    break

        assert len(memory_ids) == 10

        # Wait for all indexing to complete
        time.sleep(5)

        # Search should find multiple relevant memories
        search_request = {
            "jsonrpc": "2.0",
            "id": 100,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "batch scalability testing",
                    "project": "batch-test",
                    "top": 10,
                },
            },
        }

        search_responses = mcp_client.send_request(search_request, timeout=60)
        search_response = search_responses[0]
        assert "result" in search_response

        search_content = search_response["result"]["content"][0]["text"]
        # Should find multiple batch memories
        assert "Found" in search_content

        # List all memories should show all 10
        list_request = {
            "jsonrpc": "2.0",
            "id": 101,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "batch-test",
                    "limit": 15,
                },
            },
        }

        list_responses = mcp_client.send_request(list_request, timeout=30)
        list_response = list_responses[0]
        assert "result" in list_response

        list_content = list_response["result"]["content"][0]["text"]
        # Count the number of memories listed
        memory_count = list_content.count("✅") + list_content.count("❌")
        assert (
            memory_count >= 10
        ), f"Expected at least 10 memories, found {memory_count}"

    def test_memory_lifecycle_with_vector_sync(self, mcp_client):
        """Test complete memory lifecycle ensuring vector database sync."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # 1. Save memory
        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "lifecycle-test",
                    "category": "integration",
                    "content": "# Lifecycle Test\n\nThis memory will go through a complete lifecycle test including save, search, update, and verification.",
                    "tags": ["lifecycle", "integration", "sync"],
                    "references": ["lifecycle_test.py"],
                },
            },
        }

        save_responses = mcp_client.send_request(save_request)
        save_response = save_responses[0]
        assert "result" in save_response

        # Extract memory ID
        save_text = save_response["result"]["content"][0]["text"]
        memory_id = None
        for line in save_text.split("\n"):
            if "ID:" in line:
                memory_id = line.split("ID:")[1].strip()
                break
        assert memory_id is not None

        # 2. Wait and verify search finds it
        time.sleep(3)
        search_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "lifecycle complete integration",
                    "project": "lifecycle-test",
                    "top": 3,
                },
            },
        }

        search_responses = mcp_client.send_request(search_request)
        search_response = search_responses[0]
        assert "result" in search_response
        search_content = search_response["result"]["content"][0]["text"]
        assert "lifecycle-test" in search_content or "Found" in search_content

        # 3. Update memory status
        update_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "update_memory",
                "arguments": {
                    "memory_id": memory_id,
                    "outdated": True,
                },
            },
        }

        update_responses = mcp_client.send_request(update_request)
        update_response = update_responses[0]
        assert "result" in update_response
        assert "marked as outdated" in update_response["result"]["content"][0]["text"]

        # 4. Wait and verify list shows updated status
        time.sleep(2)
        list_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "lifecycle-test",
                    "limit": 5,
                },
            },
        }

        list_responses = mcp_client.send_request(list_request)
        list_response = list_responses[0]
        assert "result" in list_response
        list_content = list_response["result"]["content"][0]["text"]
        # Should show outdated status
        assert "❌" in list_content or "outdated" in list_content

        # 5. Search should still find it (even if outdated)
        final_search_responses = mcp_client.send_request(search_request)
        final_search_response = final_search_responses[0]
        assert "result" in final_search_response
        # Memory should still be searchable even when marked outdated
        final_search_content = final_search_response["result"]["content"][0]["text"]
        assert (
            "lifecycle-test" in final_search_content or "Found" in final_search_content
        )

    def test_cross_project_search_isolation(self, mcp_client):
        """Test that project filters properly isolate search results."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save memory in project A
        save_request_a = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "project-a",
                    "category": "isolation",
                    "content": "# Project A Memory\n\nThis memory belongs to project A and should be isolated from project B searches.",
                    "tags": ["project-a", "isolation"],
                    "references": ["project_a.py"],
                },
            },
        }

        # Save memory in project B
        save_request_b = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "project-b",
                    "category": "isolation",
                    "content": "# Project B Memory\n\nThis memory belongs to project B and should be isolated from project A searches.",
                    "tags": ["project-b", "isolation"],
                    "references": ["project_b.py"],
                },
            },
        }

        # Save both memories
        mcp_client.send_request(save_request_a)
        mcp_client.send_request(save_request_b)

        time.sleep(3)  # Wait for indexing

        # Search project A only
        search_a_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "isolation memory project",
                    "project": "project-a",
                    "top": 5,
                },
            },
        }

        search_a_responses = mcp_client.send_request(search_a_request)
        search_a_response = search_a_responses[0]
        assert "result" in search_a_response
        search_a_content = search_a_response["result"]["content"][0]["text"]

        # Should find project A, not project B
        if "Found" in search_a_content:
            assert "project-a" in search_a_content
            assert "project-b" not in search_a_content

        # Search project B only
        search_b_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "isolation memory project",
                    "project": "project-b",
                    "top": 5,
                },
            },
        }

        search_b_responses = mcp_client.send_request(search_b_request)
        search_b_response = search_b_responses[0]
        assert "result" in search_b_response
        search_b_content = search_b_response["result"]["content"][0]["text"]

        # Should find project B, not project A
        if "Found" in search_b_content:
            assert "project-b" in search_b_content
            assert "project-a" not in search_b_content

    def test_tag_based_search_filtering(self, mcp_client):
        """Test that tag filters work properly in search."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save memories with different tag combinations
        memory_configs = [
            {
                "project": "tag-test",
                "content": "Memory with python and testing tags",
                "tags": ["python", "testing", "unit"],
            },
            {
                "project": "tag-test",
                "content": "Memory with javascript and testing tags",
                "tags": ["javascript", "testing", "integration"],
            },
            {
                "project": "tag-test",
                "content": "Memory with python and documentation tags",
                "tags": ["python", "documentation", "api"],
            },
        ]

        for i, config in enumerate(memory_configs):
            save_request = {
                "jsonrpc": "2.0",
                "id": i + 1,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": {
                        "project": config["project"],
                        "category": "filtering",
                        "content": f"# Tag Test Memory {i}\n\n{config['content']}",
                        "tags": config["tags"],
                        "references": [f"tag_test_{i}.py"],
                    },
                },
            }
            mcp_client.send_request(save_request)

        time.sleep(4)  # Wait for indexing

        # Search with python tag filter
        python_search_request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "memory tags",
                    "project": "tag-test",
                    "tags": ["python"],
                    "top": 5,
                },
            },
        }

        python_responses = mcp_client.send_request(python_search_request)
        python_response = python_responses[0]
        assert "result" in python_response
        python_content = python_response["result"]["content"][0]["text"]

        # Should find memories with python tag
        if "Found" in python_content:
            # Count occurrences - should find 2 python memories
            python_count = python_content.lower().count("python")
            javascript_count = python_content.lower().count("javascript")
            assert python_count >= 2
            # Should not find javascript-only memories
            assert javascript_count == 0 or python_count > javascript_count

        # Search with testing tag filter
        testing_search_request = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "memory tags",
                    "project": "tag-test",
                    "tags": ["testing"],
                    "top": 5,
                },
            },
        }

        testing_responses = mcp_client.send_request(testing_search_request)
        testing_response = testing_responses[0]
        assert "result" in testing_response
        testing_content = testing_response["result"]["content"][0]["text"]

        # Should find memories with testing tag
        if "Found" in testing_content:
            testing_count = testing_content.lower().count("testing")
            assert testing_count >= 2
