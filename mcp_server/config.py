"""Configuration for the MCP server."""

from pathlib import Path

try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic.v1 import BaseSettings
    except ImportError:
        from pydantic import BaseSettings


class Settings(BaseSettings):
    """Server configuration."""

    # Deployment mode
    mode: str = "native"  # native, docker, or auto

    # Server settings (legacy API)
    host: str = "127.0.0.1"
    port: int = 8000

    # Storage paths
    memory_dir: Path = Path("memory")  # User-configurable for browsable memories

    # Model cache directory
    model_cache_dir: Path = Path.home() / ".cache" / "retainr"

    # ChromaDB configuration (Docker service)
    chroma_host: str = "localhost"  # ChromaDB server host
    chroma_port: int = (
        8000  # ChromaDB server port (matches docker-compose.chromadb.yml)
    )
    chroma_collection: str = "retainr_memories"  # Collection name

    # MCP server settings
    mcp_transport: str = "stdio"  # Transport type for MCP server

    # Embedding model
    embedding_model: str = "all-MiniLM-L6-v2"

    # API settings (legacy FastAPI support)
    api_prefix: str = ""
    cors_origins: list[str] = ["*"]

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
        if isinstance(self.model_cache_dir, str):
            self.model_cache_dir = Path(self.model_cache_dir).expanduser()
        elif isinstance(self.model_cache_dir, Path):
            self.model_cache_dir = self.model_cache_dir.expanduser()

        # Auto-detect mode if set to auto
        if self.mode == "auto":
            self.mode = self._detect_mode()

        # Ensure directories exist
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)

    def _detect_mode(self) -> str:
        """Auto-detect the best deployment mode."""
        import shutil

        # Check if virtual environment exists (native mode indicator)
        if (Path.cwd() / "venv").exists():
            return "native"

        # Check if Docker and docker-compose are available (docker mode indicator)
        if shutil.which("docker") and shutil.which("docker-compose"):
            return "docker"

        # Default to native mode
        return "native"

    def is_native_mode(self) -> bool:
        """Check if running in native mode."""
        return self.mode == "native"

    def is_docker_mode(self) -> bool:
        """Check if running in Docker mode."""
        return self.mode == "docker"

    @property
    def chroma_url(self) -> str:
        """Get the ChromaDB URL."""
        return f"http://{self.chroma_host}:{self.chroma_port}"


settings = Settings()
