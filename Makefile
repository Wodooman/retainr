.PHONY: help test clean setup start-mcp start-chromadb venv venv-dev format lint

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ======================================================
# NATIVE MODE COMMANDS (Recommended)
# ======================================================

setup: ## Full setup: install deps + start ChromaDB + setup Claude Code
	./setup.sh

venv: ## Create and setup virtual environment with dependencies
	@if [ ! -d "venv" ]; then echo "🔧 Creating virtual environment..."; python3 -m venv venv; fi
	@echo "📦 Installing dependencies..."
	@source venv/bin/activate && pip install --upgrade pip --quiet
	@source venv/bin/activate && pip install -r requirements-native.txt --quiet
	@echo "✅ Virtual environment ready at ./venv/"

venv-dev: ## Setup virtual environment with dev dependencies
	@if [ ! -d "venv" ]; then echo "🔧 Creating virtual environment..."; python3 -m venv venv; fi
	@echo "📦 Installing dependencies..."
	@source venv/bin/activate && pip install --upgrade pip --quiet
	@source venv/bin/activate && pip install -r requirements-native.txt --quiet
	@source venv/bin/activate && pip install -r requirements-dev.txt --quiet
	@echo "✅ Development environment ready at ./venv/"

start-chromadb: ## Start ChromaDB service (Docker)
	docker-compose up -d

stop-chromadb: ## Stop ChromaDB service
	docker-compose down

restart-chromadb: ## Restart ChromaDB service
	docker-compose restart

chromadb-status: ## Show ChromaDB status
	docker-compose ps

start-mcp: ## Start native MCP server (requires setup)
	@if [ ! -d "venv" ]; then echo "❌ Virtual environment not found. Run 'make setup' first."; exit 1; fi
	@echo "🚀 Starting native MCP server..."
	source venv/bin/activate && python -m mcp_server

dev-native: ## Start native MCP server in development mode with auto-reload
	@if [ ! -d "venv" ]; then echo "❌ Virtual environment not found. Run 'make setup' first."; exit 1; fi
	@echo "🔄 Starting native MCP server in development mode..."
	source venv/bin/activate && python -m mcp_server --reload

test-mcp-native: ## Test native MCP server connectivity
	@if [ ! -d "venv" ]; then echo "❌ Virtual environment not found. Run 'make setup' first."; exit 1; fi
	source venv/bin/activate && python -c "from mcp_server.standard_mcp import mcp; print('✅ Native MCP server loads successfully')"

health-check: ## Check health of all services (ChromaDB + MCP server readiness)
	@echo "🔍 Checking ChromaDB..."
	@if curl -f http://localhost:8000/api/v2/heartbeat &>/dev/null; then echo "✅ ChromaDB is running"; else echo "❌ ChromaDB is not accessible"; fi
	@echo "🔍 Checking Python environment..."
	@if [ -d "venv" ]; then echo "✅ Virtual environment exists"; else echo "❌ Virtual environment not found"; fi
	@if [ -f "venv/bin/activate" ]; then source venv/bin/activate && python -c "import mcp" && echo "✅ MCP SDK available"; else echo "❌ MCP SDK not available"; fi

logs-chromadb: ## Show ChromaDB logs
	docker-compose logs -f

status: ## Show status of services
	@echo "📊 Native MCP Server Status:"
	@echo "  Virtual environment: $(if $(wildcard venv),✅ exists,❌ missing)"
	@echo "  ChromaDB service:"
	@docker-compose ps
	@echo "  Claude Code config: $(if $(wildcard ~/.config/claude-code/mcp.json),✅ exists,❌ missing)"



# ======================================================
# EFFICIENT TESTING COMMANDS
# ======================================================

# Fast tests for development (< 3 minutes)
test-fast: venv-dev ## Run fast tests (unit + setup validation + protocol)
	@echo "🚀 Running fast tests for development feedback..."
	source venv/bin/activate && pytest tests/unit/ tests/test_setup_validation.py tests/test_mcp_protocol.py -v --tb=short -m "not slow"

# PR-style testing (conditional integration)
test-pr: venv-dev start-chromadb ## Run PR-style tests (fast + conditional integration)
	@echo "🧪 Running PR-style test suite..."
	source venv/bin/activate && pytest tests/unit/ tests/test_setup_validation.py tests/test_mcp_protocol.py -v --tb=short -m "not slow"
	@echo "🔗 Running integration tests..."
	source venv/bin/activate && pytest tests/integration/ tests/test_e2e_workflow.py -v --tb=short -m "integration and not slow" --timeout=120

# Comprehensive regression (nightly-style)
test-comprehensive: venv-dev start-chromadb ## Run comprehensive regression tests
	@echo "🌙 Running comprehensive regression test suite..."
	source venv/bin/activate && pytest tests/integration/ tests/test_e2e_workflow.py -v --tb=short -m "integration and not slow" --timeout=120
	source venv/bin/activate && pytest tests/integration/test_error_recovery.py -v --tb=short --timeout=120
	source venv/bin/activate && pytest tests/integration/test_data_integrity.py -v --tb=short --timeout=120

# Performance testing (weekly-style)
test-performance: venv-dev start-chromadb ## Run performance and scalability tests
	@echo "🚀 Running performance tests..."
	source venv/bin/activate && pytest tests/performance/ -v --tb=short -m "performance and not slow" --timeout=300
	@echo "⏳ Running stability tests..."
	source venv/bin/activate && pytest tests/performance/ -v --tb=short -m "performance and slow" --timeout=600

# Security testing
test-security: venv-dev start-chromadb ## Run security and input validation tests
	@echo "🔒 Running security tests..."
	source venv/bin/activate && pytest tests/security/ -v --tb=short -m "security" --timeout=120

# Full regression (weekly comprehensive)
test-full: venv-dev start-chromadb ## Run complete test suite with coverage
	@echo "🧪 Running FULL regression test suite..."
	source venv/bin/activate && pytest tests/ -v --tb=short --cov=mcp_server --cov-report=html --cov-report=term-missing -m "not slow" --timeout=300 --maxfail=5
	@echo "⏳ Running slow tests..."
	source venv/bin/activate && pytest tests/ -v --tb=short -m "slow" --timeout=600 --maxfail=2

# Individual test categories
test-unit: venv-dev ## Run unit tests only
	source venv/bin/activate && pytest tests/unit/ -v --tb=short -m "unit"

test-integration: venv-dev start-chromadb ## Run integration tests only
	source venv/bin/activate && pytest tests/integration/ -v --tb=short -m "integration"

test-cov: venv-dev start-chromadb ## Run tests with coverage report
	source venv/bin/activate && pytest tests/ -v --cov=mcp_server --cov-report=html --cov-report=term-missing --timeout=120

# Legacy commands for compatibility
test: test-pr ## Run PR-style tests (default)


clean: ## Clean up Python cache and build artifacts
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov


format: venv-dev ## Format code
	source venv/bin/activate && black .
	source venv/bin/activate && ruff check --fix .

lint: venv-dev ## Lint code (same as CI)
	source venv/bin/activate && black --check --diff .
	source venv/bin/activate && ruff check .
	source venv/bin/activate && mypy mcp_server --ignore-missing-imports

pre-commit-install: venv-dev ## Install pre-commit hooks
	source venv/bin/activate && pre-commit install

pre-commit-run: venv-dev ## Run pre-commit hooks on all files
	source venv/bin/activate && pre-commit run --all-files

pre-commit-update: venv-dev ## Update pre-commit hooks
	source venv/bin/activate && pre-commit autoupdate

setup-branch-protection: ## Setup GitHub branch protection rules (requires gh CLI)
	./scripts/setup-branch-protection.sh


test-mcp-protocol: venv-dev ## Run MCP protocol compliance tests
	source venv/bin/activate && pytest tests/test_mcp_protocol.py -v

test-e2e: venv-dev ## Run end-to-end workflow tests
	source venv/bin/activate && pytest tests/test_e2e_workflow.py -v

test-setup: venv-dev ## Run setup validation tests
	source venv/bin/activate && pytest tests/test_setup_validation.py -v
