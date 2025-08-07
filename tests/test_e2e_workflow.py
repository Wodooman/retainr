#!/usr/bin/env python3
"""
End-to-End Workflow Tests for retainr

Tests complete workflows from memory creation to retrieval across
different interfaces (MCP, REST API, CLI) to ensure system coherence.
"""

import json
import subprocess
import time
from pathlib import Path

import httpx
import pytest


class TestEndToEndWorkflow:
    """Test complete workflows across all interfaces."""

    @pytest.fixture(scope="class")
    def project_root(self):
        """Get project root directory."""
        return Path(__file__).parent.parent

    @pytest.fixture(scope="class")
    def ensure_services_running(self, project_root):
        """Check that native services are running (ChromaDB)."""
        import httpx

        try:
            # Check ChromaDB is running
            response = httpx.get("http://localhost:8000/api/v2/heartbeat", timeout=5)
            if response.status_code != 200:
                pytest.skip("ChromaDB not running. Run 'make start-chromadb' first.")
        except (httpx.RequestError, httpx.TimeoutException):
            pytest.skip("ChromaDB not running. Run 'make start-chromadb' first.")

        return True

    def test_memory_lifecycle_via_mcp(self, project_root, ensure_services_running):
        """Test complete memory lifecycle via MCP interface."""
        import sys

        # Use native MCP server command
        mcp_command = [sys.executable, "-m", "mcp_server"]

        # 1. Initialize MCP session
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "e2e-test", "version": "1.0"},
                "capabilities": {},
            },
        }

        # 2. Save a memory
        save_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "e2e-mcp-test",
                    "category": "workflow",
                    "content": "# E2E Test Memory\n\nThis memory tests the complete workflow via MCP.\n\n## Features\n- Memory persistence\n- Semantic search\n- Cross-session retrieval",
                    "tags": ["e2e", "mcp", "workflow", "testing"],
                    "references": ["test_e2e_workflow.py"],
                },
            },
        }

        # 3. Search for the memory
        search_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_memories",
                "arguments": {
                    "query": "E2E workflow semantic search",
                    "project": "e2e-mcp-test",
                    "top": 3,
                },
            },
        }

        # 4. List memories for the project
        list_request = {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}}

        # Add initialization notification after init request
        init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        input_data = (
            "\n".join(
                [
                    json.dumps(init_request),
                    json.dumps(init_notification),
                    json.dumps(save_request),
                    json.dumps(search_request),
                    json.dumps(list_request),
                ]
            )
            + "\n"
        )

        result = subprocess.run(
            mcp_command,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=project_root,
        )

        assert result.returncode == 0, f"MCP workflow failed: {result.stderr}"

        # Parse responses
        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 4, f"Expected 4 responses, got {len(lines)}"

        # Check initialization
        init_response = json.loads(lines[0])
        assert "result" in init_response
        assert init_response["result"]["serverInfo"]["name"] == "retainr"

        # Check save response
        save_response = json.loads(lines[1])
        assert "result" in save_response
        save_content = save_response["result"]["content"][0]["text"]
        assert "Memory saved successfully" in save_content

        # Check search response
        search_response = json.loads(lines[2])
        assert "result" in search_response
        search_content = search_response["result"]["content"][0]["text"]
        assert ("Found" in search_content) or ("No memories found" in search_content)

        # Check tools list
        tools_response = json.loads(lines[3])
        assert "result" in tools_response
        tools = tools_response["result"]["tools"]
        tool_names = {tool["name"] for tool in tools}
        expected_tools = {
            "save_memory",
            "search_memories",
            "list_memories",
            "update_memory",
        }
        assert expected_tools.issubset(tool_names)

    def test_cross_interface_consistency(self, project_root, ensure_services_running):
        """Test that memories are consistent across MCP interface (REST API removed for simplicity)."""
        pytest.skip(
            "Cross-interface test skipped - REST API removed for architecture simplification"
        )

        # Test data
        test_memory = {
            "project": "cross-interface-test",
            "category": "consistency",
            "content": "# Cross-Interface Test\n\nThis memory tests consistency across different interfaces.",
            "tags": ["cross-interface", "consistency", "testing"],
        }

        # 1. Save memory via REST API
        try:
            response = httpx.post(
                "http://localhost:8000/memory/", json=test_memory, timeout=10
            )
            assert response.status_code == 201
            rest_data = response.json()
            rest_data["id"]
            assert "Memory saved successfully" in rest_data["message"]
        except Exception as e:
            pytest.skip(f"REST API not accessible: {e}")

        time.sleep(2)  # Wait for indexing

        # 2. Search via MCP (wrapper script removed in cleanup)
        # This section is disabled since wrapper script was removed
        if False:  # wrapper_script.exists():
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "cross-test", "version": "1.0"},
                    "capabilities": {},
                },
            }

            search_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "search_memories",
                    "arguments": {
                        "query": "cross-interface consistency",
                        "project": "cross-interface-test",
                    },
                },
            }

            # Add initialization notification
            init_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }

            input_data = (
                json.dumps(init_request)
                + "\n"
                + json.dumps(init_notification)
                + "\n"
                + json.dumps(search_request)
                + "\n"
            )

            result = subprocess.run(
                ["echo", "disabled"],  # [str(wrapper_script)],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=60,  # Longer timeout for model download
                cwd=project_root,
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    search_response = json.loads(lines[1])
                    if "result" in search_response:
                        search_content = search_response["result"]["content"][0]["text"]
                        # Should find the memory saved via REST API
                        assert (
                            "Found" in search_content
                            and "cross-interface-test" in search_content
                        ) or "No memories found" in search_content

        # 3. Verify via CLI (if available)
        cli_main = project_root / "cli" / "main.py"
        if cli_main.exists():
            result = subprocess.run(
                [
                    "python",
                    "-m",
                    "cli.main",
                    "list",
                    "--project",
                    "cross-interface-test",
                ],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=15,
            )

            # CLI should show the memory (or handle gracefully)
            assert result.returncode == 0 or "not found" in result.stderr.lower()

        # 4. Verify via REST API search
        try:
            response = httpx.get(
                "http://localhost:8000/memory/search",
                params={"query": "cross-interface", "project": "cross-interface-test"},
                timeout=10,
            )
            assert response.status_code == 200
            search_results = response.json()

            # Should find the memory
            if search_results["results"]:
                found_memory = search_results["results"][0]
                assert found_memory["project"] == "cross-interface-test"
                assert found_memory["category"] == "consistency"
        except Exception as e:
            pytest.skip(f"REST API search failed: {e}")

    def test_large_memory_handling(self, project_root, ensure_services_running):
        """Test handling of large memories."""
        import sys

        # Use native MCP server command
        mcp_command = [sys.executable, "-m", "mcp_server"]

        # Create a large memory content
        large_content = (
            "# Large Memory Test\n\n" + "This is a large memory content. " * 1000
        )

        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "large-test", "version": "1.0"},
                "capabilities": {},
            },
        }

        save_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "large-memory-test",
                    "category": "performance",
                    "content": large_content,
                    "tags": ["large", "performance", "test"],
                },
            },
        }

        # Add initialization notification
        init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        input_data = (
            json.dumps(init_request)
            + "\n"
            + json.dumps(init_notification)
            + "\n"
            + json.dumps(save_request)
            + "\n"
        )

        result = subprocess.run(
            mcp_command,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=60,  # Longer timeout for large content
            cwd=project_root,
        )

        assert result.returncode == 0, f"Large memory handling failed: {result.stderr}"

        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 2

        save_response = json.loads(lines[1])
        assert "result" in save_response
        save_content = save_response["result"]["content"][0]["text"]
        assert "Memory saved successfully" in save_content

    def test_special_characters_and_unicode(
        self, project_root, ensure_services_running
    ):
        """Test handling of special characters and Unicode content."""
        import sys

        # Use native MCP server command
        mcp_command = [sys.executable, "-m", "mcp_server"]

        # Content with special characters and Unicode
        special_content = """# Unicode Test Memory 🧠

## Special Characters
- Quotes: "Hello" 'World'
- Symbols: @#$%^&*()
- Unicode: 你好 🚀 🎉 ñáéíóú
- Code: `print("Hello, 世界!")`

## JSON Special Characters
- Backslash: \\
- Newlines and tabs
- Brackets: {}[]
"""

        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "unicode-test", "version": "1.0"},
                "capabilities": {},
            },
        }

        save_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "save_memory",
                "arguments": {
                    "project": "unicode-test",
                    "category": "encoding",
                    "content": special_content,
                    "tags": ["unicode", "special-chars", "encoding"],
                },
            },
        }

        # Add initialization notification
        init_notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        input_data = (
            json.dumps(init_request, ensure_ascii=False)
            + "\n"
            + json.dumps(init_notification, ensure_ascii=False)
            + "\n"
            + json.dumps(save_request, ensure_ascii=False)
            + "\n"
        )

        result = subprocess.run(
            mcp_command,
            input=input_data.encode("utf-8"),
            capture_output=True,
            timeout=90,  # Longer timeout for model download
            cwd=project_root,
        )

        assert (
            result.returncode == 0
        ), f"Unicode handling failed: {result.stderr.decode('utf-8', errors='replace')}"

        lines = result.stdout.decode("utf-8", errors="replace").strip().split("\n")
        assert len(lines) >= 2

        save_response = json.loads(lines[1])
        assert "result" in save_response
        save_content = save_response["result"]["content"][0]["text"]
        assert "Memory saved successfully" in save_content

    def test_error_recovery_workflow(self, project_root, ensure_services_running):
        """Test system behavior during error conditions."""
        import sys

        # Use native MCP server command
        mcp_command = [sys.executable, "-m", "mcp_server"]

        # Test sequence with intentional errors
        requests = [
            # Valid initialization
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "error-test", "version": "1.0"},
                    "capabilities": {},
                },
            },
            # Initialization notification
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            # Invalid tool call
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "nonexistent_tool", "arguments": {}},
            },
            # Valid tool call after error
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "save_memory",
                    "arguments": {
                        "project": "error-recovery-test",
                        "category": "resilience",
                        "content": "Memory saved after error recovery",
                        "tags": ["error-recovery", "resilience"],
                    },
                },
            },
        ]

        input_data = "\n".join(json.dumps(req) for req in requests) + "\n"

        result = subprocess.run(
            mcp_command,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=90,  # Longer timeout for model download
            cwd=project_root,
        )

        assert result.returncode == 0, f"Error recovery test failed: {result.stderr}"

        lines = result.stdout.strip().split("\n")
        assert len(lines) >= 3

        # Check that system recovered and processed valid request after error
        init_response = json.loads(lines[0])
        assert "result" in init_response

        error_response = json.loads(lines[1])
        # Should be either a JSON-RPC error or a result with error content
        if "error" not in error_response:
            assert "result" in error_response
            assert error_response["result"]["isError"]

        recovery_response = json.loads(lines[2])
        assert "result" in recovery_response  # Should work after error
        save_content = recovery_response["result"]["content"][0]["text"]
        assert "Memory saved successfully" in save_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
