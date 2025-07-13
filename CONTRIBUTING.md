# Contributing to retainr

Thank you for your interest in contributing to retainr! This guide will help you get started with contributing to the project.

## 🚀 Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Set up the development environment**
4. **Make your changes**
5. **Test your changes**
6. **Submit a pull request**

## 🛠️ Development Setup

### Prerequisites
- Python 3.9 or higher
- Docker and Docker Compose
- Git

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/retainr.git
cd retainr

# Set up development environment
make install-dev

# Start the development server
make dev

# Run tests
make test

# Format and lint code
make format
make lint
```

## 📝 How to Contribute

### Reporting Bugs

Before creating a bug report, please check if the issue already exists in the [GitHub Issues](https://github.com/Wodooman/retainr/issues).

When creating a bug report, please include:
- **Clear description** of the issue
- **Steps to reproduce** the behavior
- **Expected behavior**
- **Actual behavior**
- **Environment details** (OS, Python version, Docker version)
- **Logs or error messages**

### Suggesting Features

Feature requests are welcome! Please:
- Check if the feature has already been requested
- Clearly describe the feature and its use case
- Explain why this feature would be useful
- Consider offering to implement it yourself

### Code Contributions

We welcome code contributions! Here's how to submit them:

#### 1. Choose an Issue
- Look for issues labeled `good first issue` for beginners
- Comment on the issue to let others know you're working on it
- Ask questions if you need clarification

#### 2. Create a Branch
```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/issue-description
```

#### 3. Make Your Changes
- Write clean, readable code
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

#### 4. Test Your Changes
```bash
# Run the full test suite
make test

# Test manually with Docker
make dev
# Test the functionality in another terminal

# Format and lint
make format
make lint
```

#### 5. Commit Your Changes
```bash
# Use conventional commit format
git commit -m "feat: add new memory search filters"
git commit -m "fix: resolve ChromaDB connection timeout"
git commit -m "docs: update installation instructions"
```

#### 6. Submit a Pull Request
- Push your branch to your fork
- Create a pull request from your branch to `main`
- Fill out the pull request template
- Link to any related issues

## 🎨 Code Style

### Python Code Style
- **Formatter**: Black (line length: 88)
- **Linter**: Ruff with default configuration
- **Type hints**: Required for all functions
- **Imports**: Organized with isort
- **Docstrings**: Google-style format

### Example
```python
def save_memory(entry: MemoryEntry, storage_path: Path) -> tuple[str, Path]:
    """Save a memory entry to file storage.
    
    Args:
        entry: The memory entry to save
        storage_path: Directory to save the memory file
        
    Returns:
        Tuple of (memory_id, file_path)
        
    Raises:
        ValueError: If entry validation fails
        IOError: If file cannot be written
    """
    # Implementation here
    pass
```

### Commit Message Format
We use [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (no logic changes)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(api): add memory filtering by date range
fix(storage): handle file permission errors gracefully
docs(readme): update installation instructions
test(embeddings): add unit tests for similarity search
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_storage.py

# Run with coverage
pytest --cov=mcp_server --cov=cli

# Run integration tests
pytest tests/integration/
```

### Writing Tests
- Write tests for all new functionality
- Aim for good test coverage (>80%)
- Use descriptive test names
- Include both positive and negative test cases

### Test Structure
```python
def test_save_memory_creates_file():
    """Test that saving a memory creates the expected markdown file."""
    # Arrange
    entry = MemoryEntry(project="test", category="testing", content="Test content")
    
    # Act
    memory_id, file_path = storage.save_memory(entry)
    
    # Assert
    assert file_path.exists()
    assert memory_id is not None
```

## 📚 Documentation

### Documentation Updates
When making changes, please update relevant documentation:
- **Code comments** for complex logic
- **Docstrings** for all functions and classes
- **README.md** for user-facing changes
- **API documentation** for endpoint changes
- **Configuration docs** for new settings

### Documentation Style
- Use clear, concise language
- Include code examples where helpful
- Keep documentation up-to-date with code changes
- Use markdown formatting consistently

## 🔍 Code Review Process

### Review Criteria
Pull requests are reviewed for:
- **Functionality**: Does it work as intended?
- **Code quality**: Is it readable and maintainable?
- **Testing**: Are there adequate tests?
- **Documentation**: Is documentation updated?
- **Performance**: Are there any performance concerns?
- **Security**: Are there any security implications?

### Review Timeline
- Initial review within 3-5 business days
- Follow-up reviews within 1-2 business days
- Urgent fixes reviewed within 24 hours

## 🤝 Community Guidelines

### Be Respectful
- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Focus on what's best for the community
- Show empathy towards other community members

### Communication Channels
- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community discussions
- **Pull Requests**: Code review and collaboration

## 🎯 Development Focus Areas

We're especially looking for contributions in these areas:

### High Priority
- **Test coverage**: Unit and integration tests
- **Documentation**: Usage examples and tutorials
- **Error handling**: Better error messages and recovery
- **Performance**: Optimization and benchmarking

### Medium Priority
- **CLI improvements**: Better user experience
- **Configuration**: More flexible setup options
- **Integrations**: Support for more AI tools
- **Examples**: Real-world use cases

### Future Considerations
- **Analytics**: Usage tracking and metrics
- **Scaling**: Multi-user and enterprise features
- **Plugins**: Extensibility framework
- **Monitoring**: Health checks and observability

## 📞 Getting Help

### Questions?
- Check the [documentation](docs/)
- Search [existing issues](https://github.com/Wodooman/retainr/issues)
- Ask in [GitHub Discussions](https://github.com/Wodooman/retainr/discussions)

### Stuck?
- Comment on the issue you're working on
- Reach out to maintainers for guidance
- Don't hesitate to ask for help!

## 🏆 Recognition

Contributors are recognized in:
- **CHANGELOG.md** for notable contributions
- **README.md** contributors section
- **GitHub releases** acknowledgments

Thank you for contributing to retainr! 🚀
