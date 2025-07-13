# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

**retainr** is an open-source MCP (Model Context Protocol) Server that serves as a persistent memory bank for AI agents like Claude Code. It enables knowledge preservation between sessions and across different repositories.

## Project Purpose

- **Core Function**: MCP Server providing persistent memory/knowledge storage for AI agents
- **Target Users**: AI agents (Claude Code and others) that need to maintain context between sessions
- **Key Feature**: Cross-repository and cross-session knowledge persistence
- **License**: Apache License 2.0 (open source)

## Version Differences

### Open Source Version (This Repository)
- Single-user mode only
- Core memory persistence functionality
- Free to use and modify under Apache 2.0

### Paid Version (Separate Private Repository)
- Multi-user mode support
- Additional enterprise features
- Closed source

## Development Guidelines

When implementing features:
1. Ensure all code remains compatible with single-user mode
2. Keep the architecture extensible but don't include multi-user code
3. Focus on robust memory persistence and retrieval mechanisms
4. Follow MCP protocol specifications for compatibility with AI agents
5. Use optimized CI workflow for faster development cycles

## MCP Server Context

This server will integrate with AI agents through the Model Context Protocol, allowing:
- Storage of learned information between sessions
- Retrieval of previously stored knowledge
- Cross-repository context sharing
- Session continuity for AI agents

## Project Status

✅ **Core functionality implemented and ready for use:**

### Completed Features
- ✅ FastAPI server with full memory management API
- ✅ File-based storage (markdown with YAML frontmatter)
- ✅ ChromaDB vector indexing for semantic search
- ✅ CLI client with rich terminal interface
- ✅ Docker Compose setup with bundled ChromaDB
- ✅ User-configurable memory storage paths
- ✅ Health checks and error handling

### Available Endpoints
- `POST /memory` - Save new memories
- `GET /memory/search` - Semantic search with filters
- `GET /memory` - List recent memories
- `GET /memory/{id}` - Get specific memory
- `PATCH /memory/{id}` - Update memory status
- `GET /health` - Server health and stats

### CLI Commands
- `retainr save <file.json>` - Save memory from JSON
- `retainr recall "<query>"` - Search memories
- `retainr list` - List recent memories
- `retainr status` - Check server health

### MCP Integration
- Full MCP protocol implementation for Claude Code
- Automatic memory persistence across sessions
- Tools: save_memory, search_memories, list_memories, update_memory
- Resources: Access to memory content via MCP resource protocol

### Claude Code Setup
```bash
# Quick setup for Claude Code integration
make setup-claude-code

# Manual setup
cp claude-code-mcp.json ~/.config/claude-code/mcp.json
```

## Development Commands

### Docker (Recommended)
```bash
# Build and start the server
make up

# Development mode with hot reload
make dev

# View logs
make logs

# Stop the server
make down

# Run tests in container
make test
```

### Local Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install -r requirements-dev.txt

# Start the FastAPI server locally
python -m uvicorn mcp_server.main:app --reload
```

### Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=mcp_server --cov=cli
```

### Code Quality

**IMPORTANT: Always run format and lint checks before committing to avoid pre-commit hook modifications:**

```bash
# REQUIRED before every commit - use Makefile commands:
make format

# Then proceed with commit
git add .
git commit -m "your message"
```

**Or manually (same as Makefile):**
```bash
# Format code (fixes issues automatically)
black .
ruff check --fix .
```

**Check code quality (same as CI):**
```bash
# Use Makefile (recommended)
make lint

# Or manually (same commands as CI)
black --check --diff .
ruff check .
mypy mcp_server cli --ignore-missing-imports
```

**Available Makefile commands:**
```bash
make format          # Format code (black + ruff --fix)
make lint           # Check code quality (same as CI)
make pre-commit-run # Run all pre-commit hooks
make test           # Run all tests
make test-unit      # Run unit tests only
make test-cov       # Run tests with coverage
```

### CI/CD Optimization
✅ **Optimized CI**: Uses registry caching and conditional builds for 2.36GB Docker image
- 🚀 **75% faster CI** for code changes (25min → 6min)
- ⚡ **96% faster CI** for documentation changes (25min → 1min)
- 🔄 **Registry cache** for reliable large image caching
- 🎯 **Conditional builds** skip Docker when unchanged

### Configuration
```bash
# Copy and customize configuration
cp .env.example .env

# Set custom memory storage path in .env:
# RETAINR_MEMORY_DIR=/path/to/your/memories
```

### CLI Usage
```bash
# Save a memory
retainr save memory.json

# Search memories
retainr recall "query text" --project myapp --top 5
```

### Memory Storage
Memories are stored as markdown files that can be browsed and edited:
- Default location: `./memory/` directory
- Configurable via `RETAINR_MEMORY_DIR` environment variable
- Human-readable format with YAML frontmatter
- Organized by project folders

## Project Structure

```
retainr/
├── mcp_server/        # FastAPI backend
│   ├── models.py      # Pydantic data models
│   ├── config.py      # Server configuration
│   ├── storage.py     # File-based storage logic
│   ├── embeddings.py  # Vector embedding with Chroma
│   └── main.py        # FastAPI application
├── cli/               # Command-line interface
│   └── main.py        # Click CLI implementation
├── memory/            # Markdown memory files (gitignored)
├── chroma/            # Vector database (gitignored)
├── prompt-template.md # Memory format documentation
└── Specs.md          # Implementation specifications
```
