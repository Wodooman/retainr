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

# Main registration function
main() {
    echo -e "${BLUE}🔗 Registering retainr with Claude Code...${NC}"
    echo

    # Check if virtual environment exists
    if [ ! -d "venv" ]; then
        log_error "Virtual environment not found. Run 'make setup' first."
    fi

    # Get absolute path to current directory
    current_dir=$(pwd)

    # Check if virtual environment has necessary packages
    if ! source venv/bin/activate && python -c "import mcp" &>/dev/null; then
        log_warning "MCP SDK not found in virtual environment"
        log_info "Installing missing dependencies..."
        source venv/bin/activate && pip install -r requirements-native.txt
    fi

    log_info "Creating Claude Code MCP configuration..."

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

    log_success "Configuration generated: claude-mcp-config.json"

    # Create Claude Code config directory if it doesn't exist
    claude_config_dir="$HOME/.config/claude-code"
    mkdir -p "$claude_config_dir"

    # Backup existing configuration if it exists
    if [ -f "$claude_config_dir/mcp.json" ]; then
        backup_file="$claude_config_dir/mcp.json.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$claude_config_dir/mcp.json" "$backup_file"
        log_warning "Existing configuration backed up to: $backup_file"

        # Check if retainr is already configured
        if grep -q '"retainr"' "$claude_config_dir/mcp.json" 2>/dev/null; then
            log_info "Merging with existing configuration..."
            # Create a merged configuration (simple approach - replace retainr entry)
            python3 -c "
import json
import sys

try:
    with open('$claude_config_dir/mcp.json', 'r') as f:
        existing = json.load(f)

    with open('claude-mcp-config.json', 'r') as f:
        new_config = json.load(f)

    # Merge configurations
    if 'servers' not in existing:
        existing['servers'] = {}

    existing['servers']['retainr'] = new_config['servers']['retainr']

    with open('$claude_config_dir/mcp.json', 'w') as f:
        json.dump(existing, f, indent=2)

    print('Configuration merged successfully')
except Exception as e:
    print(f'Error merging configuration: {e}', file=sys.stderr)
    sys.exit(1)
"
        else
            log_info "Adding retainr to existing configuration..."
            # Add retainr to existing config
            cp claude-mcp-config.json "$claude_config_dir/mcp.json"
        fi
    else
        log_info "Creating new Claude Code configuration..."
        cp claude-mcp-config.json "$claude_config_dir/mcp.json"
    fi

    log_success "Claude Code configuration updated at: $claude_config_dir/mcp.json"

    # Validate configuration
    log_info "Validating configuration..."
    if python3 -c "import json; json.load(open('$claude_config_dir/mcp.json'))" 2>/dev/null; then
        log_success "Configuration is valid JSON"
    else
        log_error "Configuration is invalid JSON"
    fi

    # Test MCP server accessibility
    log_info "Testing MCP server availability..."
    if source venv/bin/activate && timeout 5 python -c "from mcp_server.standard_mcp import mcp; print('✅ MCP server accessible')" 2>/dev/null; then
        log_success "MCP server is accessible"
    else
        log_warning "MCP server test failed - but configuration is still valid"
    fi

    echo
    log_success "Registration complete! 🎉"
    echo
    echo -e "${GREEN}Next steps:${NC}"
    echo "  1. Restart Claude Code to load the new configuration"
    echo "  2. Start ChromaDB service: ${BLUE}make start-chromadb${NC}"
    echo "  3. Start MCP server: ${BLUE}make start-mcp${NC}"
    echo "  4. Claude Code should now be able to connect to retainr"
    echo
    echo -e "${BLUE}Configuration file locations:${NC}"
    echo "  Local copy: $(pwd)/claude-mcp-config.json"
    echo "  Claude Code: $claude_config_dir/mcp.json"
    echo
}

# Run main function
main "$@"
