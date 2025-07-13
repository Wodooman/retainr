"""Vector embeddings and ChromaDB integration."""

import logging
from typing import List, Optional, Dict, Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .config import settings
from .models import MemoryEntry, MemorySearchResult

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Handles vector embeddings and ChromaDB operations."""
    
    def __init__(self):
        self.model = None
        self.chroma_client = None
        self.collection = None
        self._initialize_model()
        self._initialize_chroma()
    
    def _initialize_model(self):
        """Initialize the sentence transformer model."""
        try:
            self.model = SentenceTransformer(settings.embedding_model)
            logger.info(f"Initialized embedding model: {settings.embedding_model}")
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            raise
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client and collection."""
        try:
            # Connect to ChromaDB server
            self.chroma_client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False
                )
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.chroma_collection,
                metadata={"description": "retainr memory embeddings"}
            )
            
            logger.info(f"Connected to ChromaDB at {settings.chroma_url}")
            logger.info(f"Using collection: {settings.chroma_collection}")
            
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self.model:
            raise RuntimeError("Embedding model not initialized")
        
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def _prepare_text_for_embedding(self, entry: MemoryEntry) -> str:
        """Prepare text content for embedding generation."""
        # Combine relevant fields for better semantic search
        parts = []
        
        # Add content (main text)
        if entry.content:
            parts.append(entry.content)
        
        # Add tags as context
        if entry.tags:
            parts.append(" ".join(entry.tags))
        
        # Add category
        if entry.category:
            parts.append(entry.category)
        
        return " ".join(parts)
    
    def index_memory(self, memory_id: str, entry: MemoryEntry, file_path: str) -> bool:
        """Index memory entry into ChromaDB."""
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")
        
        try:
            # Prepare text for embedding
            text = self._prepare_text_for_embedding(entry)
            
            # Generate embedding
            embedding = self.generate_embedding(text)
            
            # Prepare metadata
            metadata = {
                "project": entry.project,
                "category": entry.category,
                "tags": ",".join(entry.tags) if entry.tags else "",
                "references": ",".join(entry.references) if entry.references else "",
                "file_path": file_path,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else "",
                "outdated": entry.outdated
            }
            
            # Add to collection
            self.collection.add(
                ids=[memory_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata]
            )
            
            logger.info(f"Indexed memory {memory_id} into ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to index memory {memory_id}: {e}")
            return False
    
    def search_memories(
        self, 
        query: str, 
        project: Optional[str] = None,
        tags: Optional[List[str]] = None,
        top_k: int = 3
    ) -> List[MemorySearchResult]:
        """Search for similar memories."""
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")
        
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # Prepare filter conditions
            where_conditions = {}
            
            if project:
                where_conditions["project"] = project
            
            # Don't include outdated memories by default
            where_conditions["outdated"] = False
            
            # Build where clause
            where = where_conditions if where_conditions else None
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            # Convert to MemorySearchResult objects
            search_results = []
            
            for i, memory_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                distance = results["distances"][0][i]
                
                # Convert distance to similarity score (0-1, higher is better)
                score = max(0, 1 - distance)
                
                # Reconstruct MemoryEntry from metadata
                entry = MemoryEntry(
                    project=metadata["project"],
                    category=metadata["category"],
                    tags=metadata["tags"].split(",") if metadata["tags"] else [],
                    references=metadata["references"].split(",") if metadata["references"] else [],
                    content=results["documents"][0][i],
                    outdated=metadata["outdated"],
                    timestamp=metadata["timestamp"]
                )
                
                search_result = MemorySearchResult(
                    id=memory_id,
                    score=score,
                    entry=entry,
                    file_path=metadata["file_path"]
                )
                
                search_results.append(search_result)
            
            logger.info(f"Found {len(search_results)} memories for query: {query}")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    def update_memory(self, memory_id: str, entry: MemoryEntry, file_path: str) -> bool:
        """Update memory entry in ChromaDB."""
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")
        
        try:
            # Delete existing entry
            self.delete_memory(memory_id)
            
            # Re-index with updated data
            return self.index_memory(memory_id, entry, file_path)
            
        except Exception as e:
            logger.error(f"Failed to update memory {memory_id}: {e}")
            return False
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete memory from ChromaDB."""
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")
        
        try:
            self.collection.delete(ids=[memory_id])
            logger.info(f"Deleted memory {memory_id} from ChromaDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self.collection:
            return {"error": "Collection not initialized"}
        
        try:
            count = self.collection.count()
            return {
                "total_memories": count,
                "collection_name": settings.chroma_collection,
                "embedding_model": settings.embedding_model
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}