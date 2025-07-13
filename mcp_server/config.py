"""Configuration for the MCP server."""

from pathlib import Path
from typing import List

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic.v1 import BaseSettings
    except ImportError:
        from pydantic import BaseSettings


class Settings(BaseSettings):
    """Server configuration."""
    
    # Server settings
    host: str = "127.0.0.1"
    port: int = 8000
    
    # Storage paths
    memory_dir: Path = Path("memory")  # User-configurable for browsable memories
    
    # ChromaDB configuration
    chroma_host: str = "localhost"  # ChromaDB server host
    chroma_port: int = 8001  # ChromaDB server port
    chroma_collection: str = "retainr_memories"  # Collection name
    
    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"
    
    # API settings
    api_prefix: str = ""
    cors_origins: List[str] = ["*"]
    
    # Debug mode
    debug: bool = False
    
    class Config:
        env_prefix = "RETAINR_"
        env_file = ".env"
        env_file_encoding = "utf-8"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Convert string paths to Path objects if needed
        if isinstance(self.memory_dir, str):
            self.memory_dir = Path(self.memory_dir)
        
        # Ensure memory directory exists
        self.memory_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def chroma_url(self) -> str:
        """Get the ChromaDB URL."""
        return f"http://{self.chroma_host}:{self.chroma_port}"


settings = Settings()