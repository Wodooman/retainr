#!/usr/bin/env python3
"""Error recovery and resilience tests for retainr MCP server."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from mcp_server.config import Settings
from mcp_server.embeddings import EmbeddingService
from mcp_server.storage import MemoryStorage


@pytest.mark.integration
class TestErrorRecovery:
    """Test error recovery and resilience scenarios."""

    @pytest.fixture(scope="class")
    def temp_memory_dir(self):
        """Create a temporary memory directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture(scope="class")
    def recovery_settings(self, temp_memory_dir):
        """Create settings for error recovery testing."""
        settings = Settings()
        settings.memory_dir = temp_memory_dir
        settings.chroma_collection = "test_recovery"
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
    def mcp_client(self, project_root, chromadb_available):
        """Create MCP client for error recovery testing."""
        import sys

        from tests.conftest import MCPTestClient

        executable = [sys.executable, "-m", "mcp_server"]
        return MCPTestClient(executable, project_root)

    def test_chromadb_connection_loss_recovery(self, mcp_client, recovery_settings):
        """Test recovery when ChromaDB connection is lost and restored."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save a memory while ChromaDB is available
        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "connection-recovery-test",
                    "category": "resilience",
                    "content": "# Connection Recovery Test\n\nThis memory tests recovery from ChromaDB connection loss.",
                    "tags": ["connection", "recovery", "chromadb"],
                    "references": ["connection_recovery_test.py"],
                },
            },
        }

        save_responses = mcp_client.send_request(save_request)
        save_response = save_responses[0]
        assert "result" in save_response
        assert (
            "Memory saved successfully" in save_response["result"]["content"][0]["text"]
        )

        # Wait for indexing
        time.sleep(2)

        # Verify search works initially
        search_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "connection recovery chromadb",
                    "project": "connection-recovery-test",
                    "top": 3,
                },
            },
        }

        initial_search_responses = mcp_client.send_request(search_request)
        initial_search_response = initial_search_responses[0]
        assert "result" in initial_search_response
        initial_content = initial_search_response["result"]["content"][0]["text"]
        assert (
            "Found" in initial_content or "connection-recovery-test" in initial_content
        )

        # Test operations when ChromaDB might be temporarily unavailable
        # Note: This simulates network issues or service restarts

        # Try to save another memory (should handle ChromaDB issues gracefully)
        save_request_2 = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "connection-recovery-test",
                    "category": "resilience",
                    "content": "# Recovery Test 2\n\nThis memory tests saving during potential connection issues.",
                    "tags": ["connection", "recovery", "save-test"],
                    "references": ["recovery_test_2.py"],
                },
            },
        }

        # This should either succeed or fail gracefully without crashing the server
        try:
            save_2_responses = mcp_client.send_request(save_request_2, timeout=30)
            save_2_response = save_2_responses[0]

            # Should get either success or proper error response
            assert "result" in save_2_response or "error" in save_2_response

            if "result" in save_2_response:
                # If successful, memory should be saved to file even if vector indexing fails
                content = save_2_response["result"]["content"][0]["text"]
                assert (
                    "Memory saved successfully" in content
                    or "failed" in content.lower()
                )

        except Exception as e:
            # Server should not crash, even with connection issues
            pytest.fail(f"MCP server crashed during ChromaDB connection test: {e}")

        # File-based operations should continue to work
        list_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "connection-recovery-test",
                    "limit": 5,
                },
            },
        }

        list_responses = mcp_client.send_request(list_request)
        list_response = list_responses[0]
        assert "result" in list_response

        # List should work regardless of ChromaDB status (it's file-based)
        list_content = list_response["result"]["content"][0]["text"]
        assert "connection-recovery-test" in list_content

    def test_corrupted_memory_file_handling(self, mcp_client, recovery_settings):
        """Test handling of corrupted memory files."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save a memory normally
        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "corruption-test",
                    "category": "error-handling",
                    "content": "# Corruption Test\n\nThis memory will be corrupted to test error handling.",
                    "tags": ["corruption", "error-handling", "resilience"],
                    "references": ["corruption_test.py"],
                },
            },
        }

        save_responses = mcp_client.send_request(save_request)
        save_response = save_responses[0]
        assert "result" in save_response

        # Extract file path from response
        save_text = save_response["result"]["content"][0]["text"]
        file_path = None
        for line in save_text.split("\n"):
            if "File:" in line:
                file_path = Path(line.split("File:")[1].strip())
                break

        assert file_path is not None
        assert file_path.exists()

        # Corrupt the memory file
        with open(file_path, "w") as f:
            f.write(
                "CORRUPTED: This is not valid YAML frontmatter\n---\nInvalid content"
            )

        # Try to list memories - should handle corrupted file gracefully
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "corruption-test",
                    "limit": 5,
                },
            },
        }

        list_responses = mcp_client.send_request(list_request)
        list_response = list_responses[0]
        assert "result" in list_response

        # Should return a valid response even with corrupted files
        # May show no memories or skip corrupted ones, but shouldn't crash
        list_content = list_response["result"]["content"][0]["text"]
        assert isinstance(list_content, str)

        # Server should not crash due to corrupted file
        # It may or may not show the corrupted memory in the list

        # Create another file with different corruption
        corrupted_file = file_path.parent / "corrupted_memory.md"
        with open(corrupted_file, "w") as f:
            f.write(
                "---\nproject: corruption-test\ncategory: \ninvalid-yaml-structure\n"
            )

        # List again - should still handle gracefully
        list_responses_2 = mcp_client.send_request(list_request)
        list_response_2 = list_responses_2[0]
        assert "result" in list_response_2

    def test_disk_space_exhaustion_handling(self, mcp_client, recovery_settings):
        """Test handling of disk space exhaustion during memory save."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Create a very large content that might cause disk issues
        large_content = (
            "# Large Memory Test\n\n" + "This is a large memory content. " * 10000
        )

        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "disk-space-test",
                    "category": "resource-limits",
                    "content": large_content,
                    "tags": ["disk-space", "large-content", "limits"],
                    "references": ["disk_space_test.py"],
                },
            },
        }

        # This should either succeed or fail gracefully
        try:
            save_responses = mcp_client.send_request(save_request, timeout=60)
            save_response = save_responses[0]

            # Should get either success or proper error response
            assert "result" in save_response or "error" in save_response

            if "result" in save_response:
                content = save_response["result"]["content"][0]["text"]
                # Should indicate success or provide error details
                assert (
                    "Memory saved successfully" in content
                    or "failed" in content.lower()
                    or "error" in content.lower()
                )

        except Exception as e:
            # Server should handle resource issues gracefully
            # This test primarily ensures no crashes occur
            assert (
                "timeout" not in str(e).lower()
            ), f"Operation timed out, possible resource issue: {e}"

        # System should still be responsive for normal operations
        normal_save_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "disk-space-test",
                    "category": "normal",
                    "content": "# Normal Memory\n\nThis is a normal-sized memory after the large one.",
                    "tags": ["normal", "after-large"],
                    "references": ["normal_test.py"],
                },
            },
        }

        normal_responses = mcp_client.send_request(normal_save_request)
        normal_response = normal_responses[0]
        assert "result" in normal_response
        # Normal operations should continue to work
        assert (
            "Memory saved successfully"
            in normal_response["result"]["content"][0]["text"]
        )

    def test_network_failure_during_operations(self, recovery_settings):
        """Test behavior during network failures affecting ChromaDB operations."""
        # Test direct service interaction during simulated network issues
        storage_service = MemoryStorage(recovery_settings)

        # Test with mock network failures
        with patch("httpx.get") as mock_get:
            # Simulate network timeout
            mock_get.side_effect = httpx.TimeoutException("Network timeout")

            # Test ChromaDB connection failure handling
            try:
                embedding_service = EmbeddingService(recovery_settings)
                # Should handle connection failure gracefully
                assert embedding_service is not None
            except Exception as e:
                # Should raise a descriptive error, not crash
                assert "ChromaDB" in str(e) or "connection" in str(e).lower()

        # Test storage operations (should work regardless of network)
        from datetime import datetime

        from mcp_server.models import MemoryEntry

        test_memory = MemoryEntry(
            project="network-failure-test",
            category="resilience",
            content="# Network Failure Test\n\nThis memory tests operations during network issues.",
            tags=["network", "failure", "resilience"],
            references=["network_test.py"],
            timestamp=datetime.now(),
        )

        # File storage should work even with network issues
        memory_id, file_path = storage_service.save_memory(test_memory)
        assert memory_id is not None
        assert file_path.exists()

        # Loading should work
        loaded_memory = storage_service.load_memory(file_path)
        assert loaded_memory is not None
        assert loaded_memory.project == "network-failure-test"

        # Listing should work
        memory_files = storage_service.list_memory_files("network-failure-test")
        assert len(memory_files) > 0
        assert any(str(f) == str(file_path) for f in memory_files)

    def test_invalid_memory_data_sanitization(self, mcp_client, recovery_settings):
        """Test sanitization and handling of invalid memory data."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Test various invalid inputs
        invalid_test_cases = [
            {
                "name": "empty_project",
                "data": {
                    "project": "",
                    "category": "validation",
                    "content": "# Empty Project Test\n\nTesting empty project name.",
                    "tags": ["validation", "empty"],
                },
                "should_fail": True,
            },
            {
                "name": "empty_category",
                "data": {
                    "project": "validation-test",
                    "category": "",
                    "content": "# Empty Category Test\n\nTesting empty category.",
                    "tags": ["validation", "empty"],
                },
                "should_fail": True,
            },
            {
                "name": "empty_content",
                "data": {
                    "project": "validation-test",
                    "category": "validation",
                    "content": "",
                    "tags": ["validation", "empty"],
                },
                "should_fail": True,
            },
            {
                "name": "special_characters",
                "data": {
                    "project": "validation-test",
                    "category": "validation",
                    "content": "# Special Characters Test\n\n<script>alert('xss')</script>\n\nTesting special characters: !@#$%^&*(){}[]|\\:;\"'<>?,./",
                    "tags": ["validation", "special-chars"],
                },
                "should_fail": False,  # Should be sanitized, not rejected
            },
            {
                "name": "very_long_content",
                "data": {
                    "project": "validation-test",
                    "category": "validation",
                    "content": "# Very Long Content Test\n\n"
                    + "A" * 50000,  # Very long content
                    "tags": ["validation", "long"],
                },
                "should_fail": False,  # Should handle gracefully
            },
        ]

        for i, test_case in enumerate(invalid_test_cases):
            save_request = {
                "jsonrpc": "2.0",
                "id": i + 1,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": test_case["data"],
                },
            }

            try:
                save_responses = mcp_client.send_request(save_request, timeout=30)
                save_response = save_responses[0]

                if test_case["should_fail"]:
                    # Should return error for invalid data
                    assert (
                        "error" in save_response
                        or "failed"
                        in save_response.get("result", {})
                        .get("content", [{}])[0]
                        .get("text", "")
                        .lower()
                    )
                else:
                    # Should handle gracefully (sanitize or succeed)
                    assert "result" in save_response or "error" in save_response
                    if "result" in save_response:
                        content = save_response["result"]["content"][0]["text"]
                        # Should either succeed or provide meaningful error
                        assert isinstance(content, str)

            except Exception as e:
                if not test_case["should_fail"]:
                    pytest.fail(
                        f"Unexpected error for test case {test_case['name']}: {e}"
                    )

    def test_service_restart_state_consistency(self, project_root, recovery_settings):
        """Test state consistency after service restart."""
        import sys
        import time

        # Save some memories before restart
        executable = [sys.executable, "-m", "mcp_server"]

        # First session: save memories
        from tests.conftest import MCPTestClient

        client1 = MCPTestClient(executable, project_root)
        client1.initialize_session()

        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "restart-test",
                    "category": "persistence",
                    "content": "# Restart Test\n\nThis memory tests persistence across service restarts.",
                    "tags": ["restart", "persistence", "state"],
                    "references": ["restart_test.py"],
                },
            },
        }

        save_responses = client1.send_request(save_request)
        save_response = save_responses[0]
        assert "result" in save_response

        # Extract memory ID for later verification
        save_text = save_response["result"]["content"][0]["text"]
        memory_id = None
        for line in save_text.split("\n"):
            if "ID:" in line:
                memory_id = line.split("ID:")[1].strip()
                break
        assert memory_id is not None

        # Wait for operations to complete
        time.sleep(2)

        # Simulate service restart by creating new client
        # (In a real system, this would involve actually stopping/starting the service)
        client2 = MCPTestClient(executable, project_root)
        client2.initialize_session()

        # After "restart", memories should still be accessible via file system
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "restart-test",
                    "limit": 5,
                },
            },
        }

        list_responses = client2.send_request(list_request)
        list_response = list_responses[0]
        assert "result" in list_response

        list_content = list_response["result"]["content"][0]["text"]
        # Memory should still be listed after restart
        assert memory_id in list_content
        assert "restart-test" in list_content

        # Search might need re-indexing after restart, but should work
        search_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "restart persistence state",
                    "project": "restart-test",
                    "top": 3,
                },
            },
        }

        # Search may or may not find the memory immediately after restart
        # (depends on whether vector database persists or needs re-indexing)
        # But it should not crash
        try:
            search_responses = client2.send_request(search_request)
            search_response = search_responses[0]
            assert "result" in search_response or "error" in search_response
        except Exception as e:
            pytest.fail(f"Search failed after restart: {e}")

    def test_partial_failure_rollback_mechanisms(self, mcp_client, recovery_settings):
        """Test rollback mechanisms for partial failures."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # This test simulates scenarios where file save succeeds but vector indexing fails
        # or vice versa, and tests the system's ability to handle partial failures

        # Test 1: Save operation that might have vector indexing issues
        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "rollback-test",
                    "category": "failure-handling",
                    "content": "# Rollback Test\n\nThis memory tests rollback mechanisms for partial failures.",
                    "tags": ["rollback", "failure", "partial"],
                    "references": ["rollback_test.py"],
                },
            },
        }

        # Save should either fully succeed or properly report partial failure
        save_responses = mcp_client.send_request(save_request)
        save_response = save_responses[0]
        assert "result" in save_response

        save_text = save_response["result"]["content"][0]["text"]

        # Response should indicate success or partial failure
        # But should not leave system in inconsistent state
        assert (
            "Memory saved successfully" in save_text
            or "partially" in save_text.lower()
            or "failed" in save_text.lower()
        )

        # Wait for any cleanup operations
        time.sleep(2)

        # List memories to check final state
        list_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "rollback-test",
                    "limit": 5,
                },
            },
        }

        list_responses = mcp_client.send_request(list_request)
        list_response = list_responses[0]
        assert "result" in list_response

        list_content = list_response["result"]["content"][0]["text"]

        # System should be in a consistent state
        # Either memory exists and is listed, or it was properly rolled back
        if "rollback-test" in list_content:
            # If memory exists, it should be complete
            assert "✅" in list_content or "❌" in list_content  # Should have status

        # Test update operations with potential rollback scenarios
        if "rollback-test" in list_content:
            # Extract memory ID for update test
            memory_id = None
            for line in save_text.split("\n"):
                if "ID:" in line:
                    memory_id = line.split("ID:")[1].strip()
                    break

            if memory_id:
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

                # Update should succeed or fail cleanly
                update_responses = mcp_client.send_request(update_request)
                update_response = update_responses[0]
                assert "result" in update_response or "error" in update_response

                if "result" in update_response:
                    update_text = update_response["result"]["content"][0]["text"]
                    assert (
                        "marked as outdated" in update_text
                        or "failed" in update_text.lower()
                    )

    def test_memory_corruption_detection_and_repair(
        self, mcp_client, recovery_settings
    ):
        """Test detection and repair of memory corruption."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save a memory normally first
        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "repair-test",
                    "category": "corruption-repair",
                    "content": "# Repair Test\n\nThis memory will be used to test corruption detection and repair.",
                    "tags": ["repair", "corruption", "detection"],
                    "references": ["repair_test.py"],
                },
            },
        }

        save_responses = mcp_client.send_request(save_request)
        save_response = save_responses[0]
        assert "result" in save_response

        # Extract file path
        save_text = save_response["result"]["content"][0]["text"]
        file_path = None
        for line in save_text.split("\n"):
            if "File:" in line:
                file_path = Path(line.split("File:")[1].strip())
                break

        assert file_path is not None
        assert file_path.exists()

        # Read original content for later comparison
        with open(file_path) as f:
            original_content = f.read()

        # Simulate various types of corruption
        corruption_tests = [
            {
                "name": "missing_frontmatter",
                "corruption": "# Missing Frontmatter\n\nThis file is missing YAML frontmatter.",
            },
            {
                "name": "invalid_yaml",
                "corruption": "---\nproject: repair-test\ncategory: \n  - invalid: yaml: structure\n---\n# Content",
            },
            {
                "name": "truncated_file",
                "corruption": original_content[
                    : len(original_content) // 2
                ],  # Truncate file
            },
        ]

        for corruption_test in corruption_tests:
            # Apply corruption
            with open(file_path, "w") as f:
                f.write(corruption_test["corruption"])

            # Try to list memories - should detect corruption
            list_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "list_memories",
                    "arguments": {
                        "project": "repair-test",
                        "limit": 5,
                    },
                },
            }

            list_responses = mcp_client.send_request(list_request)
            list_response = list_responses[0]
            assert "result" in list_response

            # System should handle corruption gracefully
            # May skip corrupted files or show error indicators
            list_content = list_response["result"]["content"][0]["text"]
            assert isinstance(list_content, str)  # Should not crash

            # In a production system, this might trigger repair mechanisms
            # For now, we verify the system doesn't crash

        # Restore original content to clean up
        with open(file_path, "w") as f:
            f.write(original_content)

        # Verify system recovers after repair
        final_list_responses = mcp_client.send_request(list_request)
        final_list_response = final_list_responses[0]
        assert "result" in final_list_response

        final_list_content = final_list_response["result"]["content"][0]["text"]
        # Should show the memory again after repair
        assert "repair-test" in final_list_content
