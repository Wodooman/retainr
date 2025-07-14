.PHONY: help build up down logs shell test clean dev

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build the Docker image
	docker-compose build

up: ## Start the server and ChromaDB
	docker-compose up -d

dev: ## Start the server in development mode with hot reload
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

prod: ## Start in production mode (no dev mounts)
	docker-compose -f docker-compose.prod.yml up -d

down: ## Stop all services
	docker-compose down

logs: ## Show server logs
	docker-compose logs -f retainr

logs-chroma: ## Show ChromaDB logs
	docker-compose logs -f chroma

logs-all: ## Show all service logs
	docker-compose logs -f

shell: ## Open a shell in the running container
	docker-compose exec retainr bash

test: ## Run all tests
	source test-env/bin/activate && pytest tests/ -v

test-unit: ## Run unit tests only
	source test-env/bin/activate && pytest tests/unit/ -v

test-integration: ## Run integration tests only
	source test-env/bin/activate && pytest tests/integration/ -v

test-cov: ## Run tests with coverage report
	source test-env/bin/activate && pytest tests/ -v --cov=mcp_server --cov=cli --cov-report=html --cov-report=term-missing

test-docker: ## Run tests in container
	docker-compose exec retainr pytest tests/ -v

clean: ## Clean up containers and images
	docker-compose down -v
	docker system prune -f

status: ## Show service status
	docker-compose ps

restart: ## Restart all services
	docker-compose restart

restart-server: ## Restart only the retainr server
	docker-compose restart retainr

restart-chroma: ## Restart only ChromaDB
	docker-compose restart chroma

install: ## Install dependencies locally
	pip install -r requirements.txt

install-dev: ## Install development dependencies locally
	pip install -r requirements-dev.txt

run-local: ## Run server locally (requires local Python setup)
	source test-env/bin/activate && python -m uvicorn mcp_server.main:app --reload

format: ## Format code
	source test-env/bin/activate && black .
	source test-env/bin/activate && ruff check --fix .

lint: ## Lint code (same as CI)
	source test-env/bin/activate && black --check --diff .
	source test-env/bin/activate && ruff check .
	source test-env/bin/activate && mypy mcp_server cli --ignore-missing-imports

pre-commit-install: ## Install pre-commit hooks
	source test-env/bin/activate && pre-commit install

pre-commit-run: ## Run pre-commit hooks on all files
	source test-env/bin/activate && pre-commit run --all-files

pre-commit-update: ## Update pre-commit hooks
	source test-env/bin/activate && pre-commit autoupdate

setup-claude-code: ## Setup Claude Code MCP integration
	./setup-claude-code.sh

setup-branch-protection: ## Setup GitHub branch protection rules (requires gh CLI)
	./scripts/setup-branch-protection.sh

test-mcp: ## Test MCP endpoints
	curl -X POST http://localhost:8000/mcp/initialize -H "Content-Type: application/json" -d '{"protocolVersion": "1.0", "clientInfo": {"name": "test"}}'
	curl http://localhost:8000/mcp/tools/list
