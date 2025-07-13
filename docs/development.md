# Development Guide

This guide covers development workflows, debugging, and contribution guidelines for retainr.

## 🛠️ Development Setup

### Local Development

```bash
# Clone and setup
git clone https://github.com/Wodooman/retainr.git
cd retainr

# Install dependencies
pip install -r requirements-dev.txt

# Run locally (requires ChromaDB separately)
python -m uvicorn mcp_server.main:app --reload
```

### Docker Development

```bash
# Development mode with hot reload
make dev

# View real-time logs
make logs

# Restart specific services
make restart-server
make restart-chroma

# Rebuild after code changes
make down && make build && make up
```

## 🧪 Testing

### Manual Testing

```bash
# Test all MCP endpoints
make test-mcp

# Test basic functionality
curl http://localhost:8000/health

# Save test memory
curl -X POST http://localhost:8000/memory/ \
  -H "Content-Type: application/json" \
  -d '{
    "project": "test",
    "category": "testing", 
    "content": "Test memory",
    "tags": ["test"]
  }'

# Search memories
curl "http://localhost:8000/memory/search?query=test"
```

### CLI Testing

```bash
# From container
docker exec retainr-server python -m cli.main status
docker exec retainr-server python -m cli.main recall "test query"

# Local CLI (after pip install)
python -m cli.main status --server http://localhost:8000
```

## 📁 Project Structure

```
retainr/
├── mcp_server/           # FastAPI backend
│   ├── main.py          # Application entry point
│   ├── config.py        # Configuration management
│   ├── models.py        # Pydantic data models
│   ├── storage.py       # File-based memory storage
│   ├── embeddings.py    # ChromaDB & vector operations
│   ├── api.py           # REST API endpoints
│   └── mcp.py           # MCP protocol implementation
├── cli/                 # Command-line interface
│   └── main.py          # Click CLI application
├── docs/                # Documentation
├── examples/            # Example memory files
├── memory/              # Memory storage (gitignored)
├── chroma/              # Vector database (gitignored)
└── tests/               # Test files (future)
```

## 🔧 Development Commands

### Docker Management

```bash
make help              # Show all available commands
make up                # Start all services
make down              # Stop all services
make build             # Build images
make clean             # Clean up containers and volumes
make status            # Show service status
```

### Code Quality

```bash
make format            # Format code with Black
make lint              # Lint with Ruff and MyPy
make install-dev       # Install dev dependencies
```

### Debugging

```bash
# Check container processes
docker exec retainr-server ps aux

# Interactive shell
docker exec -it retainr-server bash

# Test Python imports
docker exec retainr-server python -c "from mcp_server.config import settings; print('OK')"

# Test ChromaDB connection
docker exec retainr-server python -c "import chromadb; client = chromadb.HttpClient(host='chroma', port=8000); print(client.heartbeat())"
```

## 📊 Performance Monitoring

### Server Metrics

```bash
# Check memory usage
docker stats retainr-server retainr-chroma

# View server logs with timestamps
docker logs retainr-server -t

# Monitor ChromaDB logs
make logs-chroma
```

### Performance Notes

- **Startup time**: 5-10 seconds (sentence-transformers model loading)
- **Memory indexing**: 1-2 seconds per entry
- **Search latency**: 100-500ms for semantic search
- **File I/O**: Instant markdown creation

## 🐛 Common Development Issues

### Import Errors
- Ensure all dependencies in requirements.txt
- Check Python path in container vs local
- Verify module structure with __init__.py files

### Container Issues
- **Port conflicts**: Check if port 8000/8001 already in use
- **Volume mounts**: Verify paths in docker-compose.yml
- **Networking**: Ensure containers can communicate

### ChromaDB Issues
- **Version compatibility**: ChromaDB client/server versions
- **Collection access**: Permissions and initialization
- **Memory usage**: ChromaDB can be memory-intensive

### Development Workflow
```bash
# Typical development cycle
1. make down                    # Stop services
2. # Edit code
3. make build                   # Rebuild if needed
4. make dev                     # Start with hot reload
5. # Test changes
6. make format && make lint     # Code quality
7. git commit                   # Commit changes
```

## 📝 Contributing

### Code Style
- **Python**: Follow PEP 8, use Black for formatting
- **Imports**: Use absolute imports, organize with isort
- **Type hints**: Use type annotations for all functions
- **Docstrings**: Use Google-style docstrings

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/new-functionality

# Make changes, test locally
make dev
make test-mcp

# Format and lint
make format
make lint

# Commit with descriptive message
git commit -m "Add new functionality for X"

# Push and create PR
git push origin feature/new-functionality
```

**Note**: Memory files and ChromaDB data are automatically ignored by `.gitignore`. If you change the memory directory location, make sure it's also excluded from version control.

### Adding New Features

1. **Models**: Add Pydantic models in `models.py`
2. **Storage**: Extend storage logic in `storage.py`
3. **API**: Add REST endpoints in `api.py`
4. **MCP**: Add MCP tools in `mcp.py`
5. **CLI**: Add CLI commands in `cli/main.py`
6. **Tests**: Add test coverage
7. **Docs**: Update documentation

### Environment Variables

```bash
# Development overrides
export RETAINR_DEBUG=true
export RETAINR_MEMORY_DIR=./dev-memory
export RETAINR_CHROMA_HOST=localhost
export RETAINR_CHROMA_PORT=8001
```

### Database Management

```bash
# Reset ChromaDB (loses all vectors)
docker volume rm retainr_retainr_chroma_data
make up

# Backup memory files
tar -czf memory-backup.tar.gz memory/

# Restore memory files
tar -xzf memory-backup.tar.gz
```

## 🔍 Debugging Tips

### Memory Storage Issues
```bash
# Check file permissions
ls -la memory/

# Verify frontmatter parsing
docker exec retainr-server python -c "
import frontmatter
with open('/app/memory/project/file.md') as f:
    post = frontmatter.load(f)
    print(post.metadata)
"
```

### Vector Search Issues
```bash
# Test embeddings directly
docker exec retainr-server python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode('test query')
print(f'Embedding shape: {embedding.shape}')
"
```

### API Debugging
```bash
# Enable FastAPI debug mode
export RETAINR_DEBUG=true

# Use httpie for better API testing
pip install httpie
http POST localhost:8000/memory/ project=test category=debug content="Debug test"
```

## 🏗️ Architecture Decisions

### Why These Technologies?

- **FastAPI**: Modern, fast, automatic API docs
- **ChromaDB**: Purpose-built for vector storage
- **Sentence Transformers**: State-of-the-art embeddings
- **Markdown + YAML**: Human-readable, version-controllable
- **Docker**: Consistent development/deployment environment
- **Click + Rich**: Beautiful CLI experience

### Design Principles

1. **User-friendly**: Browsable markdown files
2. **Developer-friendly**: Clear APIs and good docs
3. **Performant**: Fast search and indexing
4. **Extensible**: Modular architecture
5. **Reliable**: Error handling and logging