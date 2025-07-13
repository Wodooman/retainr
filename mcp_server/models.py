"""Data models for memory entries."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """Schema for a memory entry."""
    
    project: str = Field(..., description="Project/repository name")
    category: str = Field(..., description="Category: architecture, implementation, debugging, documentation, other")
    tags: List[str] = Field(default_factory=list, description="Tags for searchability")
    references: List[str] = Field(default_factory=list, description="Related file paths")
    content: str = Field(..., description="Memory content in markdown format")
    outdated: bool = Field(False, description="Whether this memory is outdated")
    timestamp: Optional[datetime] = Field(None, description="Creation timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project": "myapp",
                "category": "architecture",
                "tags": ["database", "postgresql"],
                "references": ["src/models.py"],
                "content": "# Database Design\n\nUsing PostgreSQL for ACID compliance...",
                "outdated": False
            }
        }


class MemorySearchParams(BaseModel):
    """Parameters for memory search."""
    
    query: str = Field(..., description="Search query")
    project: Optional[str] = Field(None, description="Filter by project")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    top: int = Field(3, ge=1, le=10, description="Number of results to return")


class MemorySearchResult(BaseModel):
    """Single search result."""
    
    id: str = Field(..., description="Memory ID")
    score: float = Field(..., description="Relevance score")
    entry: MemoryEntry = Field(..., description="Memory entry")
    file_path: str = Field(..., description="Path to markdown file")


class MemoryUpdateRequest(BaseModel):
    """Request to update a memory entry."""
    
    outdated: bool = Field(..., description="Mark as outdated")