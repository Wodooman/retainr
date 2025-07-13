# Troubleshooting Guide

This guide helps you resolve common issues with the retainr MCP server.

First, verify your server is running correctly:

```bash
# Check if containers are running
docker ps

# Test basic connectivity
curl http://localhost:8000/

# Check health status
curl http://localhost:8000/health
```

Expected responses:
- **Root**: `{"message":"retainr MCP Server","version":"0.1.0","status":"running"}`
- **Health**: Should show `"status":"healthy"` with ChromaDB stats

## 🚀 Quick Test Commands

```bash
# 1. Check server health
curl http://localhost:8000/health

# 2. Save a test memory
curl -X POST http://localhost:8000/memory/ \
  -H "Content-Type: application/json" \
  -d '{
    "project": "test-project",
    "category": "testing",
    "content": "# Test\nThis is a test memory.",
    "tags": ["test"]
  }'

# 3. Search for memories
curl "http://localhost:8000/memory/search?query=test&top=3"

# 4. Test MCP endpoints
curl -X POST http://localhost:8000/mcp/tools/list

# 5. Test CLI (from container)
docker exec retainr-server python -m cli.main status
docker exec retainr-server python -m cli.main recall "test"
```

## 🔧 Common Issues & Solutions

### Server Won't Start
1. **Check if containers are running**: `docker ps`
2. **Check logs**: `docker logs retainr-server`
3. **Restart containers**: `make down && make up`

### Can't Connect to Server
1. **Verify port mapping**: Should be `0.0.0.0:8000->8000/tcp`
2. **Test localhost**: `curl http://localhost:8000/`
3. **Check firewall**: Ensure port 8000 is accessible

### ChromaDB Issues
1. **Check ChromaDB container**: `docker logs retainr-chroma`
2. **Verify internal connection**: `docker exec retainr-server python -c "import chromadb; print('OK')"`
3. **Test ChromaDB directly**: `curl http://localhost:8001/`

### Memory Storage Issues
1. **Check directory permissions**: Memory files should be created in `./memory/`
2. **Verify volume mounts**: `docker inspect retainr-server`
3. **Test file creation**: Save a test memory and check filesystem

### CLI Issues
1. **Run from container**: `docker exec retainr-server python -m cli.main status`
2. **Install locally**: `pip install -r requirements.txt` then use `python -m cli.main`
3. **Check server connection**: CLI connects to `http://localhost:8000` by default

## 📊 Performance Notes

- **Startup time**: ~5-10 seconds (includes loading sentence-transformers model)
- **Memory indexing**: ~1-2 seconds per memory entry
- **Search latency**: ~100-500ms for semantic search
- **File storage**: Instant markdown file creation


## 📚 Additional Resources

- **Development**: See [docs/development.md](docs/development.md) for development workflows
- **Configuration**: See [docs/configuration.md](docs/configuration.md) for advanced settings  
- **Claude Code Integration**: See [docs/claude-code-integration.md](docs/claude-code-integration.md) for detailed setup