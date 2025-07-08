#!/usr/bin/env node

/**
 * Project88 MCP Server - Simple Version
 * Provides comprehensive Project88 context for AI collaboration
 * 
 * Major Update: Added Alex's Analytics Dashboard & Complete Haku Integration
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ErrorCode,
  ListResourcesRequestSchema,
  ListToolsRequestSchema,
  McpError,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const PROJECT_ROOT = process.env.PROJECT88_ROOT || "/Users/adamswansen/Desktop/Project88";

const server = new Server(
  {
    name: "project88-mcp-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  }
);

// Enhanced system data with Alex's additions
const PROJECT_DATA = {
  overview: {
    name: "Project88 Race Timing Platform",
    status: "Production Live System",
    version: "2.0.0",
    completion: "82% complete", // Updated with dashboard + Haku
    totalRecords: "10.7M+",
    timingPartners: 13,
    businessRequirements: "11 of 13 implemented", // Updated
    architecture: "Multi-tenant SaaS, 7 microservices", // Updated
    server: "AlmaLinux 9.6 (8 CPU, 32GB RAM)",
    uptime: "24/7 production operation"
  },
  
  services: {
    // Updated with Alex's new dashboard
    "analytics-dashboard": {
      name: "Analytics Dashboard",
      url: "https://dashboard.project88hub.com",
      port: 5004,
      status: "✅ Production Ready",
      technology: "Flask + React",
      features: [
        "Real-time metrics: 13,819+ events, 2,420,628+ participants",
        "Multi-tenant filtering by timing partner",
        "Redis caching for performance",
        "Glassmorphism UI design",
        "Provider analytics and trends",
        "System health monitoring",
        "API endpoints for all metrics"
      ],
      description: "Comprehensive analytics dashboard with live metrics",
      backend: "583-line Flask application",
      frontend: "659-line React application",
      deployment: "Systemd service + Apache proxy"
    },
    
    "race-display": {
      name: "Race Display System",
      url: "https://display.project88hub.com",
      port: 5001,
      status: "✅ Production",
      technology: "Flask + React",
      features: [
        "Real-time race results display",
        "Customizable templates",
        "Multi-event support",
        "Responsive design"
      ],
      description: "Live race timing display system"
    },
    
    "timing-collector": {
      name: "ChronoTrack Timing Collector",
      port: 61611,
      status: "✅ Production",
      technology: "Python TCP",
      features: [
        "24/7 TCP connection to ChronoTrack",
        "Real-time timing data ingestion",
        "Automatic reconnection",
        "Data validation and parsing"
      ],
      description: "Collects live timing data from ChronoTrack systems"
    },
    
    "authentication": {
      name: "Authentication Service",
      url: "https://project88hub.com",
      port: 5002,
      status: "✅ Production",
      technology: "Flask + JWT",
      features: [
        "Multi-tenant authentication",
        "Role-based access control",
        "Session management",
        "API key management"
      ],
      description: "Central authentication for all Project88 services"
    },
    
    "user-management": {
      name: "User Management Service",
      port: 5003,
      status: "✅ Production",
      technology: "Flask",
      features: [
        "User registration and profiles",
        "Subscription management",
        "Billing integration",
        "Admin dashboard"
      ],
      description: "Manages user accounts and subscriptions"
    },
    
    "ai-platform": {
      name: "AI Platform",
      url: "https://ai.project88hub.com",
      port: 8501,
      status: "✅ Production",
      technology: "OpenWebUI + Ollama",
      features: [
        "Local AI models",
        "Race timing analysis",
        "Predictive analytics",
        "Custom model training"
      ],
      description: "AI-powered race timing analytics"
    },
    
    "database-api": {
      name: "Database API",
      port: 3000,
      status: "✅ Production",
      technology: "PostgREST",
      features: [
        "RESTful PostgreSQL API",
        "Row-level security",
        "Real-time subscriptions",
        "OpenAPI documentation"
      ],
      description: "Direct PostgreSQL API access"
    }
  },
  
  providers: {
    // Updated with Alex's complete Haku integration
    "haku": {
      name: "Haku Integration",
      status: "✅ Production Ready - 7 Integrations",
      priority: "PRIMARY PROVIDER",
      integrations: 7,
      timingPartners: 5,
      authentication: "Cognito User Pools",
      features: [
        "Complete Haku adapter with Cognito auth",
        "Event-driven scheduler (follows RunSignUp pattern)",
        "7 integrations across 5 timing partners",
        "Credential migration system",
        "Backfill scripts for historical data",
        "Production deployment tools",
        "Rate limiting: 500 calls/hour",
        "Pagination: 25 records per page"
      ],
      organizations: [
        "BIX (Partners 1 & 7)",
        "Goal Foundation (Partner 3)",
        "Atlanta Track Club (Partner 4)",
        "Hartford Marathon Foundation (Partner 7)",
        "J&A Racing (Partner 9)",
        "Beyond Monumental (Partner 9)"
      ],
      deployment: "Ready for production with deploy_haku_integration.sh",
      expectedVolume: "Highest volume provider (7 vs 2 RunSignUp)"
    },
    
    "runsignup": {
      name: "RunSignUp Integration",
      status: "✅ Production - 30x Performance Improvement",
      performance: "15-30 minutes (was 7.5 hours)",
      integrations: 2,
      features: [
        "Event-driven scheduler",
        "Incremental sync optimization",
        "Dynamic frequency adjustment",
        "Comprehensive error handling",
        "Production monitoring"
      ],
      metrics: {
        events: "937",
        participants: "38,362",
        syncTime: "15-30 minutes",
        improvement: "30x faster"
      }
    },
    
    "chronotrack": {
      name: "ChronoTrack Integration",
      status: "✅ Production - Highest Volume",
      volume: "Primary timing data source",
      metrics: {
        events: "12,882",
        participants: "2,382,266",
        results: "7,644,980"
      },
      features: [
        "TCP protocol integration",
        "Real-time timing data",
        "File format processing",
        "Socket protocol implementation"
      ]
    },
    
    "race-roster": {
      name: "Race Roster Integration",
      status: "📋 Tables Ready - Awaiting Data",
      readiness: "Database schema complete",
      features: [
        "Complete table structure",
        "API adapter framework",
        "Integration patterns established"
      ]
    },
    
    "copernico": {
      name: "Copernico Integration",
      status: "📋 Tables Ready - Awaiting Data",
      readiness: "Database schema complete",
      features: [
        "Events and participants tables",
        "Results tracking capability",
        "Multi-language support"
      ]
    }
  },
  
  database: {
    system: "PostgreSQL 15.2",
    name: "project88_myappdb",
    records: "10.7M+",
    tables: {
      core: ["timing_partners", "users", "providers"],
      runsignup: ["runsignup_events", "runsignup_participants"],
      chronotrack: ["ct_events", "ct_participants", "ct_results"],
      haku: ["haku_events", "haku_participants"], // Added by Alex
      raceRoster: ["raceroster_events", "raceroster_participants"],
      copernico: ["copernico_events", "copernico_participants", "copernico_results"],
      sync: ["sync_history", "sync_queue", "partner_provider_credentials"],
      unified: ["unified_events", "unified_participants", "unified_results"]
    },
    performance: {
      optimization: "30x improvement in sync performance",
      indexing: "Comprehensive indexes on timing_partner_id",
      caching: "Redis caching for dashboard metrics"
    }
  },
  
  businessRequirements: {
    completed: [
      "Multi-tenant timing partner isolation",
      "Real-time ChronoTrack data collection",
      "RunSignUp event and participant sync",
      "Event-driven sync scheduling",
      "Performance optimization (30x improvement)",
      "Production deployment infrastructure",
      "AI-powered analytics platform",
      "Multi-service architecture",
      "Analytics dashboard with real-time metrics", // Added by Alex
      "Complete Haku integration (7 integrations)", // Added by Alex
      "Database API with PostgREST"
    ],
    pending: [
      "Unique shareable URLs (Week 1 priority)",
      "ChronoTrack session selection (Week 1 priority)"
    ],
    timeline: "2 weeks remaining for 100% completion"
  },
  
  performance: {
    syncOptimization: "30x improvement (7.5 hours → 15-30 minutes)",
    databaseOptimization: "Field length constraints resolved",
    caching: "Redis caching for dashboard metrics",
    monitoring: "Real-time system health monitoring",
    uptime: "24/7 production operation"
  },
  
  recentUpdates: {
    dashboard: {
      added: "Comprehensive analytics dashboard",
      features: [
        "Real-time metrics across all providers",
        "Multi-tenant filtering",
        "Provider analytics and trends",
        "System health monitoring",
        "Modern React UI with glassmorphism",
        "Redis caching for performance",
        "Production deployment ready"
      ],
      metrics: {
        totalEvents: "13,819+",
        totalParticipants: "2,420,628+",
        totalResults: "7,644,980+"
      }
    },
    
    hakuIntegration: {
      added: "Complete Haku provider integration",
      scope: "7 integrations across 5 timing partners",
      features: [
        "Full Haku adapter with Cognito authentication",
        "Event-driven scheduler following RunSignUp pattern",
        "Credential migration system",
        "Backfill scripts for historical data",
        "Production deployment tools",
        "Rate limiting and pagination handling"
      ],
      status: "Ready for production deployment",
      expectedImpact: "Haku becomes primary provider (7 vs 2 RunSignUp)"
    }
  }
};

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "analyze_system",
        description: "Analyze Project88 system architecture, performance, and current status including Alex's new dashboard and Haku integration",
        inputSchema: {
          type: "object",
          properties: {},
          required: [],
        },
      },
      {
        name: "get_project_info",
        description: "Get comprehensive Project88 project information including business requirements, provider integrations, and development status",
        inputSchema: {
          type: "object",
          properties: {
            focus: {
              type: "string",
              description: "Focus area: 'requirements', 'providers', 'performance', 'recent-updates', or 'all'",
              enum: ["requirements", "providers", "performance", "recent-updates", "all"]
            }
          },
          required: [],
        },
      },
    ],
  };
});

// List available resources
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: "project88://overview",
        name: "Project88 System Overview",
        description: "Complete overview of Project88 platform including Alex's dashboard and Haku integration",
        mimeType: "text/plain",
      },
      {
        uri: "project88://architecture",
        name: "System Architecture",
        description: "Detailed technical architecture including all 7 microservices and provider integrations",
        mimeType: "text/plain",
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      case "analyze_system":
        return {
          content: [
            {
              type: "text",
              text: `# Project88 System Analysis

## 🎯 **System Overview**
${PROJECT_DATA.overview.name} - ${PROJECT_DATA.overview.status}
- **Architecture**: ${PROJECT_DATA.overview.architecture}
- **Completion**: ${PROJECT_DATA.overview.completion}
- **Total Records**: ${PROJECT_DATA.overview.totalRecords}
- **Timing Partners**: ${PROJECT_DATA.overview.timingPartners}
- **Server**: ${PROJECT_DATA.overview.server}

## 🚀 **Recent Major Updates by Alex**

### 📊 **Analytics Dashboard** (NEW)
- **URL**: ${PROJECT_DATA.services["analytics-dashboard"].url}
- **Status**: ${PROJECT_DATA.services["analytics-dashboard"].status}
- **Technology**: ${PROJECT_DATA.services["analytics-dashboard"].technology}
- **Backend**: ${PROJECT_DATA.services["analytics-dashboard"].backend}
- **Frontend**: ${PROJECT_DATA.services["analytics-dashboard"].frontend}
- **Metrics**: ${PROJECT_DATA.recentUpdates.dashboard.metrics.totalEvents} events, ${PROJECT_DATA.recentUpdates.dashboard.metrics.totalParticipants} participants, ${PROJECT_DATA.recentUpdates.dashboard.metrics.totalResults} results

### 🔗 **Complete Haku Integration** (NEW)
- **Status**: ${PROJECT_DATA.providers.haku.status}
- **Priority**: ${PROJECT_DATA.providers.haku.priority}
- **Integrations**: ${PROJECT_DATA.providers.haku.integrations} across ${PROJECT_DATA.providers.haku.timingPartners} timing partners
- **Authentication**: ${PROJECT_DATA.providers.haku.authentication}
- **Expected Volume**: ${PROJECT_DATA.providers.haku.expectedVolume}

## 🏗️ **Service Architecture** (7 Microservices)
${Object.entries(PROJECT_DATA.services).map(([key, service]) => 
  `- **${service.name}**: ${service.status} (${service.technology || 'N/A'})`
).join('\n')}

## 📊 **Provider Integration Status**
${Object.entries(PROJECT_DATA.providers).map(([key, provider]) => 
  `- **${provider.name}**: ${provider.status}${provider.integrations ? ` (${provider.integrations} integrations)` : ''}`
).join('\n')}

## 🎯 **Business Requirements**
- **Completed**: ${PROJECT_DATA.businessRequirements.completed.length}/13 requirements
- **Pending**: ${PROJECT_DATA.businessRequirements.pending.length} critical items
- **Timeline**: ${PROJECT_DATA.businessRequirements.timeline}

## 📈 **Performance Metrics**
- **Sync Optimization**: ${PROJECT_DATA.performance.syncOptimization}
- **Database Records**: ${PROJECT_DATA.database.records}
- **Uptime**: ${PROJECT_DATA.performance.uptime}

## 🔧 **Technical Infrastructure**
- **Database**: ${PROJECT_DATA.database.system}
- **Caching**: ${PROJECT_DATA.database.performance.caching}
- **Monitoring**: ${PROJECT_DATA.performance.monitoring}

**🎉 System Status**: Production-ready with major new capabilities!`,
            },
          ],
        };

      case "get_project_info":
        const focus = args?.focus || "all";
        
        let content = "# Project88 Project Information\n\n";
        
        if (focus === "all" || focus === "requirements") {
          content += `## 📋 **Business Requirements Status**\n\n`;
          content += `**Completed (${PROJECT_DATA.businessRequirements.completed.length}/13):**\n`;
          content += PROJECT_DATA.businessRequirements.completed.map(req => `- ✅ ${req}`).join('\n');
          content += `\n\n**Pending (${PROJECT_DATA.businessRequirements.pending.length}):**\n`;
          content += PROJECT_DATA.businessRequirements.pending.map(req => `- ⏳ ${req}`).join('\n');
          content += `\n\n**Timeline**: ${PROJECT_DATA.businessRequirements.timeline}\n\n`;
        }
        
        if (focus === "all" || focus === "providers") {
          content += `## 🔗 **Provider Integration Status**\n\n`;
          content += Object.entries(PROJECT_DATA.providers).map(([key, provider]) => {
            let providerInfo = `### ${provider.name}\n`;
            providerInfo += `- **Status**: ${provider.status}\n`;
            if (provider.integrations) providerInfo += `- **Integrations**: ${provider.integrations}\n`;
            if (provider.metrics) {
              providerInfo += `- **Metrics**: ${Object.entries(provider.metrics).map(([k, v]) => `${k}: ${v}`).join(', ')}\n`;
            }
            if (provider.features) {
              providerInfo += `- **Features**: ${provider.features.join(', ')}\n`;
            }
            return providerInfo;
          }).join('\n');
        }
        
        if (focus === "all" || focus === "performance") {
          content += `## 📈 **Performance & Optimization**\n\n`;
          content += `- **Sync Performance**: ${PROJECT_DATA.performance.syncOptimization}\n`;
          content += `- **Database**: ${PROJECT_DATA.database.records} records\n`;
          content += `- **Optimization**: ${PROJECT_DATA.database.performance.optimization}\n`;
          content += `- **Caching**: ${PROJECT_DATA.database.performance.caching}\n`;
          content += `- **Monitoring**: ${PROJECT_DATA.performance.monitoring}\n\n`;
        }
        
        if (focus === "all" || focus === "recent-updates") {
          content += `## 🚀 **Recent Major Updates**\n\n`;
          content += `### 📊 Analytics Dashboard\n`;
          content += `- **Added**: ${PROJECT_DATA.recentUpdates.dashboard.added}\n`;
          content += `- **Features**: ${PROJECT_DATA.recentUpdates.dashboard.features.join(', ')}\n`;
          content += `- **Metrics**: ${Object.entries(PROJECT_DATA.recentUpdates.dashboard.metrics).map(([k, v]) => `${k}: ${v}`).join(', ')}\n\n`;
          
          content += `### 🔗 Haku Integration\n`;
          content += `- **Added**: ${PROJECT_DATA.recentUpdates.hakuIntegration.added}\n`;
          content += `- **Scope**: ${PROJECT_DATA.recentUpdates.hakuIntegration.scope}\n`;
          content += `- **Features**: ${PROJECT_DATA.recentUpdates.hakuIntegration.features.join(', ')}\n`;
          content += `- **Status**: ${PROJECT_DATA.recentUpdates.hakuIntegration.status}\n`;
          content += `- **Expected Impact**: ${PROJECT_DATA.recentUpdates.hakuIntegration.expectedImpact}\n\n`;
        }
        
        return {
          content: [
            {
              type: "text",
              text: content,
            },
          ],
        };

      default:
        throw new McpError(
          ErrorCode.MethodNotFound,
          `Unknown tool: ${name}`
        );
    }
  } catch (error) {
    throw new McpError(
      ErrorCode.InternalError,
      `Tool execution failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }
});

// Handle resource reads
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const { uri } = request.params;

  try {
    switch (uri) {
      case "project88://overview":
        return {
          contents: [
            {
              uri,
              mimeType: "text/plain",
              text: `# Project88 Platform Overview

## System Status: ${PROJECT_DATA.overview.status}
- **Architecture**: ${PROJECT_DATA.overview.architecture}
- **Completion**: ${PROJECT_DATA.overview.completion}
- **Total Records**: ${PROJECT_DATA.overview.totalRecords}
- **Timing Partners**: ${PROJECT_DATA.overview.timingPartners}

## Recent Major Updates by Alex

### 📊 Analytics Dashboard
${PROJECT_DATA.services["analytics-dashboard"].description}
- **URL**: ${PROJECT_DATA.services["analytics-dashboard"].url}
- **Technology**: ${PROJECT_DATA.services["analytics-dashboard"].technology}
- **Features**: ${PROJECT_DATA.services["analytics-dashboard"].features.join(', ')}

### 🔗 Haku Integration
${PROJECT_DATA.providers.haku.integrations} integrations across ${PROJECT_DATA.providers.haku.timingPartners} timing partners
- **Status**: ${PROJECT_DATA.providers.haku.status}
- **Authentication**: ${PROJECT_DATA.providers.haku.authentication}
- **Organizations**: ${PROJECT_DATA.providers.haku.organizations.join(', ')}

## Services (7 Microservices)
${Object.entries(PROJECT_DATA.services).map(([key, service]) => 
  `- **${service.name}**: ${service.status} (${service.url || `Port ${service.port}`})`
).join('\n')}

## Business Requirements
- **Completed**: ${PROJECT_DATA.businessRequirements.completed.length}/13
- **Pending**: ${PROJECT_DATA.businessRequirements.pending.length}
- **Timeline**: ${PROJECT_DATA.businessRequirements.timeline}

## Performance
- **Sync Optimization**: ${PROJECT_DATA.performance.syncOptimization}
- **Database**: ${PROJECT_DATA.database.records} records
- **Uptime**: ${PROJECT_DATA.performance.uptime}
`,
            },
          ],
        };

      case "project88://architecture":
        return {
          contents: [
            {
              uri,
              mimeType: "text/plain",
              text: `# Project88 System Architecture

## Infrastructure
- **Server**: ${PROJECT_DATA.overview.server}
- **Database**: ${PROJECT_DATA.database.system}
- **Architecture**: ${PROJECT_DATA.overview.architecture}

## Service Layer (7 Microservices)
${Object.entries(PROJECT_DATA.services).map(([key, service]) => {
  let serviceInfo = `\n### ${service.name}\n`;
  serviceInfo += `- **URL**: ${service.url || `Port ${service.port}`}\n`;
  serviceInfo += `- **Status**: ${service.status}\n`;
  serviceInfo += `- **Technology**: ${service.technology || 'N/A'}\n`;
  serviceInfo += `- **Description**: ${service.description}\n`;
  if (service.features) {
    serviceInfo += `- **Features**: ${service.features.join(', ')}\n`;
  }
  return serviceInfo;
}).join('')}

## Provider Integration Layer
${Object.entries(PROJECT_DATA.providers).map(([key, provider]) => {
  let providerInfo = `\n### ${provider.name}\n`;
  providerInfo += `- **Status**: ${provider.status}\n`;
  if (provider.integrations) providerInfo += `- **Integrations**: ${provider.integrations}\n`;
  if (provider.authentication) providerInfo += `- **Authentication**: ${provider.authentication}\n`;
  if (provider.metrics) {
    providerInfo += `- **Volume**: ${Object.entries(provider.metrics).map(([k, v]) => `${k}: ${v}`).join(', ')}\n`;
  }
  return providerInfo;
}).join('')}

## Database Layer
- **System**: ${PROJECT_DATA.database.system}
- **Records**: ${PROJECT_DATA.database.records}
- **Tables**: ${Object.entries(PROJECT_DATA.database.tables).map(([category, tables]) => 
    `${category}: ${Array.isArray(tables) ? tables.join(', ') : tables}`
  ).join('; ')}
- **Performance**: ${PROJECT_DATA.database.performance.optimization}
- **Caching**: ${PROJECT_DATA.database.performance.caching}

## Recent Architecture Updates
1. **Analytics Dashboard**: New microservice for comprehensive system metrics
2. **Haku Integration**: Complete provider integration with 7 connections
3. **Enhanced Monitoring**: Real-time system health and performance tracking
4. **Redis Caching**: Performance optimization for dashboard metrics

## Technology Stack
- **Backend**: Python Flask, FastAPI
- **Frontend**: React, HTML/CSS/JS
- **Database**: PostgreSQL 15.2
- **Caching**: Redis
- **Deployment**: Docker, Systemd, Apache
- **Monitoring**: Custom monitoring + logging
- **Authentication**: JWT, Cognito User Pools
`,
            },
          ],
        };

      default:
        throw new McpError(
          ErrorCode.InvalidRequest,
          `Unknown resource: ${uri}`
        );
    }
  } catch (error) {
    throw new McpError(
      ErrorCode.InternalError,
      `Resource read failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }
});

// Start the server
const transport = new StdioServerTransport();
server.connect(transport);

console.error("Project88 MCP Server running on stdio");
console.error("Updated with Alex's Analytics Dashboard & Complete Haku Integration");
console.error("System: 7 microservices, 10.7M+ records, 82% complete"); 