#!/bin/bash

# Setup script for retainr + Claude Code integration

set -e

echo "🧠 Setting up retainr for Claude Code integration..."

# Check if Claude Code config directory exists
CLAUDE_CONFIG_DIR="$HOME/.config/claude-code"
MCP_CONFIG_FILE="$CLAUDE_CONFIG_DIR/mcp.json"

echo "📁 Checking Claude Code configuration directory..."

if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo "📂 Creating Claude Code config directory: $CLAUDE_CONFIG_DIR"
    mkdir -p "$CLAUDE_CONFIG_DIR"
fi

echo "📋 Installing MCP configuration..."

# Check if mcp.json already exists
if [ -f "$MCP_CONFIG_FILE" ]; then
    echo "⚠️  MCP configuration already exists at $MCP_CONFIG_FILE"
    echo "📄 Creating backup..."
    cp "$MCP_CONFIG_FILE" "$MCP_CONFIG_FILE.backup.$(date +%s)"
    echo "✅ Backup created: $MCP_CONFIG_FILE.backup.$(date +%s)"
fi

# Copy MCP configuration
cp claude-code-mcp.json "$MCP_CONFIG_FILE"
echo "✅ MCP configuration installed: $MCP_CONFIG_FILE"

# Check if server is running
echo "🔍 Checking if retainr server is running..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ retainr server is running at http://localhost:8000"
    
    # Test MCP endpoints
    echo "🧪 Testing MCP endpoints..."
    if curl -s http://localhost:8000/mcp/tools/list > /dev/null; then
        echo "✅ MCP endpoints are accessible"
    else
        echo "❌ MCP endpoints not accessible"
        exit 1
    fi
else
    echo "❌ retainr server is not running at http://localhost:8000"
    echo "🚀 Start the server with: make up"
    exit 1
fi

echo ""
echo "🎉 Setup complete! retainr is now configured for Claude Code."
echo ""
echo "📋 Next steps:"
echo "1. Restart Claude Code to register the MCP server"
echo "2. Start a new conversation - Claude Code will now have persistent memory!"
echo ""
echo "🔧 Test the integration:"
echo "   - Ask Claude Code to remember something about your project"
echo "   - Start a new session and ask if it remembers"
echo ""
echo "📊 Monitor memories:"
echo "   - View server status: retainr status"
echo "   - List memories: retainr list"
echo "   - Browse files: ls $HOME/.config/claude-code/retainr/memory/"
echo ""
echo "📖 For more information, see: docs/claude-code-integration.md"