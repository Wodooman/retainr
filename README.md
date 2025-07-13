# 🧠 retainr

[![CI Status](https://github.com/Wodooman/retainr/workflows/CI/badge.svg)](https://github.com/Wodooman/retainr/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com)

An open-source MCP (Model Context Protocol) Server that provides persistent memory storage for AI agents like Claude Code. Enable your AI assistants to remember context between sessions and across repositories.

## Features

- **Persistent Memory**: Store and retrieve knowledge across AI agent sessions
- **Semantic Search**: Find relevant memories using vector similarity
- **File-Based Storage**: Human-readable markdown files for all memories
- **MCP Protocol**: Compatible with Claude Code and other AI agents
- **Single-User Mode**: Simple, secure local deployment

## Quick Start

### Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/Wodooman/retainr.git
cd retainr

# Start with Docker Compose
docker-compose up -d

# Or use the Makefile
make up
```

### Local Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python -m uvicorn mcp_server.main:app --reload
```

### Configuration

```bash
# Copy example configuration
cp .env.example .env

# Edit .env to set custom memory storage path
# RETAINR_MEMORY_DIR=/path/to/your/memories
```

### Basic Usage

```bash
# Save a memory from JSON file
retainr save examples/memory1.json

# Search memories with semantic similarity
retainr recall "how to setup the project"

# Search with filters
retainr recall "database schema" --project myapp --top 5

# List recent memories
retainr list --project retainr --limit 10

# Update memory status
retainr update <memory-id> --outdated

# Check server status
retainr status
```

The server stores memories as human-readable markdown files in your configured directory, allowing you to browse and edit them with any text editor.

### Claude Code Integration

To use retainr with Claude Code for persistent memory:

```bash
# 1. Start the retainr server
make up

# 2. Copy MCP configuration for Claude Code
cp claude-code-mcp.json ~/.config/claude-code/mcp.json

# 3. Restart Claude Code to register the MCP server
```

Once configured, Claude Code will automatically:
- Save important information as memories
- Recall relevant context from previous sessions
- Maintain project-specific knowledge across conversations

See [Claude Code Integration Guide](docs/claude-code-integration.md) for detailed setup instructions.

## Architecture

- **FastAPI Server**: RESTful API for memory operations
- **ChromaDB**: Vector database for semantic search (bundled in Docker)
- **CLI**: Command-line interface for interacting with the server
- **Memory Storage**: User-configurable markdown files

## Memory Format

Memories are stored as markdown files with frontmatter metadata:

```markdown
---
project: myapp
category: architecture
tags: [database, schema]
timestamp: 2024-01-15T10:30:00Z
references: [src/models.py, docs/database.md]
outdated: false
---

# Database Schema Design

The application uses PostgreSQL with the following main tables...
```

## Development

### Docker Development

```bash
# Start in development mode with hot reload
make dev

# View logs
make logs

# Run tests in container
make test

# Open shell in container
make shell
```

### Local Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Format code
make format

# Lint code
make lint
```

### Available Make Commands

Run `make help` to see all available commands:

- `make up` - Start server and ChromaDB
- `make dev` - Start in development mode
- `make down` - Stop all services
- `make logs` - View server logs
- `make logs-chroma` - View ChromaDB logs
- `make status` - Show service status
- `make test` - Run tests
- `make clean` - Clean up containers

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Commercial Version

A commercial version with multi-user support and enterprise features is available. Contact us for more information.
