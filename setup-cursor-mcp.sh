#!/bin/bash

# Project88 Cursor MCP Setup Script
echo "🚀 Setting up Project88 MCP Server for Cursor..."

# Check if we're in the right directory
if [ ! -f "build/simple-server.js" ]; then
    echo "❌ Error: simple-server.js not found in build directory"
    echo "Please run this script from the project88-mcp-server directory"
    echo "And ensure you've built the server: npm run build"
    exit 1
fi

# Get the absolute path to the MCP server
MCP_SERVER_PATH="$(pwd)/build/simple-server.js"
PROJECT_ROOT="$(dirname $(pwd))"

echo "📍 MCP Server Path: $MCP_SERVER_PATH"
echo "📍 Project Root: $PROJECT_ROOT"

# Create Cursor MCP directory
CURSOR_MCP_DIR="$HOME/Library/Application Support/Cursor/User/globalStorage/cursor.mcp"
echo "📂 Creating Cursor MCP directory..."
mkdir -p "$CURSOR_MCP_DIR"

# Create the configuration
echo "⚙️  Creating MCP configuration..."
cat > "$CURSOR_MCP_DIR/mcp_servers.json" << EOF
{
  "mcpServers": {
    "project88": {
      "name": "Project88 Race Timing Platform",
      "description": "Comprehensive Project88 system context with analytics dashboard and Haku integration",
      "command": "node",
      "args": [
        "$MCP_SERVER_PATH"
      ],
      "env": {
        "PROJECT88_ROOT": "$PROJECT_ROOT",
        "NODE_ENV": "development"
      },
      "capabilities": {
        "tools": true,
        "resources": true
      }
    }
  }
}
EOF

echo "✅ Configuration installed at: $CURSOR_MCP_DIR/mcp_servers.json"

# Test the MCP server
echo "🧪 Testing MCP server..."
if node test-mcp.js; then
    echo "✅ MCP server test passed!"
else
    echo "❌ MCP server test failed"
    exit 1
fi

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Restart Cursor completely"
echo "2. Open Cursor and look for 'Project88 Race Timing Platform' in MCP panel"
echo "3. Test with: 'Can you analyze the current Project88 system architecture?'"
echo ""
echo "📚 For testing help, see: test-cursor-integration.md"
echo ""
echo "🚀 Your Project88 MCP Server is ready in Cursor!" 