"""API endpoints for memory operations."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from .embeddings import EmbeddingService
from .models import (
    MemoryEntry,
    MemorySearchResult,
    MemoryUpdateRequest,
)
from .storage import MemoryStorage

logger = logging.getLogger(__name__)

# Initialize services
memory_storage = MemoryStorage()
embedding_service = EmbeddingService()

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryCreateResponse(BaseModel):
    """Response for memory creation."""

    id: str
    file_path: str
    message: str


class MemorySearchResponse(BaseModel):
    """Response for memory search."""

    query: str
    results: list[MemorySearchResult]
    total: int


@router.post(
    "/", response_model=MemoryCreateResponse, status_code=status.HTTP_201_CREATED
)
async def create_memory(entry: MemoryEntry):
    """Create a new memory entry."""
    try:
        # Save to file storage
        memory_id, file_path = memory_storage.save_memory(entry)

        # Index in vector database
        success = embedding_service.index_memory(memory_id, entry, str(file_path))

        if not success:
            logger.warning(
                f"Memory {memory_id} saved to file but failed to index in vector DB"
            )

        return MemoryCreateResponse(
            id=memory_id,
            file_path=str(file_path),
            message=f"Memory saved successfully{'with vector indexing' if success else ' (file only)'}",
        )

    except Exception as e:
        logger.error(f"Failed to create memory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save memory: {str(e)}",
        ) from e


@router.get("/search", response_model=MemorySearchResponse)
async def search_memories(
    query: str,
    project: Optional[str] = None,
    tags: Optional[str] = None,  # Comma-separated tags
    top: int = 3,
):
    """Search for memories using semantic similarity."""
    try:
        # Parse tags if provided
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # Search using embedding service
        results = embedding_service.search_memories(
            query=query,
            project=project,
            tags=tag_list,
            top_k=min(top, 10),  # Limit to max 10 results
        )

        return MemorySearchResponse(query=query, results=results, total=len(results))

    except Exception as e:
        logger.error(f"Failed to search memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search memories: {str(e)}",
        ) from e


@router.patch("/{memory_id}", status_code=status.HTTP_200_OK)
async def update_memory(memory_id: str, update_request: MemoryUpdateRequest):
    """Update a memory entry (mark as outdated)."""
    try:
        # Find memory file by ID
        file_path = memory_storage.find_memory_by_id(memory_id)

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory with ID {memory_id} not found",
            )

        # Update file storage
        success = memory_storage.update_memory(file_path, update_request.outdated)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update memory file",
            )

        # Update vector database
        entry = memory_storage.load_memory(file_path)
        if entry:
            embedding_service.update_memory(memory_id, entry, str(file_path))

        return {"message": f"Memory {memory_id} updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update memory {memory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update memory: {str(e)}",
        ) from e


@router.get("/{memory_id}")
async def get_memory(memory_id: str):
    """Get a specific memory by ID."""
    try:
        file_path = memory_storage.find_memory_by_id(memory_id)

        if not file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory with ID {memory_id} not found",
            )

        entry = memory_storage.load_memory(file_path)

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load memory content",
            )

        return {"id": memory_id, "file_path": str(file_path), "entry": entry}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory {memory_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve memory: {str(e)}",
        ) from e


@router.get("/")
async def list_memories(project: Optional[str] = None, limit: int = 20):
    """List recent memories, optionally filtered by project."""
    try:
        files = memory_storage.list_memory_files(project)
        files = files[:limit]  # Limit results

        memories = []
        for file_path in files:
            entry = memory_storage.load_memory(file_path)
            if entry:
                memory_id = memory_storage.get_memory_id(file_path)
                memories.append(
                    {
                        "id": memory_id,
                        "file_path": str(file_path),
                        "project": entry.project,
                        "category": entry.category,
                        "tags": entry.tags,
                        "timestamp": entry.timestamp,
                        "outdated": entry.outdated,
                    }
                )

        return {"memories": memories, "total": len(memories), "project_filter": project}

    except Exception as e:
        logger.error(f"Failed to list memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list memories: {str(e)}",
        ) from e


@router.get("/stats/collection")
async def get_collection_stats():
    """Get vector database collection statistics."""
    try:
        stats = embedding_service.get_collection_stats()
        return stats

    except Exception as e:
        logger.error(f"Failed to get collection stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}",
        ) from e
