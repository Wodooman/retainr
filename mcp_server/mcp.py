"""MCP (Model Context Protocol) implementation for retainr."""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from .models import MemoryEntry
from .storage import MemoryStorage
from .embeddings import EmbeddingService

logger = logging.getLogger(__name__)

# Initialize services
memory_storage = MemoryStorage()
embedding_service = EmbeddingService()

router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPInitializeRequest(BaseModel):
    """MCP initialization request."""
    protocolVersion: str
    clientInfo: Dict[str, Any]


class MCPInitializeResponse(BaseModel):
    """MCP initialization response."""
    protocolVersion: str
    serverInfo: Dict[str, Any]
    capabilities: Dict[str, Any]


class MCPToolsListResponse(BaseModel):
    """MCP tools list response."""
    tools: List[Dict[str, Any]]


class MCPToolCallRequest(BaseModel):
    """MCP tool call request."""
    name: str
    arguments: Dict[str, Any]


class MCPToolCallResponse(BaseModel):
    """MCP tool call response."""
    content: List[Dict[str, Any]]
    isError: bool = False


class MCPResourcesListResponse(BaseModel):
    """MCP resources list response."""
    resources: List[Dict[str, Any]]


@router.post("/initialize", response_model=MCPInitializeResponse)
async def mcp_initialize(request: MCPInitializeRequest):
    """Initialize MCP session."""
    logger.info(f"MCP initialization from client: {request.clientInfo}")
    
    return MCPInitializeResponse(
        protocolVersion="1.0",
        serverInfo={
            "name": "retainr",
            "version": "0.1.0",
            "description": "Persistent memory server for AI agents"
        },
        capabilities={
            "tools": {
                "listChanged": False
            },
            "resources": {
                "subscribe": False,
                "listChanged": False
            }
        }
    )


@router.post("/tools/list", response_model=MCPToolsListResponse)
async def mcp_tools_list():
    """List available MCP tools."""
    tools = [
        {
            "name": "save_memory",
            "description": "Save a new memory entry to the persistent storage",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project or repository name"
                    },
                    "category": {
                        "type": "string", 
                        "description": "Memory category (architecture, implementation, debugging, documentation, other)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Memory content in markdown format"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for better searchability"
                    },
                    "references": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Related file paths or references"
                    }
                },
                "required": ["project", "category", "content"]
            }
        },
        {
            "name": "search_memories",
            "description": "Search for relevant memories using semantic similarity",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for finding relevant memories"
                    },
                    "project": {
                        "type": "string",
                        "description": "Optional project filter"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tag filters"
                    },
                    "top": {
                        "type": "integer",
                        "default": 3,
                        "description": "Number of top results to return"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "list_memories",
            "description": "List recent memories, optionally filtered by project",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Optional project filter"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of memories to return"
                    }
                }
            }
        },
        {
            "name": "update_memory",
            "description": "Update a memory entry (mark as outdated)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "memory_id": {
                        "type": "string",
                        "description": "ID of the memory to update"
                    },
                    "outdated": {
                        "type": "boolean",
                        "description": "Whether to mark the memory as outdated"
                    }
                },
                "required": ["memory_id", "outdated"]
            }
        }
    ]
    
    return MCPToolsListResponse(tools=tools)


@router.post("/tools/call", response_model=MCPToolCallResponse)
async def mcp_tool_call(request: MCPToolCallRequest):
    """Execute MCP tool call."""
    try:
        tool_name = request.name
        args = request.arguments
        
        if tool_name == "save_memory":
            return await _tool_save_memory(args)
        elif tool_name == "search_memories":
            return await _tool_search_memories(args)
        elif tool_name == "list_memories":
            return await _tool_list_memories(args)
        elif tool_name == "update_memory":
            return await _tool_update_memory(args)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
            
    except HTTPException:
        # Re-raise HTTP exceptions to return proper status codes
        raise
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        return MCPToolCallResponse(
            content=[{
                "type": "text",
                "text": f"Error executing tool {request.name}: {str(e)}"
            }],
            isError=True
        )


async def _tool_save_memory(args: Dict[str, Any]) -> MCPToolCallResponse:
    """Save memory tool implementation."""
    try:
        # Create memory entry
        entry = MemoryEntry(
            project=args["project"],
            category=args["category"],
            content=args["content"],
            tags=args.get("tags", []),
            references=args.get("references", []),
            timestamp=datetime.utcnow()
        )
        
        # Save memory
        memory_id, file_path = memory_storage.save_memory(entry)
        
        # Index in vector database
        embedding_service.index_memory(memory_id, entry, str(file_path))
        
        return MCPToolCallResponse(
            content=[{
                "type": "text",
                "text": f"Memory saved successfully!\n\nID: {memory_id}\nFile: {file_path}\nProject: {entry.project}\nCategory: {entry.category}"
            }]
        )
        
    except Exception as e:
        logger.error(f"Save memory failed: {e}")
        raise


async def _tool_search_memories(args: Dict[str, Any]) -> MCPToolCallResponse:
    """Search memories tool implementation."""
    try:
        query = args["query"]
        project = args.get("project")
        tags = args.get("tags")
        top = args.get("top", 3)
        
        # Search memories
        results = embedding_service.search_memories(
            query=query,
            project=project,
            tags=tags,
            top_k=top
        )
        
        if not results:
            return MCPToolCallResponse(
                content=[{
                    "type": "text",
                    "text": f"No memories found for query: '{query}'"
                }]
            )
        
        # Format results
        response_text = f"Found {len(results)} relevant memories for '{query}':\n\n"
        
        for i, result in enumerate(results, 1):
            score_indicator = "🟢" if result.score > 0.8 else "🟡" if result.score > 0.6 else "🔴"
            response_text += f"{i}. {score_indicator} **{result.entry.project}** - {result.entry.category} (Score: {result.score:.3f})\n"
            response_text += f"   Tags: {', '.join(result.entry.tags) if result.entry.tags else 'None'}\n"
            response_text += f"   Content: {result.entry.content[:200]}{'...' if len(result.entry.content) > 200 else ''}\n"
            response_text += f"   File: {result.file_path}\n\n"
        
        return MCPToolCallResponse(
            content=[{
                "type": "text",
                "text": response_text
            }]
        )
        
    except Exception as e:
        logger.error(f"Search memories failed: {e}")
        raise


async def _tool_list_memories(args: Dict[str, Any]) -> MCPToolCallResponse:
    """List memories tool implementation."""
    try:
        project = args.get("project")
        limit = args.get("limit", 10)
        
        # Get memory files
        files = memory_storage.list_memory_files(project)
        files = files[:limit]
        
        if not files:
            filter_text = f" for project '{project}'" if project else ""
            return MCPToolCallResponse(
                content=[{
                    "type": "text",
                    "text": f"No memories found{filter_text}"
                }]
            )
        
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
                response_text += f"   Tags: {', '.join(entry.tags) if entry.tags else 'None'}\n"
                response_text += f"   File: {file_path}\n"
                if entry.timestamp:
                    response_text += f"   Created: {entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                response_text += "\n"
        
        return MCPToolCallResponse(
            content=[{
                "type": "text", 
                "text": response_text
            }]
        )
        
    except Exception as e:
        logger.error(f"List memories failed: {e}")
        raise


async def _tool_update_memory(args: Dict[str, Any]) -> MCPToolCallResponse:
    """Update memory tool implementation."""
    try:
        memory_id = args["memory_id"]
        outdated = args["outdated"]
        
        # Find memory file
        file_path = memory_storage.find_memory_by_id(memory_id)
        if not file_path:
            return MCPToolCallResponse(
                content=[{
                    "type": "text",
                    "text": f"Memory with ID {memory_id} not found"
                }],
                isError=True
            )
        
        # Update memory
        success = memory_storage.update_memory(file_path, outdated)
        if not success:
            return MCPToolCallResponse(
                content=[{
                    "type": "text",
                    "text": f"Failed to update memory {memory_id}"
                }],
                isError=True
            )
        
        # Update vector database
        entry = memory_storage.load_memory(file_path)
        if entry:
            embedding_service.update_memory(memory_id, entry, str(file_path))
        
        status = "outdated" if outdated else "active"
        return MCPToolCallResponse(
            content=[{
                "type": "text",
                "text": f"Memory {memory_id} marked as {status}"
            }]
        )
        
    except Exception as e:
        logger.error(f"Update memory failed: {e}")
        raise


@router.post("/resources/list", response_model=MCPResourcesListResponse)
async def mcp_resources_list():
    """List available MCP resources."""
    # For now, we'll expose recent memories as resources
    try:
        files = memory_storage.list_memory_files()[:20]  # Limit to recent 20
        
        resources = []
        for file_path in files:
            entry = memory_storage.load_memory(file_path)
            if entry and not entry.outdated:
                memory_id = memory_storage.get_memory_id(file_path)
                resources.append({
                    "uri": f"memory://{memory_id}",
                    "name": f"{entry.project} - {entry.category}",
                    "description": entry.content[:100] + "..." if len(entry.content) > 100 else entry.content,
                    "mimeType": "text/markdown"
                })
        
        return MCPResourcesListResponse(resources=resources)
        
    except Exception as e:
        logger.error(f"List resources failed: {e}")
        return MCPResourcesListResponse(resources=[])


@router.get("/resources/{memory_id}")
async def mcp_get_resource(memory_id: str):
    """Get resource content by memory ID."""
    try:
        file_path = memory_storage.find_memory_by_id(memory_id)
        if not file_path:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        entry = memory_storage.load_memory(file_path)
        if not entry:
            raise HTTPException(status_code=404, detail="Failed to load memory")
        
        return {
            "contents": [{
                "uri": f"memory://{memory_id}",
                "mimeType": "text/markdown",
                "text": entry.content
            }]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get resource failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to get resource")