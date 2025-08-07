"""Standard MCP (Model Context Protocol) server implementation for retainr.

This module implements a standards-compliant MCP server using the official MCP Python SDK.
It provides tools and resources for persistent memory management for AI agents.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from .embeddings import EmbeddingService
from .models import MemoryEntry
from .storage import MemoryStorage

logger = logging.getLogger(__name__)

# Initialize services
memory_storage = MemoryStorage()
embedding_service = EmbeddingService()

# Create MCP server
mcp = FastMCP("retainr")


class MemoryToolResult(BaseModel):
    """Result from memory operations."""

    success: bool
    message: str
    data: Optional[dict[str, Any]] = None


@mcp.tool()
def save_memory(
    project: str,
    category: str,
    content: str,
    tags: Optional[list[str]] = None,
    references: Optional[list[str]] = None,
) -> str:
    """Save a new memory entry to the persistent storage.

    Args:
        project: Project or repository name
        category: Memory category (architecture, implementation, debugging, documentation, other)
        content: Memory content in markdown format
        tags: Tags for better searchability
        references: Related file paths or references

    Returns:
        Success message with memory details
    """
    try:
        # Create memory entry
        entry = MemoryEntry(
            project=project,
            category=category,
            content=content,
            tags=tags or [],
            references=references or [],
            timestamp=datetime.utcnow(),
        )

        # Save memory
        memory_id, file_path = memory_storage.save_memory(entry)

        # Index in vector database
        embedding_service.index_memory(memory_id, entry, str(file_path))

        return f"Memory saved successfully!\n\nID: {memory_id}\nFile: {file_path}\nProject: {entry.project}\nCategory: {entry.category}"

    except Exception as e:
        logger.error(f"Save memory failed: {e}")
        raise RuntimeError(f"Failed to save memory: {str(e)}") from e


@mcp.tool()
def search_memories(
    query: str,
    project: Optional[str] = None,
    tags: Optional[list[str]] = None,
    top: int = 3,
) -> str:
    """Search for relevant memories using semantic similarity.

    Args:
        query: Search query for finding relevant memories
        project: Optional project filter
        tags: Optional tag filters
        top: Number of top results to return (default: 3)

    Returns:
        Formatted search results
    """
    try:
        # Search memories
        results = embedding_service.search_memories(
            query=query, project=project, tags=tags, top_k=top
        )

        if not results:
            return f"No memories found for query: '{query}'"

        # Format results
        response_text = f"Found {len(results)} relevant memories for '{query}':\n\n"

        for i, result in enumerate(results, 1):
            score_indicator = (
                "🟢" if result.score > 0.8 else "🟡" if result.score > 0.6 else "🔴"
            )
            response_text += f"{i}. {score_indicator} **{result.entry.project}** - {result.entry.category} (Score: {result.score:.3f})\n"
            response_text += f"   Tags: {', '.join(result.entry.tags) if result.entry.tags else 'None'}\n"
            response_text += f"   Content: {result.entry.content[:200]}{'...' if len(result.entry.content) > 200 else ''}\n"
            response_text += f"   File: {result.file_path}\n\n"

        return response_text

    except Exception as e:
        logger.error(f"Search memories failed: {e}")
        raise RuntimeError(f"Failed to search memories: {str(e)}") from e


@mcp.tool()
def list_memories(project: Optional[str] = None, limit: int = 10) -> str:
    """List recent memories, optionally filtered by project.

    Args:
        project: Optional project filter
        limit: Maximum number of memories to return (default: 10)

    Returns:
        Formatted list of memories
    """
    try:
        # Get memory files
        files = memory_storage.list_memory_files(project)
        files = files[:limit]

        if not files:
            filter_text = f" for project '{project}'" if project else ""
            return f"No memories found{filter_text}"

        # Format response
        response_text = f"Recent memories{' for project ' + project if project else ''} ({len(files)} total):\n\n"

        for i, file_path in enumerate(files, 1):
            entry = memory_storage.load_memory(file_path)
            if entry:
                memory_id = memory_storage.get_memory_id(file_path)
                status = "outdated" if entry.outdated else "active"
                status_indicator = "❌" if entry.outdated else "✅"

                response_text += f"{i}. {status_indicator} **{entry.project}** - {entry.category} ({status})\n"
                response_text += f"   ID: {memory_id}\n"
                response_text += (
                    f"   Tags: {', '.join(entry.tags) if entry.tags else 'None'}\n"
                )
                response_text += f"   File: {file_path}\n"
                if entry.timestamp:
                    response_text += (
                        f"   Created: {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                response_text += "\n"

        return response_text

    except Exception as e:
        logger.error(f"List memories failed: {e}")
        raise RuntimeError(f"Failed to list memories: {str(e)}") from e


@mcp.tool()
def update_memory(memory_id: str, outdated: bool) -> str:
    """Update a memory entry (mark as outdated).

    Args:
        memory_id: ID of the memory to update
        outdated: Whether to mark the memory as outdated

    Returns:
        Success message
    """
    try:
        # Find memory file
        file_path = memory_storage.find_memory_by_id(memory_id)
        if not file_path:
            raise ValueError(f"Memory with ID {memory_id} not found")

        # Update memory
        success = memory_storage.update_memory(file_path, outdated)
        if not success:
            raise RuntimeError(f"Failed to update memory {memory_id}")

        # Update vector database
        entry = memory_storage.load_memory(file_path)
        if entry:
            embedding_service.update_memory(memory_id, entry, str(file_path))

        status = "outdated" if outdated else "active"
        return f"Memory {memory_id} marked as {status}"

    except Exception as e:
        logger.error(f"Update memory failed: {e}")
        raise RuntimeError(f"Failed to update memory: {str(e)}") from e


@mcp.resource("memory://{memory_id}")
def get_memory_resource(memory_id: str) -> str:
    """Get memory content as a resource.

    Args:
        memory_id: ID of the memory to retrieve

    Returns:
        Memory content in markdown format
    """
    try:
        file_path = memory_storage.find_memory_by_id(memory_id)
        if not file_path:
            raise ValueError(f"Memory with ID {memory_id} not found")

        entry = memory_storage.load_memory(file_path)
        if not entry:
            raise RuntimeError(f"Failed to load memory {memory_id}")

        # Return the content with metadata
        content = f"# {entry.project} - {entry.category}\n\n"
        if entry.tags:
            content += f"**Tags:** {', '.join(entry.tags)}\n\n"
        if entry.references:
            content += f"**References:** {', '.join(entry.references)}\n\n"
        content += f"**Created:** {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S') if entry.timestamp else 'Unknown'}\n\n"
        content += "---\n\n"
        content += entry.content

        return content

    except Exception as e:
        logger.error(f"Get memory resource failed: {e}")
        raise RuntimeError(f"Failed to get memory resource: {str(e)}") from e


# Server info is set during FastMCP initialization
# The server info is passed when creating the FastMCP instance


def run_server():
    """Run the MCP server with stdio transport."""
    try:
        logger.info("Starting retainr MCP server...")
        mcp.run(transport="stdio")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        raise


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    run_server()
