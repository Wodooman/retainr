#!/bin/bash
set -e

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
    exit 1
}

# Main setup function
main() {
    echo -e "${BLUE}🚀 Setting up retainr MCP server...${NC}"
    echo

    # Check system requirements
    check_system_requirements

    # Install Python dependencies
    install_dependencies

    # Start ChromaDB service
    start_chromadb

    # Pre-download ML models
    download_models

    # Generate Claude Code configuration
    setup_claude_code

    echo
    log_success "Setup complete! 🎉"
    echo
    echo -e "${GREEN}Next steps:${NC}"
    echo "  1. Start MCP server: ${BLUE}make start-mcp${NC}"
    echo "  2. Or use development mode: ${BLUE}make dev${NC}"
    echo "  3. Claude Code should now be able to connect to retainr"
    echo
}

# Check system requirements
check_system_requirements() {
    log_info "Checking system requirements..."

    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
    fi

    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.10"

    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
        log_error "Python 3.10+ is required, but found Python $python_version"
    fi

    log_success "Python $python_version found"

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is required but not installed"
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is required but not installed"
    fi

    log_success "Docker and Docker Compose found"

    # Check pip
    if ! python3 -m pip --version &> /dev/null; then
        log_error "pip is required but not available"
    fi

    log_success "pip found"
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    python -m pip install --upgrade pip

    # Install dependencies
    if [ -f "requirements-native.txt" ]; then
        log_info "Installing native MCP server dependencies..."
        pip install -r requirements-native.txt
    else
        log_error "requirements-native.txt not found"
    fi

    log_success "Dependencies installed"
}

# Start ChromaDB service
start_chromadb() {
    log_info "Starting ChromaDB service..."

    if [ ! -f "docker-compose.yml" ]; then
        log_error "docker-compose.yml not found"
    fi

    # Stop any existing ChromaDB containers
    docker-compose down --remove-orphans 2>/dev/null || true

    # Start ChromaDB
    docker-compose up -d

    # Wait for ChromaDB to be ready
    log_info "Waiting for ChromaDB to be ready..."
    max_attempts=30
    attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8000/api/v2/heartbeat &>/dev/null; then
            break
        fi
        sleep 2
        attempt=$((attempt + 1))
        echo -n "."
    done
    echo

    if [ $attempt -eq $max_attempts ]; then
        log_error "ChromaDB failed to start within 60 seconds"
    fi

    log_success "ChromaDB is running"
}

# Download ML models
download_models() {
    log_info "Pre-downloading ML models..."

    # Activate virtual environment
    source venv/bin/activate

    # Download sentence-transformers model
    python3 -c "
import os
from sentence_transformers import SentenceTransformer
print('Downloading all-MiniLM-L6-v2 model...')
model = SentenceTransformer('all-MiniLM-L6-v2')
print('Model downloaded successfully!')
" || log_error "Failed to download ML models"

    log_success "ML models downloaded"
}

# Setup Claude Code configuration
setup_claude_code() {
    log_info "Setting up Claude Code configuration..."

    # Get absolute path to current directory
    current_dir=$(pwd)

    # Create Claude Code config
    cat > claude-mcp-config.json << EOF
{
  "servers": {
    "retainr": {
      "transport": {
        "type": "stdio",
        "command": "python",
        "args": ["-m", "mcp_server"],
        "cwd": "$current_dir",
        "env": {
          "PATH": "$current_dir/venv/bin:\$PATH"
        }
      },
      "description": "Persistent memory server for AI agents"
    }
  }
}
EOF

    # Create Claude Code config directory if it doesn't exist
    claude_config_dir="$HOME/.config/claude-code"
    mkdir -p "$claude_config_dir"

    # Copy configuration
    if [ -f "$claude_config_dir/mcp.json" ]; then
        log_warning "Existing Claude Code MCP configuration found"
        cp "$claude_config_dir/mcp.json" "$claude_config_dir/mcp.json.backup"
        log_info "Backed up existing configuration to mcp.json.backup"
    fi

    cp claude-mcp-config.json "$claude_config_dir/mcp.json"

    log_success "Claude Code configuration created at $claude_config_dir/mcp.json"
    log_info "Configuration saved locally as claude-mcp-config.json"
}

# Run main function
main "$@"
