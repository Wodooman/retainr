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



test: venv-dev ## Run all tests
	source venv/bin/activate && pytest tests/ -v

test-unit: venv-dev ## Run unit tests only
	source venv/bin/activate && pytest tests/unit/ -v

test-integration: venv-dev ## Run integration tests only
	source venv/bin/activate && pytest tests/integration/ -v

test-cov: venv-dev ## Run tests with coverage report
	source venv/bin/activate && pytest tests/ -v --cov=mcp_server --cov-report=html --cov-report=term-missing


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
