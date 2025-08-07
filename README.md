# 🧠 retainr

[![CI Status](https://github.com/Wodooman/retainr/workflows/CI/badge.svg)](https://github.com/Wodooman/retainr/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com)

An open-source MCP (Model Context Protocol) Server that provides persistent memory storage for AI agents like Claude Code. Enable your AI assistants to remember context between sessions and across repositories.

## Features

- **Persistent Memory**: Store and retrieve knowledge across AI agent sessions
- **Semantic Search**: Find relevant memories using vector similarity
- **File-Based Storage**: Human-readable markdown files for all memories
- **MCP Protocol**: Compatible with Claude Code and other AI agents
- **Single-User Mode**: Simple, secure local deployment

## Quick Start

### Native Mode (Recommended)

```bash
# Clone the repository
git clone https://github.com/Wodooman/retainr.git
cd retainr

# One-command setup
./setup.sh

# Start MCP server
make start-mcp
```

### Manual Installation

```bash
# Install dependencies
make setup

# Start ChromaDB service
make start-chromadb

# Start the MCP server
make start-mcp
```

### Configuration

```bash
# Copy example configuration
cp .env.example .env

# Edit .env to set custom memory storage path
# RETAINR_MEMORY_DIR=/path/to/your/memories
```

### Basic Usage

Once connected to Claude Code, you can use natural language:

```
# Save important information
"Save a memory about implementing OAuth in my project with tags authentication and security"

# Search for relevant context
"Search for memories about database optimization techniques"

# List recent memories
"List my recent memories for the web-app project"

# Update memory status
"Mark memory abc123 as outdated"
```

The server stores memories as human-readable markdown files in your configured directory, allowing you to browse and edit them with any text editor.

### Claude Code Integration

To use retainr with Claude Code for persistent memory:

```bash
# 1. Run the setup script (includes Claude Code configuration)
./setup.sh

# 2. Start the MCP server
make start-mcp

# 3. Restart Claude Code to register the MCP server
```

Once configured, Claude Code will automatically:
- Save important information as memories
- Recall relevant context from previous sessions
- Maintain project-specific knowledge across conversations

See [Claude Code Integration Guide](docs/claude-code-integration.md) for detailed setup instructions.

## Architecture

- **Native MCP Server**: Standards-compliant MCP server using Python SDK
- **ChromaDB**: Vector database for semantic search (Docker service)
- **Memory Storage**: Human-readable markdown files with YAML frontmatter
- **Claude Code Integration**: Direct stdio communication via MCP protocol

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

### Native Development

```bash
# Start in development mode with auto-reload
make dev-native

# View ChromaDB logs
make logs-chromadb

# Run tests
make test

# Check system health
make health-check
```

### Code Quality

```bash
# Install development dependencies
make venv-dev

# Format code
make format

# Lint code
make lint

# Run tests with coverage
make test-cov
```

### Available Make Commands

Run `make help` to see all available commands:

- `make setup` - Full setup with dependencies and ChromaDB
- `make start-mcp` - Start native MCP server
- `make start-chromadb` - Start ChromaDB service
- `make dev-native` - Start in development mode
- `make logs-chromadb` - View ChromaDB logs
- `make health-check` - Check system health
- `make test` - Run tests
- `make clean` - Clean up Python artifacts

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! All PRs must pass automated quality checks:

- ✅ **Code Quality**: Black formatting + Ruff linting
- ✅ **Unit Tests**: Python 3.9, 3.11, 3.12 
- ✅ **Security**: Bandit + Safety scans
- ✅ **Build**: Docker build verification

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## Commercial Version

A commercial version with multi-user support and enterprise features is available. Contact us for more information.
