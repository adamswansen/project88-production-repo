# Project88 MCP Server Integration Guide

## 🚀 Quick Start

Your Project88 MCP server is ready! Here's how to get it working:

### 1. Test the Server

```bash
# Test the MCP server functionality
cd project88-mcp-server
node test-mcp.js
```

### 2. Launch the Server

```bash
# Option 1: Use the launch script
./launch-mcp.sh

# Option 2: Direct launch
npm run start
```

## 🔧 Integration Options

### A. Claude Desktop Integration

1. **Locate your Claude Desktop config file:**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
   - Linux: `~/.config/Claude/claude_desktop_config.json`

2. **Add the Project88 MCP server to your config:**

```json
{
  "mcpServers": {
    "project88": {
      "command": "node",
      "args": [
        "/Users/adamswansen/Desktop/Project88/project88-mcp-server/build/simple-server.js"
      ],
      "env": {
        "PROJECT88_ROOT": "/Users/adamswansen/Desktop/Project88",
        "NODE_ENV": "development"
      }
    }
  }
}
```

3. **Restart Claude Desktop** - The MCP server will be automatically loaded

### B. VS Code Integration

1. Install the MCP extension for VS Code
2. Configure the server path in your workspace settings

### C. Other MCP Clients

The server runs on stdio and follows the MCP protocol, so it works with any MCP client.

## 🛠️ Available Tools

Once integrated, you'll have access to these Project88-specific tools:

### 1. `analyze_system`
- Provides comprehensive system architecture analysis
- Returns service status, database info, and performance metrics

### 2. `get_project_info`
- Returns detailed project context including business requirements
- Shows provider integrations and current development status

## 📊 Available Resources

The MCP server provides these resources:

### 1. `project_overview`
- Complete Project88 system overview
- Business requirements and completion status

### 2. `system_architecture`
- Detailed technical architecture
- Service configurations and database schema

## 🎯 What This Gives You

With the Project88 MCP server integrated, Claude will have deep context about:

- **Live Production System**: 10.7M+ records, 13 timing partners
- **Service Architecture**: 6 microservices, multi-tenant SaaS
- **Database Schema**: Complete PostgreSQL structure
- **Provider Integrations**: RunSignUp, Haku, ChronoTrack
- **Performance Metrics**: 30x optimization achievements
- **Business Requirements**: 77% complete, 3-week roadmap
- **Deployment Status**: Live production environment details

## 🔍 Testing & Validation

Run the test script to verify everything works:

```bash
cd project88-mcp-server
node test-mcp.js
```

Expected output:
```
✅ Server started successfully
✅ Tools are available and responding
✅ Resources are accessible
🎉 MCP Server test completed successfully!
```

## 🐛 Troubleshooting

### Server Won't Start
- Check that Node.js is installed: `node --version`
- Verify the build exists: `ls build/simple-server.js`
- Rebuild if needed: `npm run build`

### Claude Desktop Not Recognizing Server
- Verify config file location and syntax
- Check that the path to the built server is correct
- Restart Claude Desktop completely

### Permission Issues
- Make sure the launch script is executable: `chmod +x launch-mcp.sh`
- Check file permissions on the build directory

## 📚 Usage Examples

Once integrated, you can ask Claude questions like:

- "What's the current status of the Project88 system?"
- "How are the provider integrations performing?"
- "What database optimizations have been implemented?"
- "What are the pending business requirements?"
- "How is the RunSignUp sync performing?"

The MCP server will provide detailed, context-aware responses based on your live system data.

## 🔄 Updates

To update the MCP server:

1. Make changes to `src/simple-server.ts`
2. Rebuild: `npm run build`
3. Restart Claude Desktop (if using Claude Desktop integration)

---

**🎉 Your Project88 MCP Server is ready for enhanced AI collaboration!** 