# Claude Code Integration Guide

This guide explains how to register and use the retainr MCP server with Claude Code for persistent memory across sessions.

## Prerequisites

1. **Claude Code installed** - Make sure you have Claude Code CLI installed
2. **retainr server running** - Follow the main README to start the server
3. **Server accessible** - Server should be running on `http://localhost:8000`

## MCP Server Registration

### Method 1: Using Claude Code Settings (Recommended)

1. **Copy the MCP configuration file**

```bash
# Copy the provided configuration
cp claude-code-mcp.json ~/.config/claude-code/mcp.json
```

Or manually create the file:

**Location:**
- **macOS/Linux:** `~/.config/claude-code/mcp.json`
- **Windows:** `%APPDATA%\claude-code\mcp.json`

**Configuration:**
```json
{
  "servers": {
    "retainr": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8000/mcp"
      },
      "description": "Persistent memory server for AI agents",
      "capabilities": ["tools", "resources"]
    }
  }
}
```

### Method 2: Environment Variable Configuration

Set environment variables for automatic discovery:

```bash
export CLAUDE_MCP_RETAINR_URL="http://localhost:8000/mcp"
export CLAUDE_MCP_RETAINR_NAME="retainr"
```

## MCP Protocol Implementation

The retainr server implements the full MCP protocol with these endpoints:

### Available MCP Endpoints

- `POST /mcp/initialize` - Initialize MCP session
- `POST /mcp/tools/list` - List available tools
- `POST /mcp/tools/call` - Execute tool calls
- `POST /mcp/resources/list` - List available memory resources
- `GET /mcp/resources/{memory_id}` - Get memory content

### Available MCP Tools

1. **save_memory** - Save new memory entries
2. **search_memories** - Semantic search for relevant memories
3. **list_memories** - List recent memories with optional filtering
4. **update_memory** - Mark memories as outdated or active

## Usage with Claude Code

Once registered, Claude Code can use retainr for:

### 1. Automatic Memory Storage

Claude Code will automatically store important information:

```
==BEGIN_MEMORY==
{
  "project": "my-web-app",
  "category": "implementation", 
  "tags": ["authentication", "jwt", "security"],
  "references": ["src/auth.py", "src/middleware.py"],
  "content": "# JWT Authentication Setup\n\nImplemented JWT authentication with 24-hour token expiry. Refresh tokens last 30 days. Secret stored in JWT_SECRET_KEY environment variable.",
  "outdated": false
}
==END_MEMORY==
```

### 2. Memory Recall

Claude Code can search for relevant memories:

```markdown
I'll search for previous information about authentication setup...

*Searches retainr for "JWT authentication setup"*

Based on my memory, you previously implemented JWT authentication with...
```

### 3. Cross-Session Continuity

Memories persist across Claude Code sessions, providing context for:
- Previous architectural decisions
- Bug fixes and solutions
- Implementation patterns
- Project-specific conventions

## Testing the Integration

### 1. Verify Server is Running

```bash
# Check if retainr is accessible
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "memory_dir": "./memory",
  "chroma_url": "http://chroma:8000",
  ...
}
```

### 2. Test MCP Endpoints

```bash
# Test MCP initialization
curl -X POST http://localhost:8000/mcp/initialize \
  -H "Content-Type: application/json" \
  -d '{"protocolVersion": "1.0", "clientInfo": {"name": "claude-code"}}'
```

### 3. Manually Add a Memory

```bash
# Save a test memory
retainr save examples/memory1.json

# Search for it
retainr recall "MCP server architecture"
```

### 4. Verify in Claude Code

Start a new Claude Code session and ask:

```
"Do you remember anything about the retainr project architecture?"
```

Claude should be able to recall information from stored memories.

## Troubleshooting

### Common Issues

1. **Server not accessible**
   ```bash
   # Check if server is running
   docker ps
   # or
   curl http://localhost:8000/health
   ```

2. **MCP registration failed**
   - Verify the MCP configuration file location
   - Check JSON syntax in configuration
   - Restart Claude Code after configuration changes

3. **Memory not persisting**
   - Check memory directory permissions
   - Verify ChromaDB is running
   - Check server logs: `make logs`

4. **Search not working**
   - Verify embeddings are generated
   - Check ChromaDB connectivity
   - Test search via CLI: `retainr recall "test query"`

### Debug Commands

```bash
# Check server status
retainr status

# View server logs
make logs

# Test memory operations
retainr save examples/memory1.json
retainr list
retainr recall "architecture"

# Check ChromaDB
make logs-chroma
```

## Advanced Configuration

### Custom Memory Directory

Configure a specific directory for memories:

```bash
# Set in .env file
RETAINR_MEMORY_DIR=/Users/username/Documents/claude-memories

# Or environment variable
export RETAINR_MEMORY_DIR="/Users/username/Documents/claude-memories"
```

### Multiple Projects

Use project-specific memory isolation:

```json
{
  "project": "web-app-frontend",
  "category": "implementation",
  "content": "Frontend uses React with TypeScript..."
}
```

```json
{
  "project": "web-app-backend", 
  "category": "implementation",
  "content": "Backend uses FastAPI with PostgreSQL..."
}
```

Search within specific projects:
```bash
retainr recall "database setup" --project web-app-backend
```

## Security Considerations

1. **Local Only**: retainr runs locally and doesn't send data to external services
2. **File Permissions**: Ensure memory directory has appropriate permissions
3. **Network Access**: Server only binds to localhost by default
4. **Sensitive Data**: Avoid storing secrets or sensitive information in memories

## Next Steps

1. Start using Claude Code with retainr enabled
2. Monitor memory accumulation in your configured directory
3. Periodically review and clean up outdated memories
4. Share memory directories between team members if desired

For more information, see:
- [Main README](../README.md) for server setup
- [Configuration Guide](./configuration.md) for advanced settings
- [Memory Format Template](../prompt-template.md) for memory structure