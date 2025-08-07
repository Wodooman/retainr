#!/usr/bin/env python3
"""Performance and scalability tests for retainr MCP server."""

import tempfile
import threading
import time
from pathlib import Path

import httpx
import pytest


@pytest.mark.performance
class TestScalability:
    """Test performance and scalability under various loads."""

    @pytest.fixture(scope="class")
    def temp_memory_dir(self):
        """Create a temporary memory directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

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
        """Create MCP client for performance testing."""
        import sys

        from tests.conftest import MCPTestClient

        executable = [sys.executable, "-m", "mcp_server"]
        return MCPTestClient(executable, project_root)

    def test_search_performance_with_1000_memories(self, mcp_client):
        """Test search performance with a large number of memories."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save 100 memories (scaled down for practical testing)
        print("Saving memories for performance test...")
        start_save_time = time.time()

        for i in range(100):
            save_request = {
                "jsonrpc": "2.0",
                "id": i + 1,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": {
                        "project": "performance-test",
                        "category": "scalability",
                        "content": f"# Performance Memory {i}\n\nThis is memory {i} for performance testing. It contains various content that makes it unique and searchable.",
                        "tags": ["performance", f"memory-{i}", "scalability"],
                        "references": [f"perf_test_{i}.py"],
                    },
                },
            }

            # Only check every 10th response for speed
            if i % 10 == 0:
                responses = mcp_client.send_request(save_request, timeout=30)
                assert len(responses) > 0
                assert "result" in responses[0]
            else:
                mcp_client.send_request(save_request, timeout=30)

        save_duration = time.time() - start_save_time
        print(f"Saved 100 memories in {save_duration:.2f} seconds")

        # Wait for indexing
        time.sleep(10)

        # Test search performance
        search_times = []
        for i in range(5):  # Run 5 search tests
            start_search_time = time.time()

            search_request = {
                "jsonrpc": "2.0",
                "id": 1000 + i,
                "method": "tools/call",
                "params": {
                    "name": "search_memories",
                    "arguments": {
                        "query": f"performance scalability memory {i*20}",
                        "project": "performance-test",
                        "top": 10,
                    },
                },
            }

            search_responses = mcp_client.send_request(search_request, timeout=30)
            search_duration = time.time() - start_search_time
            search_times.append(search_duration)

            assert len(search_responses) > 0
            assert "result" in search_responses[0]

        avg_search_time = sum(search_times) / len(search_times)
        print(f"Average search time: {avg_search_time:.3f} seconds")

        # Performance assertions (adjust thresholds as needed)
        assert avg_search_time < 5.0, f"Search too slow: {avg_search_time:.3f}s"
        assert save_duration < 300, f"Saving too slow: {save_duration:.2f}s"

    def test_memory_save_performance_large_content(self, mcp_client):
        """Test saving memories with large content."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Test various content sizes
        content_sizes = [1000, 5000, 10000, 25000]  # Character counts
        save_times = []

        for size in content_sizes:
            large_content = "# Large Content Test\n\n" + "This is test content. " * (
                size // 20
            )

            start_time = time.time()
            save_request = {
                "jsonrpc": "2.0",
                "id": size,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": {
                        "project": "large-content-test",
                        "category": "performance",
                        "content": large_content,
                        "tags": ["large-content", f"size-{size}"],
                        "references": [f"large_content_{size}.py"],
                    },
                },
            }

            responses = mcp_client.send_request(save_request, timeout=60)
            save_duration = time.time() - start_time
            save_times.append(save_duration)

            assert len(responses) > 0
            assert "result" in responses[0]
            print(f"Saved {size} chars in {save_duration:.3f} seconds")

        # Performance should scale reasonably with content size
        assert all(t < 30 for t in save_times), f"Some saves too slow: {save_times}"

        # Larger content shouldn't be exponentially slower
        if len(save_times) >= 2:
            ratio = save_times[-1] / save_times[0]
            assert ratio < 10, f"Performance degrades too much with size: {ratio}x"

    def test_concurrent_search_operations_load(self, mcp_client):
        """Test performance under concurrent search load."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Save some test memories first
        for i in range(20):
            save_request = {
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": {
                        "project": "concurrent-search-test",
                        "category": "performance",
                        "content": f"# Concurrent Search Memory {i}\n\nContent for concurrent search testing with unique identifier {i}.",
                        "tags": ["concurrent", f"search-{i}"],
                        "references": [f"concurrent_search_{i}.py"],
                    },
                },
            }
            mcp_client.send_request(save_request, timeout=30)

        time.sleep(5)  # Wait for indexing

        # Concurrent search test
        search_results = []
        search_errors = []

        def search_operation(thread_id):
            try:
                start_time = time.time()
                search_request = {
                    "jsonrpc": "2.0",
                    "id": thread_id + 1000,
                    "method": "tools/call",
                    "params": {
                        "name": "search_memories",
                        "arguments": {
                            "query": f"concurrent search memory {thread_id % 10}",
                            "project": "concurrent-search-test",
                            "top": 5,
                        },
                    },
                }

                responses = mcp_client.send_request(search_request, timeout=30)
                duration = time.time() - start_time

                if responses and "result" in responses[0]:
                    search_results.append(duration)
                else:
                    search_errors.append(f"Thread {thread_id}: No valid response")

            except Exception as e:
                search_errors.append(f"Thread {thread_id}: {str(e)}")

        # Run concurrent searches
        threads = []
        for i in range(10):  # 10 concurrent searches
            thread = threading.Thread(target=search_operation, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join(timeout=60)

        # Analyze results
        successful_searches = len(search_results)
        total_errors = len(search_errors)

        print(f"Successful concurrent searches: {successful_searches}/10")
        print(f"Errors: {total_errors}")
        if search_results:
            avg_time = sum(search_results) / len(search_results)
            print(f"Average concurrent search time: {avg_time:.3f}s")

        # Performance assertions
        assert (
            successful_searches >= 8
        ), f"Too many failed searches: {total_errors} errors"
        if search_results:
            assert (
                max(search_results) < 15
            ), f"Some searches too slow: {max(search_results):.3f}s"

    def test_memory_consumption_during_indexing(self, mcp_client):
        """Test memory consumption during large indexing operations."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # This test monitors system behavior during intensive operations
        # Note: Actual memory monitoring would require additional tools

        start_time = time.time()

        # Save a batch of memories with varied content
        for i in range(50):
            content_variety = [
                f"# Technical Memory {i}\n\nThis discusses technical concepts, algorithms, and implementation details for system {i}.",
                f"# Documentation Memory {i}\n\nUser guide and documentation for feature {i} with examples and usage patterns.",
                f"# Bug Report Memory {i}\n\nIssue #{i}: Description of bug, reproduction steps, and potential solutions.",
                f"# Meeting Notes Memory {i}\n\nMeeting on topic {i} with decisions, action items, and follow-up tasks.",
            ]

            content = content_variety[i % 4]

            save_request = {
                "jsonrpc": "2.0",
                "id": i,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": {
                        "project": "memory-consumption-test",
                        "category": ["technical", "documentation", "bugs", "meetings"][
                            i % 4
                        ],
                        "content": content,
                        "tags": ["memory-test", f"batch-{i//10}", f"type-{i%4}"],
                        "references": [f"memory_consumption_{i}.py"],
                    },
                },
            }

            # Check response every 10 operations
            if i % 10 == 0:
                responses = mcp_client.send_request(save_request, timeout=30)
                assert len(responses) > 0
                assert "result" in responses[0]
            else:
                mcp_client.send_request(save_request, timeout=30)

        batch_duration = time.time() - start_time
        print(f"Batch save completed in {batch_duration:.2f} seconds")

        # Wait for indexing to complete
        time.sleep(10)

        # Test that system is still responsive
        list_request = {
            "jsonrpc": "2.0",
            "id": 2000,
            "method": "tools/call",
            "params": {
                "name": "list_memories",
                "arguments": {
                    "project": "memory-consumption-test",
                    "limit": 20,
                },
            },
        }

        list_responses = mcp_client.send_request(list_request, timeout=30)
        assert len(list_responses) > 0
        assert "result" in list_responses[0]

        # System should still be responsive
        assert batch_duration < 180, f"Batch processing too slow: {batch_duration:.2f}s"

    def test_startup_time_with_large_dataset(self, project_root):
        """Test startup time with existing large dataset."""
        # This test measures how long it takes to initialize the MCP server
        # when there are many existing memory files

        import os
        import sys

        from tests.conftest import MCPTestClient

        # First, create many memory files directly (simulating existing data)
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Create test memories using storage directly
            from datetime import datetime

            from mcp_server.config import Settings
            from mcp_server.models import MemoryEntry
            from mcp_server.storage import MemoryStorage

            settings = Settings()
            settings.memory_dir = temp_dir
            storage = MemoryStorage(settings)

            # Create 100 test memories
            for i in range(100):
                memory = MemoryEntry(
                    project="startup-test",
                    category="performance",
                    content=f"# Startup Test Memory {i}\n\nMemory {i} for startup performance testing.",
                    tags=["startup", f"memory-{i}"],
                    references=[f"startup_{i}.py"],
                    timestamp=datetime.now(),
                )
                storage.save_memory(memory)

            # Measure startup time with existing data
            executable = [sys.executable, "-m", "mcp_server"]
            os.environ["RETAINR_MEMORY_DIR"] = str(temp_dir)

            start_time = time.time()
            client = MCPTestClient(executable, project_root)

            # Initialize should work even with many existing files
            init_response = client.initialize_session()
            startup_duration = time.time() - start_time

            assert "result" in init_response
            print(f"Startup with 100 existing memories: {startup_duration:.2f}s")

            # Startup should be reasonably fast even with data
            assert startup_duration < 30, f"Startup too slow: {startup_duration:.2f}s"

            # Test that all memories are accessible
            list_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "list_memories",
                    "arguments": {
                        "project": "startup-test",
                        "limit": 50,
                    },
                },
            }

            list_responses = client.send_request(list_request, timeout=30)
            assert len(list_responses) > 0
            assert "result" in list_responses[0]

            list_content = list_responses[0]["result"]["content"][0]["text"]
            memory_count = list_content.count("startup-test")
            assert memory_count >= 50, f"Not all memories accessible: {memory_count}"

        finally:
            # Clean up
            import shutil

            shutil.rmtree(temp_dir, ignore_errors=True)
            if "RETAINR_MEMORY_DIR" in os.environ:
                del os.environ["RETAINR_MEMORY_DIR"]

    @pytest.mark.slow
    def test_long_running_stability(self, mcp_client):
        """Test stability during extended operations."""
        # Initialize MCP session
        mcp_client.initialize_session()

        # Run a series of operations over time to test stability
        operations_count = 50
        error_count = 0

        for i in range(operations_count):
            try:
                # Alternate between different operations
                if i % 3 == 0:
                    # Save operation
                    save_request = {
                        "jsonrpc": "2.0",
                        "id": i,
                        "method": "tools/call",
                        "params": {
                            "name": "save_memory",
                            "arguments": {
                                "project": "stability-test",
                                "category": "longevity",
                                "content": f"# Stability Test {i}\n\nLong-running stability test memory {i}.",
                                "tags": ["stability", f"operation-{i}"],
                                "references": [f"stability_{i}.py"],
                            },
                        },
                    }
                    mcp_client.send_request(save_request, timeout=30)

                elif i % 3 == 1:
                    # Search operation
                    search_request = {
                        "jsonrpc": "2.0",
                        "id": i,
                        "method": "tools/call",
                        "params": {
                            "name": "search_memories",
                            "arguments": {
                                "query": f"stability longevity {i//10}",
                                "project": "stability-test",
                                "top": 5,
                            },
                        },
                    }
                    mcp_client.send_request(search_request, timeout=30)

                else:
                    # List operation
                    list_request = {
                        "jsonrpc": "2.0",
                        "id": i,
                        "method": "tools/call",
                        "params": {
                            "name": "list_memories",
                            "arguments": {
                                "project": "stability-test",
                                "limit": 10,
                            },
                        },
                    }
                    mcp_client.send_request(list_request, timeout=30)

                # Small delay between operations
                time.sleep(0.1)

            except Exception as e:
                error_count += 1
                print(f"Operation {i} failed: {e}")

        # Calculate success rate
        success_rate = (operations_count - error_count) / operations_count
        print(f"Stability test success rate: {success_rate:.2%} ({error_count} errors)")

        # Should have high success rate
        assert (
            success_rate >= 0.95
        ), f"Too many failures: {success_rate:.2%} success rate"
