#!/bin/bash

# Project88 MCP Server Launcher
# This script launches the MCP server with proper environment setup

echo "🚀 Starting Project88 MCP Server..."

# Set working directory to the project root
cd "$(dirname "$0")"

# Check if the server is built
if [ ! -f "build/simple-server.js" ]; then
    echo "📦 Building MCP server..."
    npm run build
fi

# Set environment variables
export PROJECT88_ROOT="/Users/adamswansen/Desktop/Project88"
export NODE_ENV="development"
export DEBUG="false"

# Start the MCP server
echo "✅ Launching MCP server on stdio..."
echo "📝 Server provides comprehensive Project88 context"
echo "🔗 Use with Claude Desktop, VS Code, or other MCP clients"
echo ""

node build/simple-server.js 