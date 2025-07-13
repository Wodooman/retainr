"""FastAPI application for the MCP Memory Server."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .api import router as memory_router
from .mcp import router as mcp_router

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting retainr MCP Server...")
    logger.info(f"Memory directory: {settings.memory_dir}")
    logger.info(f"ChromaDB URL: {settings.chroma_url}")

    yield

    logger.info("Shutting down retainr MCP Server...")


app = FastAPI(
    title="retainr MCP Server",
    description="Persistent memory server for AI agents",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(memory_router)
app.include_router(mcp_router)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "retainr MCP Server", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    """Detailed health check with service connectivity."""
    try:
        # Import here to avoid circular imports
        from .embeddings import EmbeddingService

        # Test ChromaDB connectivity
        embedding_service = EmbeddingService()
        chroma_stats = embedding_service.get_collection_stats()

        return {
            "status": "healthy",
            "memory_dir": str(settings.memory_dir),
            "chroma_url": settings.chroma_url,
            "chroma_collection": settings.chroma_collection,
            "embedding_model": settings.embedding_model,
            "chroma_stats": chroma_stats,
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "memory_dir": str(settings.memory_dir),
                "chroma_url": settings.chroma_url,
            },
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "mcp_server.main:app", host=settings.host, port=settings.port, reload=True
    )
