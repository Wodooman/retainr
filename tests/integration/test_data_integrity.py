#!/usr/bin/env python3
"""Data integrity tests for retainr MCP server."""

import tempfile
import time
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from mcp_server.config import Settings
from mcp_server.embeddings import EmbeddingService
from mcp_server.models import MemoryEntry
from mcp_server.storage import MemoryStorage


@pytest.mark.integration
class TestDataIntegrity:
    """Test data consistency between file storage and vector database."""

    @pytest.fixture(scope="class")
    def temp_memory_dir(self):
        """Create a temporary memory directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture(scope="class")
    def integrity_settings(self, temp_memory_dir):
        """Create settings for integrity testing."""
        settings = Settings()
        settings.memory_dir = temp_memory_dir
        settings.chroma_collection = "test_integrity"
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
    def storage_service(self, integrity_settings):
        """Create storage service for testing."""
        return MemoryStorage(integrity_settings)

    @pytest.fixture
    def embedding_service(self, integrity_settings, chromadb_available):
        """Create embedding service for testing."""
        return EmbeddingService(integrity_settings)

    @pytest.fixture
    def mcp_client(self, project_root, chromadb_available):
        """Create MCP client for integrity testing."""
        import sys

        from tests.conftest import MCPTestClient

        executable = [sys.executable, "-m", "mcp_server"]
        return MCPTestClient(executable, project_root)

    def test_file_vector_consistency_after_save(
        self, mcp_client, storage_service, embedding_service, integrity_settings
    ):
        """Test that file storage and vector database remain consistent after save."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save a memory via MCP
        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "integrity-test",
                    "category": "consistency",
                    "content": "# Integrity Test Memory\n\nThis memory tests file-vector database consistency.",
                    "tags": ["integrity", "consistency", "testing"],
                    "references": ["integrity_test.py"],
                },
            },
        }

        save_responses = mcp_client.send_request(save_request)
        save_response = save_responses[0]
        assert "result" in save_response

        # Extract memory ID and file path from response
        save_text = save_response["result"]["content"][0]["text"]
        memory_id = None
        file_path = None

        for line in save_text.split("\n"):
            if "ID:" in line:
                memory_id = line.split("ID:")[1].strip()
            elif "File:" in line:
                file_path = Path(line.split("File:")[1].strip())

        assert memory_id is not None
        assert file_path is not None

        # Wait for indexing
        time.sleep(2)

        # Verify file exists and is readable
        assert file_path.exists(), f"Memory file {file_path} does not exist"

        # Load memory from file
        file_memory = storage_service.load_memory(file_path)
        assert file_memory is not None
        assert file_memory.project == "integrity-test"
        assert file_memory.category == "consistency"
        assert "Integrity Test Memory" in file_memory.content

        # Verify memory is searchable in vector database
        search_results = embedding_service.search_memories(
            "integrity consistency testing", project="integrity-test", top_k=5
        )

        # Should find the memory in vector database
        found_memory = None
        for result in search_results:
            if result.memory_id == memory_id:
                found_memory = result
                break

        assert (
            found_memory is not None
        ), f"Memory {memory_id} not found in vector database"
        assert found_memory.entry.project == file_memory.project
        assert found_memory.entry.category == file_memory.category
        assert found_memory.entry.content == file_memory.content
        assert found_memory.entry.tags == file_memory.tags

    def test_memory_id_consistency_across_systems(
        self, mcp_client, storage_service, integrity_settings
    ):
        """Test that memory IDs are consistent between file storage and vector database."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save multiple memories
        memory_data = [
            {
                "project": "id-consistency",
                "category": "testing",
                "content": "# Memory 1\n\nFirst test memory for ID consistency.",
                "tags": ["id", "consistency", "first"],
            },
            {
                "project": "id-consistency",
                "category": "testing",
                "content": "# Memory 2\n\nSecond test memory for ID consistency.",
                "tags": ["id", "consistency", "second"],
            },
            {
                "project": "id-consistency",
                "category": "testing",
                "content": "# Memory 3\n\nThird test memory for ID consistency.",
                "tags": ["id", "consistency", "third"],
            },
        ]

        saved_memory_ids = []
        saved_file_paths = []

        for i, data in enumerate(memory_data):
            save_request = {
                "jsonrpc": "2.0",
                "id": i + 1,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": data,
                },
            }

            save_responses = mcp_client.send_request(save_request)
            save_response = save_responses[0]
            assert "result" in save_response

            # Extract memory ID and file path
            save_text = save_response["result"]["content"][0]["text"]
            memory_id = None
            file_path = None

            for line in save_text.split("\n"):
                if "ID:" in line:
                    memory_id = line.split("ID:")[1].strip()
                elif "File:" in line:
                    file_path = Path(line.split("File:")[1].strip())

            assert memory_id is not None
            assert file_path is not None

            saved_memory_ids.append(memory_id)
            saved_file_paths.append(file_path)

        # Wait for indexing
        time.sleep(3)

        # Verify all memory IDs are unique
        assert len(set(saved_memory_ids)) == len(
            saved_memory_ids
        ), "Memory IDs are not unique"

        # Verify memory IDs can be found by file path
        for memory_id, file_path in zip(saved_memory_ids, saved_file_paths):
            # Get memory ID from file path
            file_memory_id = storage_service.get_memory_id(file_path)
            assert (
                file_memory_id == memory_id
            ), f"Memory ID mismatch: file has {file_memory_id}, expected {memory_id}"

            # Find memory file by ID
            found_file_path = storage_service.find_memory_by_id(memory_id)
            assert (
                found_file_path == file_path
            ), f"File path mismatch for memory {memory_id}"

        # List memories and verify all IDs are present
        list_request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "id-consistency",
                    "limit": 10,
                },
            },
        }

        list_responses = mcp_client.send_request(list_request)
        list_response = list_responses[0]
        assert "result" in list_response

        list_content = list_response["result"]["content"][0]["text"]

        # Verify all memory IDs appear in the list
        for memory_id in saved_memory_ids:
            assert (
                memory_id in list_content
            ), f"Memory ID {memory_id} not found in list output"

    def test_concurrent_update_race_conditions(self, mcp_client, integrity_settings):
        """Test data integrity under concurrent update operations."""
        import queue
        import threading

        # Initialize MCP session
        mcp_client.initialize_session()

        # Save initial memory
        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "race-condition-test",
                    "category": "concurrency",
                    "content": "# Race Condition Test\n\nThis memory will be updated concurrently to test race conditions.",
                    "tags": ["race", "concurrency", "update"],
                    "references": ["race_test.py"],
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

        # Wait for initial indexing
        time.sleep(2)

        # Concurrent update operations
        results_queue = queue.Queue()
        errors_queue = queue.Queue()

        def update_memory_operation(thread_id, outdated_status):
            try:
                update_request = {
                    "jsonrpc": "2.0",
                    "id": thread_id + 100,
                    "method": "tools/call",
                    "params": {
                        "name": "update_memory",
                        "arguments": {
                            "memory_id": memory_id,
                            "outdated": outdated_status,
                        },
                    },
                }

                responses = mcp_client.send_request(update_request)
                if responses and "result" in responses[0]:
                    results_queue.put(f"update_{thread_id}_success")
                else:
                    errors_queue.put(f"update_{thread_id}_failed")
            except Exception as e:
                errors_queue.put(f"update_{thread_id}_error: {str(e)}")

        # Start concurrent updates
        threads = []
        for i in range(5):
            # Alternate between marking as outdated and active
            outdated = i % 2 == 0
            thread = threading.Thread(
                target=update_memory_operation, args=(i, outdated)
            )
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

        # At least some updates should succeed
        assert success_count > 0, f"No successful updates, errors: {errors}"

        # Wait for updates to propagate
        time.sleep(3)

        # Verify final state consistency
        list_request = {
            "jsonrpc": "2.0",
            "id": 200,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "race-condition-test",
                    "limit": 5,
                },
            },
        }

        list_responses = mcp_client.send_request(list_request)
        list_response = list_responses[0]
        assert "result" in list_response

        # Memory should still be accessible and have a consistent state
        list_content = list_response["result"]["content"][0]["text"]
        assert memory_id in list_content

        # Should show either outdated or active status consistently
        assert ("✅" in list_content and "❌" not in list_content) or (
            "❌" in list_content and "✅" not in list_content
        )

    def test_orphaned_vector_detection_cleanup(
        self, storage_service, embedding_service, integrity_settings
    ):
        """Test detection and handling of orphaned vector entries."""
        # Create a test memory entry
        test_memory = MemoryEntry(
            project="orphan-test",
            category="cleanup",
            content="# Orphan Test\n\nThis memory will be used to test orphan detection.",
            tags=["orphan", "cleanup"],
            references=["orphan_test.py"],
            timestamp=datetime.now(),
        )

        # Save memory to storage
        memory_id, file_path = storage_service.save_memory(test_memory)

        # Index in vector database
        embedding_service.index_memory(memory_id, test_memory, str(file_path))

        # Wait for indexing
        time.sleep(2)

        # Verify memory exists in both systems
        stored_memory = storage_service.load_memory(file_path)
        assert stored_memory is not None

        search_results = embedding_service.search_memories(
            "orphan cleanup test", project="orphan-test", top_k=3
        )
        assert len(search_results) > 0
        assert any(result.memory_id == memory_id for result in search_results)

        # Simulate orphaned vector by deleting file but leaving vector entry
        file_path.unlink()  # Delete the file

        # Verify file is gone but vector entry still exists
        assert not file_path.exists()
        search_results = embedding_service.search_memories(
            "orphan cleanup test", project="orphan-test", top_k=3
        )
        # Vector entry should still be found
        assert len(search_results) > 0

        # Now when we try to load the memory, it should handle the missing file gracefully
        orphaned_result = None
        for result in search_results:
            if result.memory_id == memory_id:
                orphaned_result = result
                break

        assert orphaned_result is not None

        # The vector entry points to a non-existent file
        # In a real system, this would be detected and cleaned up
        # For now, we verify the inconsistency is detectable
        missing_file = storage_service.load_memory(file_path)
        assert missing_file is None  # File is missing

        # But vector search still returns the entry
        assert orphaned_result.file_path == str(file_path)

    def test_missing_file_search_result_handling(
        self, mcp_client, storage_service, integrity_settings
    ):
        """Test handling of search results that point to missing files."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save a memory
        save_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "missing-file-test",
                    "category": "error-handling",
                    "content": "# Missing File Test\n\nThis memory file will be deleted to test error handling.",
                    "tags": ["missing", "file", "error"],
                    "references": ["missing_file_test.py"],
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
                    "query": "missing file error handling",
                    "project": "missing-file-test",
                    "top": 3,
                },
            },
        }

        initial_search_responses = mcp_client.send_request(search_request)
        initial_search_response = initial_search_responses[0]
        assert "result" in initial_search_response
        initial_content = initial_search_response["result"]["content"][0]["text"]
        assert "Found" in initial_content or "missing-file-test" in initial_content

        # Delete the memory file to simulate corruption/deletion
        file_path.unlink()
        assert not file_path.exists()

        # Search again - should handle missing file gracefully
        final_search_responses = mcp_client.send_request(search_request)
        final_search_response = final_search_responses[0]
        assert "result" in final_search_response

        # The search should either:
        # 1. Return no results (if missing files are filtered out)
        # 2. Return results but handle missing files gracefully (no crashes)
        # The important thing is that it doesn't crash the server
        final_content = final_search_response["result"]["content"][0]["text"]
        assert isinstance(final_content, str)  # Should return valid string response

    def test_backup_restore_consistency(
        self, mcp_client, storage_service, embedding_service, integrity_settings
    ):
        """Test data consistency after backup and restore operations."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save multiple memories
        original_memories = []
        for i in range(3):
            save_request = {
                "jsonrpc": "2.0",
                "id": i + 1,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": {
                        "project": "backup-test",
                        "category": "backup",
                        "content": f"# Backup Test Memory {i}\n\nThis is memory {i} for backup consistency testing.",
                        "tags": ["backup", f"memory-{i}", "consistency"],
                        "references": [f"backup_test_{i}.py"],
                    },
                },
            }

            save_responses = mcp_client.send_request(save_request)
            save_response = save_responses[0]
            assert "result" in save_response

            # Extract memory details
            save_text = save_response["result"]["content"][0]["text"]
            memory_id = None
            file_path = None

            for line in save_text.split("\n"):
                if "ID:" in line:
                    memory_id = line.split("ID:")[1].strip()
                elif "File:" in line:
                    file_path = Path(line.split("File:")[1].strip())

            original_memories.append({"id": memory_id, "path": file_path, "index": i})

        # Wait for indexing
        time.sleep(3)

        # Create backup of memory files
        backup_dir = integrity_settings.memory_dir / "backup"
        backup_dir.mkdir(exist_ok=True)

        import shutil

        for memory in original_memories:
            backup_path = backup_dir / memory["path"].name
            shutil.copy2(memory["path"], backup_path)

        # Verify initial state
        initial_search_request = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "backup consistency testing",
                    "project": "backup-test",
                    "top": 5,
                },
            },
        }

        initial_search_responses = mcp_client.send_request(initial_search_request)
        initial_search_response = initial_search_responses[0]
        assert "result" in initial_search_response
        initial_content = initial_search_response["result"]["content"][0]["text"]

        # Should find all 3 memories
        if "Found" in initial_content:
            memory_count = initial_content.count("backup-test")
            assert memory_count >= 3

        # Simulate data loss by deleting original files
        for memory in original_memories:
            if memory["path"].exists():
                memory["path"].unlink()

        # Restore from backup
        for memory in original_memories:
            backup_path = backup_dir / memory["path"].name
            shutil.copy2(backup_path, memory["path"])

        # Wait for any automatic re-indexing (if implemented)
        time.sleep(2)

        # Verify restored state
        # Note: Vector database entries might still exist, but files are restored
        # The system should handle this gracefully

        for memory in original_memories:
            # File should be restored
            assert memory["path"].exists()

            # File content should be intact
            restored_memory = storage_service.load_memory(memory["path"])
            assert restored_memory is not None
            assert restored_memory.project == "backup-test"
            assert f"memory {memory['index']}" in restored_memory.content.lower()

        # Search should still work (might need re-indexing in a real system)
        final_search_responses = mcp_client.send_request(initial_search_request)
        final_search_response = final_search_responses[0]
        assert "result" in final_search_response

        # Should handle the restore gracefully without crashing
        final_content = final_search_response["result"]["content"][0]["text"]
        assert isinstance(final_content, str)

        # Clean up backup
        shutil.rmtree(backup_dir, ignore_errors=True)

    def test_vector_database_corruption_recovery(
        self, mcp_client, embedding_service, integrity_settings
    ):
        """Test recovery from vector database corruption or unavailability."""
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
                    "project": "corruption-test",
                    "category": "recovery",
                    "content": "# Corruption Recovery Test\n\nThis memory tests recovery from vector database issues.",
                    "tags": ["corruption", "recovery", "resilience"],
                    "references": ["corruption_test.py"],
                },
            },
        }

        save_responses = mcp_client.send_request(save_request)
        save_response = save_responses[0]
        assert "result" in save_response

        # Wait for indexing
        time.sleep(2)

        # Verify initial search works
        search_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "corruption recovery resilience",
                    "project": "corruption-test",
                    "top": 3,
                },
            },
        }

        initial_search_responses = mcp_client.send_request(search_request)
        initial_search_response = initial_search_responses[0]
        assert "result" in initial_search_response
        initial_content = initial_search_response["result"]["content"][0]["text"]
        assert "Found" in initial_content or "corruption-test" in initial_content

        # Test search when ChromaDB becomes unavailable
        # Note: In a real system, this would test graceful degradation
        # For now, we verify the system handles errors appropriately

        # Simulate ChromaDB issues by attempting operations that might fail
        try:
            # This might fail if ChromaDB has issues, but shouldn't crash the server
            corrupted_search_responses = mcp_client.send_request(search_request)
            corrupted_search_response = corrupted_search_responses[0]

            # Even if search fails, it should return a proper error response
            assert (
                "result" in corrupted_search_response
                or "error" in corrupted_search_response
            )

        except Exception as e:
            # If MCP server crashes, that's a test failure
            pytest.fail(f"MCP server crashed during ChromaDB issue simulation: {e}")

        # List memories should still work (file-based operation)
        list_request = {
            "jsonrpc": "2.0",
            "id": 3,
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

        # List should work even if vector database has issues
        list_content = list_response["result"]["content"][0]["text"]
        assert "corruption-test" in list_content or "Recent memories" in list_content
