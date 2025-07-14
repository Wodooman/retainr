# Memory Format Template for Claude Code

This document describes how to format memory entries for the retainr MCP server.

## Memory JSON Schema

When creating a memory entry, use the following JSON structure:

```json
{
  "project": "project-name",
  "category": "architecture|implementation|debugging|documentation|other",
  "tags": ["tag1", "tag2", "tag3"],
  "references": ["file1.py", "docs/guide.md"],
  "content": "The actual memory content in markdown format",
  "outdated": false
}
```

### Field Descriptions

- **project**: The project/repository this memory relates to
- **category**: Type of knowledge (architecture, implementation, debugging, documentation, other)
- **tags**: Keywords for better searchability
- **references**: Related files or documentation
- **content**: The main memory content (supports markdown)
- **outdated**: Whether this memory is still valid

## Memory Block Format

When generating memories in conversations, wrap them with markers:

```
==BEGIN_MEMORY==
{
  "project": "retainr",
  "category": "architecture",
  "tags": ["mcp", "server", "fastapi"],
  "references": ["mcp-server/main.py", "Specs.md"],
  "content": "# MCP Server Architecture\n\nThe retainr MCP server uses FastAPI to provide endpoints for memory storage and retrieval. Key components:\n\n- **POST /memory**: Accepts JSON memory entries\n- **GET /memory/search**: Semantic search with query parameters\n- **PATCH /memory/{id}**: Mark memories as outdated\n\nMemories are stored as markdown files and indexed in Chroma for vector search.",
  "outdated": false
}
==END_MEMORY==
```

## Examples

### Architecture Decision Memory
```json
{
  "project": "myapp",
  "category": "architecture",
  "tags": ["database", "postgresql", "schema"],
  "references": ["src/models.py", "migrations/"],
  "content": "# Database Architecture Decision\n\nWe chose PostgreSQL for the following reasons:\n1. Strong ACID compliance\n2. JSON field support for flexible data\n3. Full-text search capabilities\n\nKey tables: users, sessions, memories",
  "outdated": false
}
```

### Implementation Detail Memory
```json
{
  "project": "myapp",
  "category": "implementation",
  "tags": ["authentication", "jwt", "security"],
  "references": ["src/auth.py", "src/middleware.py"],
  "content": "# JWT Authentication Implementation\n\nJWT tokens are generated with 24-hour expiry. Refresh tokens last 30 days. The secret key is stored in environment variable JWT_SECRET_KEY.",
  "outdated": false
}
```

### Debugging Solution Memory
```json
{
  "project": "myapp",
  "category": "debugging",
  "tags": ["performance", "database", "n+1"],
  "references": ["src/api/users.py"],
  "content": "# Fixed N+1 Query Issue\n\nThe user listing endpoint was making N+1 queries. Solution: Added .options(joinedload(User.profile)) to eagerly load related data.",
  "outdated": false
}
```

## Best Practices

1. **Be Specific**: Include concrete details, not general observations
2. **Add Context**: Explain why decisions were made
3. **Reference Files**: Always include relevant file paths
4. **Use Tags Wisely**: Think about how you'll search for this later
5. **Mark Outdated**: Update memories when implementations change
