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

## Python Version Management

**Native mode requires Python 3.10+**. Use pyenv for version management:

### Install pyenv (one-time setup)
```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to shell configuration (choose your shell)
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init - zsh)"' >> ~/.zshrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.zshrc

# Restart shell or source config
source ~/.zshrc
```

### Python Version Setup
```bash
# Install Python 3.11.8 (recommended)
pyenv install 3.11.8

# Set as global default
pyenv global 3.11.8

# Set for this project (creates .python-version file)
pyenv local 3.11.8

# Verify version
python --version  # Should show Python 3.11.8
```

### Usage Commands
```bash
pyenv versions        # List installed versions
pyenv install --list # List available versions
pyenv local 3.11.8   # Set project-specific version
pyenv global 3.11.8  # Set system-wide default
```

## MCP Server Context

This server will integrate with AI agents through the Model Context Protocol, allowing:
- Storage of learned information between sessions
- Retrieval of previously stored knowledge
- Cross-repository context sharing
- Session continuity for AI agents

## Project Status

✅ **Core functionality implemented and ready for use:**

### Completed Features
- ✅ **Standard MCP server** with full protocol compliance
- ✅ **Legacy FastAPI server** with full memory management API
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

**Docker-based MCP Server (Production Ready):**
- ✅ **Full MCP protocol compliance** using official Python SDK
- ✅ **Docker deployment** - no local dependencies required
- ✅ **stdio transport** for direct Claude Code integration
- ✅ **Standards-compliant** tools, resources, and error handling
- ✅ **Consistent environment** across all systems
- Tools: save_memory, search_memories, list_memories, update_memory
- Resources: Access to memory content via `memory://{id}` URIs

**Legacy HTTP MCP Server (Deprecated):**
- Custom HTTP-based implementation
- Compatible with current Claude Code but non-standard
- Will be removed in future versions

### Claude Code Setup
```bash
# Quick setup for Docker-based MCP server (recommended)
make setup-claude-code

# Manual setup
cp claude-code-mcp.json ~/.config/claude-code/mcp.json
chmod +x mcp_server_wrapper.sh
```

**Note:** This setup uses Docker containers with the MCP Python SDK pre-installed. No local Python dependencies required!

## Development Commands

**IMPORTANT: Always use make commands for all development tasks. Never run pytest, source venv, or other commands directly. This ensures consistent environment setup and follows project conventions.**

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

# Run tests against running services
make test
```

### Docker Setup (Recommended)
```bash
# Start all services (MCP server + REST API + ChromaDB)
make up

# Development mode with hot reload
make dev

# Run standard MCP server for testing
./mcp_server_wrapper.sh

# Access REST API at http://localhost:8000
# Access ChromaDB at http://localhost:8001
```

### Local Setup (Advanced)
```bash
# Only if you need local development without Docker
# Requires Python 3.10+ and manual dependency management
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start the REST API server locally
make run-local
```

### Testing (Preferred Commands)

**IMPORTANT: Always use make commands for testing to ensure proper environment setup.**

#### Quick Testing (Fast)
```bash
# Unit tests only (fastest - no services required)
make test-unit                  # Docker environment
make test-native-unit          # Native environment (requires setup)

# Setup validation (configuration and files)
make test-setup                # No services required
```

#### Integration Testing (Medium)
```bash
# Start services first
make up                        # Docker services
# OR
make setup && make start-chromadb  # Native setup

# Then run integration tests
make test-integration          # Docker mode
make test-native-integration   # Native mode
```

#### Full Testing (Comprehensive)
```bash
# Docker mode testing (current)
make up                        # Start Docker services
make test                      # All tests
make test-all-mcp             # All MCP-related tests
make test-cov                 # With coverage report

# Native mode testing (new architecture)
make setup                     # One-time setup
make start-chromadb           # Start ChromaDB service
make test-native              # All native tests
make health-check             # Verify setup
```

#### Specific Test Categories
```bash
# MCP Protocol Compliance
make test-mcp-protocol        # Protocol compliance (requires 'make up')
make test-standard-mcp        # Standard MCP server tests

# Performance and Validation
make test-docker              # Docker integration tests
make test-mcp-native         # Native MCP server connectivity

# Legacy (Deprecated)
make test-legacy-mcp         # Legacy HTTP endpoints
```

#### Testing Workflow Recommendations

**For Development:**
1. `make test-unit` - Fast feedback on code changes
2. `make test-native-unit` - After native setup

**For Feature Testing:**
1. `make up` or `make setup && make start-chromadb`
2. `make test-integration` or `make test-native-integration`
3. `make health-check` - Verify system health

**For Release Validation:**
1. `make up` - Start all Docker services
2. `make test-all-mcp` - Comprehensive MCP testing
3. `make test-cov` - Coverage analysis
4. `make test-native` - Native architecture validation (if setup available)

**Troubleshooting Tests:**
```bash
make status-native            # Check native setup status
make health-check             # Diagnose issues
make logs                     # Check service logs
make restart                  # Restart services if needed
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
