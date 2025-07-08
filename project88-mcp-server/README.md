# Project88 MCP Server

A comprehensive Model Context Protocol (MCP) server specifically designed for the Project88 Race Timing Platform. This server provides deep context, tools, and resources to enhance AI-assisted development and collaboration on the Project88 system.

## 🎯 Overview

The Project88 MCP Server is purpose-built for a live production SaaS platform serving 13 timing partners with 10.7M+ records. It provides:

- **System Architecture Context**: Deep understanding of multi-service architecture
- **Database Schema Knowledge**: Complete schema with multi-tenant isolation
- **Provider Integration Expertise**: RunSignUp, Haku, ChronoTrack adapters
- **Service Management Tools**: Production service monitoring and management
- **Business Logic Context**: Race timing domain knowledge
- **Development Workflow**: Deployment, debugging, and optimization guidance

## 🚀 Features

### Tools Available
- `analyze_system_architecture` - Analyze Project88 system components
- `check_service_status` - Monitor production services
- `get_database_schema` - Database schema information
- `analyze_provider_integration` - Provider adapter analysis
- `get_business_requirements` - Current requirements and completion status
- `generate_deployment_plan` - Deployment planning assistance
- `analyze_performance_metrics` - Performance analysis
- `get_error_analysis` - Common errors and solutions

### Resources Available
- `project88://system/architecture` - Complete system architecture
- `project88://database/schema` - Database schema and relationships
- `project88://services/config` - Service configurations
- `project88://providers/adapters` - Provider adapter documentation
- `project88://business/requirements` - Business requirements status
- `project88://deployment/guide` - Deployment procedures
- `project88://troubleshooting/guide` - Troubleshooting guide

### Prompts Available
- `debug_sync_issue` - Debug provider synchronization problems
- `optimize_database_query` - Database query optimization
- `implement_new_feature` - New feature implementation guidance
- `troubleshoot_service` - Service troubleshooting assistance

## 📦 Installation

### Prerequisites
- Node.js 18.0.0 or higher
- npm or yarn package manager

### Install Dependencies
```bash
npm install
```

### Build the Server
```bash
npm run build
```

## 🛠️ Usage

### Running the Server
```bash
npm start
```

### Development Mode
```bash
npm run dev
```

### Testing
```bash
npm test
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory:

```env
# Project88 Configuration
PROJECT88_ROOT=/path/to/project88
DATABASE_URL=postgresql://user:password@localhost:5432/project88_myappdb
PRODUCTION_SERVER=69.62.69.90

# Optional: Enable debug logging
DEBUG=true
```

### Claude Desktop Integration
Add to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "project88": {
      "command": "node",
      "args": ["/path/to/project88-mcp-server/build/index.js"]
    }
  }
}
```

### VS Code Integration
Add to your VS Code settings:

```json
{
  "mcp": {
    "servers": {
      "project88": {
        "command": "node",
        "args": ["/path/to/project88-mcp-server/build/index.js"]
      }
    }
  }
}
```

## 🎯 Use Cases

### System Analysis
```
Use the analyze_system_architecture tool to understand:
- Service architecture and dependencies
- Port mappings and URLs
- Technology stack details
- Production status
```

### Database Management
```
Use the get_database_schema tool to:
- Understand table relationships
- Review multi-tenant isolation
- Analyze data structures
- Plan schema changes
```

### Provider Integration
```
Use the analyze_provider_integration tool to:
- Understand adapter patterns
- Review sync performance
- Debug integration issues
- Plan new provider additions
```

### Performance Optimization
```
Use the analyze_performance_metrics tool to:
- Review current performance
- Identify bottlenecks
- Plan optimizations
- Monitor improvements
```

## 📊 Project88 System Context

### Architecture Overview
- **Platform**: Live production SaaS race timing platform
- **Scale**: 13 timing partners, 10.7M+ records
- **Completion**: 77% complete (10 of 13 business requirements)
- **Timeline**: 3 weeks to 100% completion

### Production Services
- **Race Display**: https://display.project88hub.com (Port 5001)
- **Timing Collector**: ChronoTrack TCP (Port 61611)
- **Authentication**: https://project88hub.com (Port 5002)
- **AI Platform**: https://ai.project88hub.com (Port 8501)
- **Database**: PostgreSQL with 10.7M+ records

### Technology Stack
- **Backend**: Python (FastAPI, Flask), PostgreSQL, Redis
- **Frontend**: React, Node.js
- **AI**: OpenWebUI, Ollama, LLM models
- **Infrastructure**: VPS (AlmaLinux 9.6, 8 CPU, 32GB RAM)

## 🐛 Troubleshooting

### Common Issues

**Server won't start**
```bash
# Check Node.js version
node --version  # Should be 18.0.0+

# Check TypeScript compilation
npm run build

# Check for missing dependencies
npm install
```

**Resource not found**
```bash
# Verify project root detection
# Check PROJECT88_ROOT environment variable
# Ensure project structure is correct
```

**Performance issues**
```bash
# Enable debug logging
DEBUG=true npm start

# Check memory usage
# Monitor for large JSON responses
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Install dependencies: `npm install`
3. Start development server: `npm run dev`
4. Make your changes
5. Run tests: `npm test`
6. Submit a pull request

### Code Style
- TypeScript strict mode
- ESLint + Prettier formatting
- Comprehensive error handling
- Clear documentation

## 📝 License

MIT License - see LICENSE file for details.

## 🎉 Acknowledgments

Built for the Project88 Race Timing Platform - a live production system serving the race timing community with cutting-edge technology and AI-assisted development.

---

**Made with ❤️ for the Project88 team** 