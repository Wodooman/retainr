#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Health check functions
check_python_version() {
    log_info "Checking Python version..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        return 1
    fi

    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")

    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
        log_error "Python 3.10+ is required, but found Python $python_version"
        return 1
    fi

    log_success "Python $python_version"
    return 0
}

check_docker() {
    log_info "Checking Docker..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        return 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        return 1
    fi

    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"
        return 1
    fi

    log_success "Docker and Docker Compose are available"
    return 0
}

check_virtual_environment() {
    log_info "Checking virtual environment..."

    if [ ! -d "venv" ]; then
        log_error "Virtual environment not found"
        return 1
    fi

    if [ ! -f "venv/bin/activate" ]; then
        log_error "Virtual environment is corrupted"
        return 1
    fi

    log_success "Virtual environment exists"
    return 0
}

check_mcp_dependencies() {
    log_info "Checking MCP dependencies..."

    if ! check_virtual_environment; then
        return 1
    fi

    if ! source venv/bin/activate && python -c "import mcp" &>/dev/null; then
        log_error "MCP SDK not available in virtual environment"
        return 1
    fi

    if ! source venv/bin/activate && python -c "import sentence_transformers" &>/dev/null; then
        log_error "sentence-transformers not available"
        return 1
    fi

    if ! source venv/bin/activate && python -c "import chromadb" &>/dev/null; then
        log_error "ChromaDB client not available"
        return 1
    fi

    log_success "All MCP dependencies are available"
    return 0
}

check_chromadb_service() {
    log_info "Checking ChromaDB service..."

    # Check if ChromaDB container is running
    if ! docker-compose -f docker-compose.chromadb.yml ps | grep -q "Up"; then
        log_error "ChromaDB container is not running"
        return 1
    fi

    # Check if ChromaDB is responding
    if ! curl -f http://localhost:8000/api/v1/heartbeat &>/dev/null; then
        log_error "ChromaDB is not responding on port 8000"
        return 1
    fi

    log_success "ChromaDB service is running and accessible"
    return 0
}

check_mcp_server() {
    log_info "Checking MCP server..."

    if ! check_virtual_environment || ! check_mcp_dependencies; then
        return 1
    fi

    # Test MCP server import
    if ! source venv/bin/activate && timeout 10 python -c "from mcp_server.standard_mcp import mcp; print('MCP server loads successfully')" &>/dev/null; then
        log_error "MCP server cannot be loaded"
        return 1
    fi

    log_success "MCP server is ready"
    return 0
}

check_claude_code_config() {
    log_info "Checking Claude Code configuration..."

    claude_config_file="$HOME/.config/claude-code/mcp.json"

    if [ ! -f "$claude_config_file" ]; then
        log_error "Claude Code MCP configuration not found"
        return 1
    fi

    if ! python3 -c "import json; json.load(open('$claude_config_file'))" 2>/dev/null; then
        log_error "Claude Code configuration is invalid JSON"
        return 1
    fi

    if ! grep -q '"retainr"' "$claude_config_file" 2>/dev/null; then
        log_error "retainr not found in Claude Code configuration"
        return 1
    fi

    log_success "Claude Code configuration is valid"
    return 0
}

check_model_cache() {
    log_info "Checking model cache..."

    model_cache_dir="$HOME/.cache/huggingface/transformers"

    if [ ! -d "$model_cache_dir" ]; then
        log_warning "Model cache directory not found - models will be downloaded on first use"
        return 0
    fi

    # Check if the specific model exists
    if find "$model_cache_dir" -name "*all-MiniLM-L6-v2*" | grep -q .; then
        log_success "Model cache exists (all-MiniLM-L6-v2 found)"
    else
        log_warning "Model not in cache - will be downloaded on first use"
    fi

    return 0
}

# Auto-recovery functions
auto_fix_virtual_environment() {
    log_info "Attempting to fix virtual environment..."

    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi

    log_info "Installing/updating dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements-native.txt

    log_success "Virtual environment fixed"
}

auto_fix_chromadb() {
    log_info "Attempting to fix ChromaDB service..."

    log_info "Stopping ChromaDB..."
    docker-compose -f docker-compose.chromadb.yml down --remove-orphans 2>/dev/null || true

    log_info "Starting ChromaDB..."
    docker-compose -f docker-compose.chromadb.yml up -d

    log_info "Waiting for ChromaDB to be ready..."
    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8000/api/v1/heartbeat &>/dev/null; then
            log_success "ChromaDB fixed and running"
            return 0
        fi
        sleep 2
        attempt=$((attempt + 1))
        echo -n "."
    done
    echo

    log_error "Failed to start ChromaDB after 60 seconds"
    return 1
}

auto_fix_claude_code_config() {
    log_info "Attempting to fix Claude Code configuration..."

    ./register-claude-code.sh

    if check_claude_code_config; then
        log_success "Claude Code configuration fixed"
        return 0
    else
        log_error "Failed to fix Claude Code configuration"
        return 1
    fi
}

# Main health check function
main() {
    local fix_mode=false
    local failed_checks=()

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --fix)
                fix_mode=true
                shift
                ;;
            *)
                echo "Usage: $0 [--fix]"
                echo "  --fix: Attempt to automatically fix issues"
                exit 1
                ;;
        esac
    done

    echo -e "${BLUE}🔍 Running retainr health check...${NC}"
    echo

    # Run all health checks
    checks=(
        "check_python_version"
        "check_docker"
        "check_virtual_environment"
        "check_mcp_dependencies"
        "check_chromadb_service"
        "check_mcp_server"
        "check_claude_code_config"
        "check_model_cache"
    )

    for check in "${checks[@]}"; do
        if ! $check; then
            failed_checks+=("$check")
        fi
        echo
    done

    # Summary
    if [ ${#failed_checks[@]} -eq 0 ]; then
        echo -e "${GREEN}🎉 All health checks passed!${NC}"
        echo -e "${GREEN}retainr is ready to use.${NC}"
        return 0
    else
        echo -e "${RED}❌ ${#failed_checks[@]} health check(s) failed:${NC}"
        for check in "${failed_checks[@]}"; do
            echo -e "  ${RED}• $check${NC}"
        done
        echo

        if [ "$fix_mode" = true ]; then
            echo -e "${YELLOW}🔧 Attempting to fix issues...${NC}"
            echo

            for check in "${failed_checks[@]}"; do
                case $check in
                    "check_virtual_environment"|"check_mcp_dependencies")
                        auto_fix_virtual_environment
                        ;;
                    "check_chromadb_service")
                        auto_fix_chromadb
                        ;;
                    "check_claude_code_config")
                        auto_fix_claude_code_config
                        ;;
                    *)
                        log_warning "No auto-fix available for $check"
                        ;;
                esac
                echo
            done

            echo -e "${BLUE}Re-running health checks...${NC}"
            echo
            main # Re-run without --fix to avoid infinite loop
        else
            echo -e "${YELLOW}Run with --fix to attempt automatic repairs:${NC}"
            echo -e "  ${BLUE}./health-check.sh --fix${NC}"
        fi

        return 1
    fi
}

# Run main function
main "$@"
