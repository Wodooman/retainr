# MCP Architecture: Standard Claude Code ↔ MCP Server Communication

## Overview

This document describes the optimal, standards-compliant communication architecture between Claude Code and an MCP (Model Context Protocol) Server following official MCP specifications.

## Architecture Overview

```
┌─────────────────┐    stdio     ┌─────────────────┐              ┌─────────────────┐
│   Claude Code   │ ──────────► │ MCP Server      │ ◄────────────► │ Application     │
│   (MCP Client)  │             │ (Persistent)    │                │ Services        │
└─────────────────┘             └─────────────────┘              └─────────────────┘
        │                               │                                   │
        │                               │                                   ▼
        │                               │                         ┌─────────────────┐
        │                               │                         │ Memory Storage  │
        │                               │                         │ Vector Database │
        │                               │                         │ ML Models       │
        │                               │                         └─────────────────┘
        │                               │
        ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           JSON-RPC 2.0 Protocol Layer                              │
│                                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Initialize    │  │   Tools         │  │   Resources     │  │   Notifications │ │
│  │   Capabilities  │  │   Management    │  │   Access        │  │   Lifecycle     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. **MCP Client (Claude Code)**

**Role**: AI assistant that connects to MCP servers to access external functionality

**Configuration**:
```json
{
  "servers": {
    "retainr": {
      "transport": {
        "type": "stdio",
        "command": "./mcp_server",
        "args": [],
        "cwd": "${PWD}"
      }
    }
  }
}
```

**Responsibilities**:
- Establish stdio connection to MCP server
- Send JSON-RPC 2.0 requests
- Handle server responses and errors
- Manage session lifecycle

### 2. **MCP Server (retainr)**

**Role**: Long-running service that provides memory management capabilities to AI agents

**Architecture**:
- **Process Model**: Single persistent process
- **Transport**: stdio (standard input/output)
- **Protocol**: JSON-RPC 2.0
- **Lifecycle**: Starts once, serves multiple requests

### 3. **Application Services**

**Memory Storage**:
- File-based markdown storage with YAML frontmatter
- Project-based organization
- Atomic file operations

**Vector Database (ChromaDB)**:
- Semantic search capabilities
- Embedding generation and storage
- Collection management

**ML Models**:
- Pre-loaded sentence-transformers models
- Cached embeddings for fast retrieval
- Optimized for batch processing

## Communication Protocol

### Session Initialization

```sequence
Claude Code -> MCP Server: initialize request
MCP Server -> Claude Code: capabilities + server info
Claude Code -> MCP Server: notifications/initialized
MCP Server: ready for tool/resource calls
```

### Tool Execution Flow

```sequence
Claude Code -> MCP Server: tools/list request
MCP Server -> Claude Code: available tools list
Claude Code -> MCP Server: tools/call request
MCP Server -> Claude Code: tool execution result
```

### Resource Access Flow

```sequence
Claude Code -> MCP Server: resources/list request
MCP Server -> Claude Code: available resources list
Claude Code -> MCP Server: resources/read request
MCP Server -> Claude Code: resource content
```

## Server Capabilities

### Available Tools

1. **save_memory** - Store new memories with semantic indexing
2. **search_memories** - Semantic search across stored memories  
3. **list_memories** - List recent memories with filtering
4. **update_memory** - Modify memory metadata

### Available Resources

1. **Memory Content Access** - Direct access via `memory://{id}` URIs

## Performance Characteristics

### Process Model

```
┌─────────────────┐
│ Server Startup  │  Initial: ~3-5 seconds (one-time cost)
│ Model Loading   │  • Load sentence-transformers
│ Cache warming   │  • Connect to ChromaDB
└─────────────────┘  • Initialize storage

┌─────────────────┐
│ Request Serving │  Ongoing: ~50-200ms per request
│ Fast Responses  │  • Models pre-loaded
│ Cached Data     │  • Vector cache warm
└─────────────────┘  • Connection pooling
```

### Scalability Model

**Memory Usage**: ~600-1300MB per process
**Concurrency**: Single-threaded stdio transport with async I/O
**Resource Management**: Automatic garbage collection and cache management

## Deployment Architecture

### Development Environment
- Docker containerized services via `make up`
- MCP server as persistent process
- Claude Code connects via stdio transport

### Production Environment  
- Docker containerized deployment
- MCP server as system service
- Load balancer for multiple instances (if needed)

## Error Handling

### Error Types
- **JSON-RPC Errors**: Standard protocol error codes for malformed requests
- **Application Errors**: Business logic errors returned as tool results with `isError: true`

## Security Model

### Transport Security
- **stdio**: Local process communication (inherently secure)
- **No network exposure**: Server not accessible remotely  
- **Process isolation**: Container environment

### Data Security
- **Local storage**: All data stored locally
- **No external APIs**: Self-contained system
- **User control**: Complete data ownership

## Standards Compliance

### MCP Protocol Compliance
✅ **JSON-RPC 2.0**: All messages follow specification  
✅ **stdio Transport**: Standard input/output communication  
✅ **Capability Negotiation**: Proper initialization sequence  
✅ **Error Handling**: Standard error codes and messages  
✅ **Tool Schema**: JSON Schema validation for tool parameters  
✅ **Resource URIs**: Proper URI-based resource addressing  

This architecture provides a standards-compliant MCP server implementation for production use with Claude Code and other MCP clients.
