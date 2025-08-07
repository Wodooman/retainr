# Retainr Native Mode Setup

This guide covers setting up retainr in **native mode** - the new recommended approach that provides optimal performance and true MCP compliance.

## Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd retainr

# 2. One-command setup
./setup.sh

# 3. Start MCP server
make start-mcp
```

That's it! Claude Code should now be able to connect to retainr.

## Architecture Overview

```
Claude Code → python -m mcp_server (native) → ChromaDB (Docker)
                                           → Local file storage
```

**Benefits:**
- ✅ **True MCP compliance** - Direct stdio communication
- ✅ **Fast startup** - <5 seconds (vs 5-30s per session)
- ✅ **Better performance** - Single persistent process
- ✅ **Simpler architecture** - No wrapper scripts

## Detailed Setup

### Prerequisites

- **Python 3.10+** - Required for MCP SDK
- **Docker & Docker Compose** - For ChromaDB service only
- **Git** - For cloning the repository

### Step-by-Step Installation

#### 1. Clone Repository
```bash
git clone <repository-url>
cd retainr
```

#### 2. Run Setup Script
```bash
./setup.sh
```

This script will:
- ✅ Check system requirements (Python 3.10+, Docker)
- ✅ Create virtual environment with MCP dependencies
- ✅ Start ChromaDB service (Docker)
- ✅ Pre-download ML models (sentence-transformers)
- ✅ Configure Claude Code integration

#### 3. Start MCP Server
```bash
make start-mcp
```

The server will start and listen for Claude Code connections via stdio.

## Available Commands

### Core Commands
```bash
make setup           # Full setup (one-time)
make start-mcp       # Start native MCP server
make start-chromadb  # Start ChromaDB service
make health-check    # Check system health
```

### Development Commands
```bash
make dev-native      # Start with auto-reload
make test-native     # Run native mode tests
make status-native   # Show setup status
```

### Health & Troubleshooting
```bash
make health-check           # Basic health check
make logs-chromadb          # ChromaDB logs
make status                 # Show service status
```

## Configuration

### Environment Variables
Copy `.env.example` to `.env` and customize:

```bash
# Deployment mode
RETAINR_MODE=native

# Storage locations
RETAINR_MEMORY_DIR=./memory
RETAINR_MODEL_CACHE_DIR=~/.cache/retainr

# ChromaDB service
RETAINR_CHROMA_HOST=localhost
RETAINR_CHROMA_PORT=8000
```

### Claude Code Configuration

The setup script automatically creates this configuration:

```json
{
  "servers": {
    "retainr": {
      "transport": {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "mcp_server"],
        "cwd": "/path/to/retainr",
        "env": {
          "PATH": "/path/to/retainr/venv/bin:$PATH"
        }
      }
    }
  }
}
```

Location: `~/.config/claude-code/mcp.json`

## Usage

Once set up, Claude Code can use these retainr capabilities:

### Save Memories
```
Save a memory about implementing OAuth in my project with tags authentication and security
```

### Search Memories  
```
Search for memories about database optimization techniques
```

### List Recent Memories
```
List my recent memories for the web-app project
```

### Update Memory Status
```
Mark memory abc123 as outdated
```

## Troubleshooting

### Common Issues

#### 1. Python Version Error
```
Error: Python 3.10+ is required, but found Python 3.9
```
**Solution:** Install Python 3.10+ or use a version manager like pyenv.

#### 2. MCP SDK Not Found
```
Error: MCP SDK not available in virtual environment
```
**Solution:** 
```bash
./health-check.sh --fix
# OR manually:
source venv/bin/activate
pip install -r requirements-native.txt
```

#### 3. ChromaDB Not Accessible
```
Error: ChromaDB is not responding on port 8000
```
**Solution:**
```bash
make restart-chromadb
# OR check logs:
make logs-chromadb
```

#### 4. Claude Code Can't Connect
```
Error: Failed to connect to MCP server
```
**Solution:**
```bash
# Check MCP server
make test-mcp-native

# Re-register with Claude Code
./setup.sh

# Restart Claude Code
```

### Advanced Troubleshooting

#### Health Check
```bash
make health-check
```

Sample output:
```
🔍 Running retainr health check...

ℹ️  Checking Python version...
✅ Python 3.11.5

ℹ️  Checking Docker...
✅ Docker and Docker Compose are available

ℹ️  Checking virtual environment...
✅ Virtual environment exists

ℹ️  Checking MCP dependencies...
✅ All MCP dependencies are available

ℹ️  Checking ChromaDB service...
✅ ChromaDB service is running and accessible

ℹ️  Checking MCP server...
✅ MCP server is ready

🎉 All health checks passed!
retainr is ready to use.
```

#### Fix Issues
```bash
# Restart services
make restart-chromadb

# Rebuild virtual environment
rm -rf venv && make setup

# Re-run setup
./setup.sh
```

## Performance

### Expected Performance (Native Mode)
- **Startup time:** <5 seconds (one-time)
- **Tool calls:** 50-200ms 
- **Search queries:** 100-500ms
- **Memory usage:** ~600MB (single process)

### Performance Comparison
| Metric | Native Mode | Docker Mode (Legacy) |
|--------|-------------|---------------------|
| Startup | <5s (once) | 5-30s (per session) |
| Memory | 600MB | 500MB × N processes |
| Tool calls | 50-200ms | 200ms-2s |
| Test suite | <3 minutes | 10+ minutes |

## Migration from Docker Mode

If you're migrating from the old Docker wrapper approach:

### 1. Check Current Mode
```bash
grep RETAINR_MODE .env || echo "Not set (defaults to native)"
```

### 2. Backup Existing Data
```bash
cp -r memory memory.backup
cp -r chroma chroma.backup
```

### 3. Run Native Setup
```bash
./setup.sh
```

### 4. Verify Migration
```bash
make health-check
make test-mcp-native
```

Your existing memory files and ChromaDB data will be preserved.

## Development

### Running Tests
```bash
# Native mode tests only
make test-native

# Unit tests
make test-native-unit

# Integration tests
make test-native-integration
```

### Development Mode
```bash
# Start with auto-reload
make dev-native

# Install dev dependencies
make install-native-dev

# Code formatting
make format-native
make lint-native
```

### Environment Variables for Testing
```bash
export RETAINR_TEST_MODE=native
export RETAINR_MODE=native
```

## File Structure

```
retainr/
├── venv/                      # Python virtual environment
├── memory/                    # Memory files (markdown)
├── chroma/                    # ChromaDB data (Docker volume)
├── mcp_server/               # MCP server implementation
├── setup.sh                 # One-command setup
├── health-check.sh          # Health check & auto-fix
├── register-claude-code.sh  # Claude Code registration
├── docker-compose.yml           # ChromaDB service
├── requirements-native.txt  # Native Python dependencies
└── claude-mcp-config.json  # Generated Claude Code config
```

## Support

If you encounter issues:

1. **Run health check:** `./health-check.sh --fix`
2. **Check logs:** `make logs-chromadb`
3. **Test MCP server:** `make test-mcp-native`  
4. **Verify Claude Code config:** `cat ~/.config/claude-code/mcp.json`

For additional help, check the main README.md or open an issue.
