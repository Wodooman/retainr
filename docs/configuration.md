# Configuration Guide

## Memory Storage Configuration

The retainr server allows you to configure a custom path for storing memories as browsable markdown files. The vector database remains internal for performance and simplicity. This is useful for:

- Storing memories in a specific location (e.g., Documents folder)
- Sharing memories between different projects
- Backing up memories to cloud storage
- Browsing memory files with your favorite text editor

## Configuration Methods

### 1. Environment Variables

Set environment variables with the `RETAINR_` prefix:

```bash
export RETAINR_MEMORY_DIR="/Users/username/Documents/ai-memories"
```

### 2. .env File

Create a `.env` file in the project root:

```env
# Copy from .env.example and customize
RETAINR_MEMORY_DIR=/Users/username/Documents/ai-memories
```

### 3. Docker Environment

For Docker deployments, you can:

**Option A: Use .env file**
```bash
# Create .env file with your paths
cp .env.example .env
# Edit .env with your preferred paths
docker-compose up
```

**Option B: Set environment variables**
```bash
RETAINR_MEMORY_DIR=/path/to/memories docker-compose up
```

**Option C: Override docker-compose.yml**
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  retainr:
    volumes:
      - /Users/username/Documents/memories:/app/memory
```

## Memory File Structure

When you configure a custom memory directory, memories are stored as markdown files with this structure:

```
memory/
├── project1/
│   ├── 2024-01-15T10-30-00-architecture-database-design.md
│   ├── 2024-01-15T11-15-00-implementation-auth-system.md
│   └── 2024-01-16T09-20-00-debugging-performance-issue.md
├── project2/
│   └── 2024-01-16T14-45-00-documentation-api-guide.md
└── shared/
    └── 2024-01-14T16-00-00-other-coding-patterns.md
```

Each markdown file contains:
- YAML frontmatter with metadata (project, category, tags, etc.)
- Markdown content with the actual memory

## Browsing and Editing Memories

Since memories are stored as standard markdown files, you can:

1. **Browse with file explorer** - Navigate to your memory directory
2. **Edit with any text editor** - VSCode, Sublime, Vim, etc.
3. **Search with system tools** - Spotlight, grep, ripgrep
4. **Version control** - Git track your memory directory
5. **Sync to cloud** - Dropbox, iCloud, Google Drive

## Example Configurations

### Personal Knowledge Base
```env
RETAINR_MEMORY_DIR=/Users/username/Documents/Knowledge/AI-Memories
```

### Project-Specific Memories
```env
RETAINR_MEMORY_DIR=/Users/username/Projects/myapp/docs/memories
```

### Shared Team Memories (with Git)
```env
RETAINR_MEMORY_DIR=/Users/username/team-knowledge/memories
```

## Path Requirements

- Memory path can be absolute (`/Users/username/memories`) or relative (`./memories`)
- Directory will be created automatically if it doesn't exist
- The server needs read/write permissions to the memory directory
- Vector database remains internal to the application for optimal performance
- For Docker, ensure the memory path is accessible to the container

## Security Considerations

- Don't store sensitive information in memory files
- Be cautious when sharing memory directories
- Consider file permissions for shared environments
- Regular backups are recommended for important memories