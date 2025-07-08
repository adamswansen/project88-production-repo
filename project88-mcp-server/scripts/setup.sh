#!/bin/bash

# Project88 MCP Server Setup Script
# This script sets up the MCP server for development and production use

set -e

echo "🚀 Setting up Project88 MCP Server..."

# Check Node.js version
echo "📋 Checking Node.js version..."
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18.0.0 or higher."
    exit 1
fi

NODE_VERSION=$(node --version | cut -d'v' -f2)
REQUIRED_VERSION="18.0.0"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$NODE_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Node.js version $NODE_VERSION is too old. Please install Node.js 18.0.0 or higher."
    exit 1
fi

echo "✅ Node.js version $NODE_VERSION is compatible"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

# Copy environment configuration
echo "⚙️ Setting up configuration..."
if [ ! -f ".env" ]; then
    cp config.example.env .env
    echo "📝 Created .env file from template. Please update it with your configuration."
else
    echo "✅ .env file already exists"
fi

# Build the project
echo "🔨 Building TypeScript..."
npm run build

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p cache

# Set permissions
echo "🔐 Setting permissions..."
chmod +x scripts/*.sh

# Test the build
echo "🧪 Testing the build..."
if [ -f "build/index.js" ]; then
    echo "✅ Build successful"
else
    echo "❌ Build failed"
    exit 1
fi

echo ""
echo "🎉 Project88 MCP Server setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update .env file with your Project88 configuration"
echo "2. Run: npm start"
echo ""
echo "🔧 Configuration:"
echo "- Edit .env file for your environment"
echo "- Update PROJECT88_ROOT to point to your Project88 workspace"
echo "- Configure database connection if needed"
echo ""
echo "🚀 Usage:"
echo "- Development: npm run dev"
echo "- Production: npm start"
echo "- Testing: npm test"
echo ""
echo "📖 Documentation:"
echo "- See README.md for detailed usage instructions"
echo "- Check config.example.env for all configuration options"
echo "" 