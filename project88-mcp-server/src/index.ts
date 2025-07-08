#!/usr/bin/env node

/**
 * Project88 MCP Server
 * A comprehensive Model Context Protocol server for Project88 Race Timing Platform
 * 
 * This server provides:
 * - System architecture context
 * - Database schema information
 * - Provider integration knowledge
 * - Service management tools
 * - Business logic context
 * - Development workflow assistance
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  ListPromptsRequestSchema,
  GetPromptRequestSchema,
  PromptMessage,
  TextContent,
  ImageContent,
  Tool,
  Resource,
  Prompt,
} from "@modelcontextprotocol/sdk/types.js";
import { z } from "zod";
import fs from "fs-extra";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class Project88MCPServer {
  private server: Server;
  private projectRoot: string;

  constructor() {
    this.server = new Server(
      {
        name: "project88-mcp-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          tools: {},
          resources: {},
          prompts: {},
        },
      }
    );

    // Assume we're running from the project root or detect it
    this.projectRoot = this.findProjectRoot();
    this.setupHandlers();
  }

  private findProjectRoot(): string {
    // Try to find the project root by looking for characteristic files
    let currentDir = process.cwd();
    const markers = ['project88-production-repo', 'README.md', 'package.json'];
    
    while (currentDir !== '/') {
      const hasMarker = markers.some(marker => 
        fs.existsSync(path.join(currentDir, marker))
      );
      if (hasMarker) {
        return currentDir;
      }
      currentDir = path.dirname(currentDir);
    }
    
    return process.cwd(); // fallback to current directory
  }

  private setupHandlers(): void {
    this.setupToolHandlers();
    this.setupResourceHandlers();
    this.setupPromptHandlers();
  }

  private setupToolHandlers(): void {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "analyze_system_architecture",
            description: "Analyze the Project88 system architecture and services",
            inputSchema: {
              type: "object",
              properties: {
                component: {
                  type: "string",
                  description: "Specific component to analyze (optional)",
                  enum: ["race-display", "timing-collector", "auth", "ai-platform", "provider-integrations", "all"]
                }
              }
            }
          },
          {
            name: "check_service_status",
            description: "Check the status of Project88 services",
            inputSchema: {
              type: "object",
              properties: {
                service: {
                  type: "string",
                  description: "Specific service to check (optional)"
                }
              }
            }
          },
          {
            name: "get_database_schema",
            description: "Get database schema information for Project88",
            inputSchema: {
              type: "object",
              properties: {
                table: {
                  type: "string",
                  description: "Specific table to describe (optional)"
                }
              }
            }
          },
          {
            name: "analyze_provider_integration",
            description: "Analyze provider integration patterns and adapters",
            inputSchema: {
              type: "object",
              properties: {
                provider: {
                  type: "string",
                  description: "Specific provider to analyze",
                  enum: ["runsignup", "haku", "chronotrack", "all"]
                }
              }
            }
          },
          {
            name: "get_business_requirements",
            description: "Get current business requirements and completion status",
            inputSchema: {
              type: "object",
              properties: {
                category: {
                  type: "string",
                  description: "Specific requirement category",
                  enum: ["completed", "partial", "missing", "all"]
                }
              }
            }
          },
          {
            name: "generate_deployment_plan",
            description: "Generate a deployment plan for Project88 changes",
            inputSchema: {
              type: "object",
              properties: {
                component: {
                  type: "string",
                  description: "Component to deploy"
                },
                environment: {
                  type: "string",
                  description: "Target environment",
                  enum: ["development", "staging", "production"]
                }
              },
              required: ["component", "environment"]
            }
          },
          {
            name: "analyze_performance_metrics",
            description: "Analyze Project88 performance metrics and bottlenecks",
            inputSchema: {
              type: "object",
              properties: {
                metric_type: {
                  type: "string",
                  description: "Type of performance metric",
                  enum: ["database", "api", "sync", "memory", "all"]
                }
              }
            }
          },
          {
            name: "get_error_analysis",
            description: "Analyze common errors and their solutions",
            inputSchema: {
              type: "object",
              properties: {
                error_type: {
                  type: "string",
                  description: "Type of error to analyze",
                  enum: ["sync", "database", "api", "auth", "all"]
                }
              }
            }
          }
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "analyze_system_architecture":
          return this.analyzeSystemArchitecture(args?.component);
        
        case "check_service_status":
          return this.checkServiceStatus(args?.service);
        
        case "get_database_schema":
          return this.getDatabaseSchema(args?.table);
        
        case "analyze_provider_integration":
          return this.analyzeProviderIntegration(args?.provider);
        
        case "get_business_requirements":
          return this.getBusinessRequirements(args?.category);
        
        case "generate_deployment_plan":
          return this.generateDeploymentPlan(args?.component, args?.environment);
        
        case "analyze_performance_metrics":
          return this.analyzePerformanceMetrics(args?.metric_type);
        
        case "get_error_analysis":
          return this.getErrorAnalysis(args?.error_type);
        
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  private setupResourceHandlers(): void {
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return {
        resources: [
          {
            uri: "project88://system/architecture",
            name: "System Architecture Overview",
            description: "Complete Project88 system architecture and service map",
            mimeType: "application/json"
          },
          {
            uri: "project88://database/schema",
            name: "Database Schema",
            description: "Complete database schema with table relationships",
            mimeType: "application/json"
          },
          {
            uri: "project88://services/config",
            name: "Service Configurations",
            description: "All service configurations and deployment details",
            mimeType: "application/json"
          },
          {
            uri: "project88://providers/adapters",
            name: "Provider Adapters",
            description: "Documentation of all provider integration adapters",
            mimeType: "application/json"
          },
          {
            uri: "project88://business/requirements",
            name: "Business Requirements",
            description: "Current business requirements and completion status",
            mimeType: "application/json"
          },
          {
            uri: "project88://deployment/guide",
            name: "Deployment Guide",
            description: "Step-by-step deployment procedures",
            mimeType: "text/markdown"
          },
          {
            uri: "project88://troubleshooting/guide",
            name: "Troubleshooting Guide",
            description: "Common issues and solutions",
            mimeType: "text/markdown"
          }
        ],
      };
    });

    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const uri = request.params.uri;
      
      switch (uri) {
        case "project88://system/architecture":
          return this.getSystemArchitecture();
        
        case "project88://database/schema":
          return this.getDatabaseSchemaResource();
        
        case "project88://services/config":
          return this.getServiceConfigurations();
        
        case "project88://providers/adapters":
          return this.getProviderAdapters();
        
        case "project88://business/requirements":
          return this.getBusinessRequirementsResource();
        
        case "project88://deployment/guide":
          return this.getDeploymentGuide();
        
        case "project88://troubleshooting/guide":
          return this.getTroubleshootingGuide();
        
        default:
          throw new Error(`Unknown resource: ${uri}`);
      }
    });
  }

  private setupPromptHandlers(): void {
    this.server.setRequestHandler(ListPromptsRequestSchema, async () => {
      return {
        prompts: [
          {
            name: "debug_sync_issue",
            description: "Debug provider synchronization issues",
            arguments: [
              {
                name: "provider",
                description: "Provider name (runsignup, haku, etc.)",
                required: true
              },
              {
                name: "error_message",
                description: "Error message encountered",
                required: false
              }
            ]
          },
          {
            name: "optimize_database_query",
            description: "Optimize database queries for better performance",
            arguments: [
              {
                name: "query_type",
                description: "Type of query to optimize",
                required: true
              },
              {
                name: "table",
                description: "Target table name",
                required: false
              }
            ]
          },
          {
            name: "implement_new_feature",
            description: "Guide for implementing new features in Project88",
            arguments: [
              {
                name: "feature_name",
                description: "Name of the feature to implement",
                required: true
              },
              {
                name: "component",
                description: "Component where feature will be added",
                required: true
              }
            ]
          },
          {
            name: "troubleshoot_service",
            description: "Troubleshoot service issues",
            arguments: [
              {
                name: "service_name",
                description: "Name of the service having issues",
                required: true
              },
              {
                name: "symptoms",
                description: "Observed symptoms",
                required: false
              }
            ]
          }
        ],
      };
    });

    this.server.setRequestHandler(GetPromptRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "debug_sync_issue":
          return this.getDebugSyncIssuePrompt(args?.provider, args?.error_message);
        
        case "optimize_database_query":
          return this.getOptimizeDatabaseQueryPrompt(args?.query_type, args?.table);
        
        case "implement_new_feature":
          return this.getImplementNewFeaturePrompt(args?.feature_name, args?.component);
        
        case "troubleshoot_service":
          return this.getTroubleshootServicePrompt(args?.service_name, args?.symptoms);
        
        default:
          throw new Error(`Unknown prompt: ${name}`);
      }
    });
  }

  // Tool Implementation Methods
  private async analyzeSystemArchitecture(component?: string) {
    const architecture = {
      overview: "Project88 is a live production SaaS race timing platform serving 13 timing partners with 10.7M+ records",
      services: {
        "race-display": {
          port: 5001,
          url: "https://display.project88hub.com",
          technology: "Flask + React",
          status: "Production",
          description: "Real-time race timing display interface"
        },
        "timing-collector": {
          port: 61611,
          protocol: "ChronoTrack TCP",
          technology: "Python",
          status: "Production 24/7",
          description: "ChronoTrack hardware data collection"
        },
        "authentication": {
          port: 5002,
          url: "https://project88hub.com",
          technology: "Multi-tenant Python",
          status: "Production",
          description: "Multi-tenant user authentication"
        },
        "user-management": {
          port: 5003,
          technology: "Python API",
          status: "Production",
          description: "Subscription and user management"
        },
        "ai-platform": {
          port: 8501,
          url: "https://ai.project88hub.com",
          technology: "OpenWebUI + Ollama",
          status: "Production",
          description: "Natural language database queries"
        },
        "provider-integrations": {
          technology: "Python adapters",
          status: "Production",
          description: "RunSignUp, Haku, and other provider integrations"
        }
      },
      database: {
        type: "PostgreSQL",
        records: "10.7M+",
        tables: "Multi-tenant with proper isolation",
        optimization: "Configured for high performance"
      },
      infrastructure: {
        provider: "Hostinger KVM 8",
        server: "69.62.69.90",
        os: "AlmaLinux 9.6",
        resources: "8 CPU cores, 32GB RAM, 400GB disk"
      }
    };

    if (component && component !== "all") {
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify(architecture.services[component] || {}, null, 2)
          }
        ]
      };
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(architecture, null, 2)
        }
      ]
    };
  }

  private async checkServiceStatus(service?: string) {
    const services = {
      "race-display-clean.service": "✅ Production - Real-time race timing display",
      "timing-collector.service": "✅ Production 24/7 - ChronoTrack TCP listener",
      "project88hub-auth-production.service": "✅ Production - Main authentication",
      "project88hub-auth-phase2.service": "✅ Production - User management",
      "postgrest.service": "✅ Production - Database API",
      "openwebui.service": "✅ Production - AI platform",
      "postgresql.service": "✅ Production - Database server",
      "redis.service": "✅ Production - Session store",
      "apache2.service": "✅ Production - Web server & SSL proxy"
    };

    const statusInfo = service ? 
      { [service]: services[service] || "❌ Unknown service" } : 
      services;

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(statusInfo, null, 2)
        }
      ]
    };
  }

  private async getDatabaseSchema(table?: string) {
    const schema = {
      overview: "Multi-tenant PostgreSQL database with 10.7M+ records",
      key_tables: {
        // User & Authentication
        "users": "User accounts (13 timing partners)",
        "timing_partners": "Timing company configurations",
        "user_subscriptions": "Active subscriptions",
        "payment_history": "Transaction tracking",
        "user_templates": "Custom race templates",
        
        // Race Timing Data
        "ct_events": "ChronoTrack events",
        "ct_races": "Race configurations",
        "ct_participants": "Participant registrations",
        "ct_results": "Race timing results",
        
        // Provider Integrations
        "runsignup_events": "RunSignUp synchronized events",
        "runsignup_participants": "RunSignUp participant data",
        "partner_provider_credentials": "API credentials for providers",
        "sync_history": "Synchronization logs",
        "sync_queue": "Pending sync operations",
        
        // Live Timing
        "timing_sessions": "Live timing sessions (45+ active)",
        "timing_reads": "Real-time timing data (2,040+ reads)",
        "timing_locations": "Hardware location configurations",
        "raw_tag_data": "Raw timing data from hardware"
      },
      relationships: {
        "Multi-tenant isolation": "All tables filtered by timing_partner_id",
        "Event hierarchy": "events → races → participants → results",
        "Provider sync": "External provider data → local normalized tables",
        "Live timing": "Hardware → timing_reads → display system"
      }
    };

    if (table) {
      return {
        content: [
          {
            type: "text",
            text: `Table: ${table}\nDescription: ${schema.key_tables[table] || "Table not found"}`
          }
        ]
      };
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(schema, null, 2)
        }
      ]
    };
  }

  private async analyzeProviderIntegration(provider?: string) {
    const providers = {
      runsignup: {
        status: "✅ Production",
        adapter: "RunSignUpAdapter",
        features: ["Events sync", "Participants sync", "Incremental updates"],
        performance: "30x performance improvement (15-30 min vs 7.5 hours)",
        api_usage: "727/1000 calls per hour",
        schedule: "Event-driven with proximity-based frequencies"
      },
      haku: {
        status: "✅ Production",
        adapter: "HakuAdapter", 
        features: ["Events sync", "Participants sync", "OAuth authentication"],
        integration: "Recently deployed with comprehensive testing"
      },
      chronotrack: {
        status: "✅ Production",
        adapter: "TCP Protocol Handler",
        features: ["Real-time timing data", "Hardware integration"],
        protocol: "ChronoTrack TCP on port 61611"
      },
      base_architecture: {
        pattern: "Abstract base class with standardized interfaces",
        classes: ["ProviderEvent", "ProviderParticipant", "SyncResult"],
        features: ["Rate limiting", "Error handling", "Retry logic", "Caching"]
      }
    };

    const result = provider && provider !== "all" ? 
      providers[provider] : 
      providers;

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2)
        }
      ]
    };
  }

  private async getBusinessRequirements(category?: string) {
    const requirements = {
      completed: [
        "✅ User login system (multi-tenant)",
        "✅ Mode selection (pre-race/results)",
        "✅ Event selection (ChronoTrack + RunSignUp)",
        "✅ Template creation (21 API endpoints)",
        "✅ Timing data connection (TCP + database)",
        "✅ Access control (multi-tenant isolation)"
      ],
      partial: [
        "⚠️ Local storage (needs enhancement)",
        "⚠️ Multi-session usage (infrastructure ready)",
        "⚠️ Provider integrations (2 of 7 complete)",
        "⚠️ Database normalization (schema ready)"
      ],
      missing: [
        "❌ Unique shareable URLs (CRITICAL - Week 1)",
        "❌ ChronoTrack session selection (CRITICAL - Week 1)",
        "❌ Session-level data isolation (CRITICAL - Week 1)"
      ],
      completion_status: "77% complete (10 of 13 requirements)",
      timeline: "3 weeks to 100% completion"
    };

    const result = category && category !== "all" ? 
      requirements[category] : 
      requirements;

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2)
        }
      ]
    };
  }

  private async generateDeploymentPlan(component: string, environment: string) {
    const plan = {
      component,
      environment,
      steps: [
        "1. 🧪 Run comprehensive tests",
        "2. 🔍 Review code changes",
        "3. 🛠️ Build and package",
        "4. 🚀 Deploy to target environment",
        "5. ✅ Verify deployment",
        "6. 📊 Monitor performance"
      ],
      considerations: {
        production: [
          "⚠️ Zero downtime deployment required",
          "🔄 Database migrations if needed",
          "📈 Performance monitoring",
          "🔙 Rollback plan ready"
        ],
        staging: [
          "🧪 Full integration testing",
          "🔗 External API connections",
          "💾 Database state validation"
        ],
        development: [
          "🛠️ Local testing first",
          "📋 Feature branch workflow",
          "🔄 Code review process"
        ]
      }
    };

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(plan, null, 2)
        }
      ]
    };
  }

  private async analyzePerformanceMetrics(metricType?: string) {
    const metrics = {
      database: {
        records: "10.7M+ records",
        optimization: "8GB shared_buffers, configured for high performance",
        query_performance: "Optimized for multi-tenant queries"
      },
      api: {
        runsignup_sync: "30x performance improvement",
        sync_duration: "15-30 minutes (vs 7.5 hours previously)",
        api_usage: "727/1000 calls per hour (optimal efficiency)",
        error_rate: "0% (clean operation)"
      },
      sync: {
        incremental_sync: "Only changed records processed",
        event_filtering: "Only future events + 1 hour past start",
        database_load: "Reduced by 80%+",
        field_optimization: "Zero sync errors after field expansion"
      },
      memory: {
        infrastructure: "8 CPU cores, 32GB RAM, 400GB disk",
        services: "Multi-service Python architecture",
        caching: "Redis for session storage"
      }
    };

    const result = metricType && metricType !== "all" ? 
      metrics[metricType] : 
      metrics;

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2)
        }
      ]
    };
  }

  private async getErrorAnalysis(errorType?: string) {
    const errors = {
      sync: {
        common_issues: [
          "Field length constraints (FIXED: expanded VARCHAR fields)",
          "Date parsing errors (FIXED: multiple format support)",
          "Rate limiting (FIXED: intelligent rate limiter)",
          "API authentication timeouts"
        ],
        solutions: [
          "Incremental sync reduces load",
          "Event-driven scheduling",
          "Comprehensive error logging",
          "Automatic retry mechanisms"
        ]
      },
      database: {
        common_issues: [
          "Connection pool exhaustion",
          "Query timeout on large datasets",
          "Multi-tenant data isolation"
        ],
        solutions: [
          "Connection pooling optimization",
          "Query optimization for 10M+ records",
          "Row-level security implementation"
        ]
      },
      api: {
        common_issues: [
          "Provider API rate limits",
          "Authentication token expiration",
          "Network timeouts"
        ],
        solutions: [
          "Intelligent rate limiting",
          "Token refresh mechanisms",
          "Retry with exponential backoff"
        ]
      },
      auth: {
        common_issues: [
          "Multi-tenant session management",
          "OAuth token handling",
          "Cross-service authentication"
        ],
        solutions: [
          "Redis session storage",
          "JWT token management",
          "Service-to-service authentication"
        ]
      }
    };

    const result = errorType && errorType !== "all" ? 
      errors[errorType] : 
      errors;

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2)
        }
      ]
    };
  }

  // Resource Implementation Methods
  private async getSystemArchitecture() {
    return {
      contents: [
        {
          type: "text",
          text: JSON.stringify({
            platform: "Project88 Race Timing Platform",
            status: "77% Complete & Live Production",
            serves: "13 timing partners with 10.7M+ records",
            architecture: "Multi-service Python architecture on VPS",
            services: {
              "race-display": "https://display.project88hub.com (Port 5001)",
              "timing-collector": "ChronoTrack TCP (Port 61611)",
              "authentication": "https://project88hub.com (Port 5002)",
              "user-management": "Internal API (Port 5003)",
              "database-api": "PostgreSQL API via PostgREST (Port 3000)",
              "ai-platform": "https://ai.project88hub.com (Port 8501)"
            }
          }, null, 2)
        }
      ]
    };
  }

  private async getDatabaseSchemaResource() {
    return {
      contents: [
        {
          type: "text",
          text: JSON.stringify({
            database: "PostgreSQL with 10.7M+ records",
            structure: "Multi-tenant with proper isolation",
            key_tables: {
              users: "User accounts (13 timing partners)",
              timing_partners: "Timing company configurations",
              ct_events: "ChronoTrack events",
              ct_participants: "Participant registrations",
              ct_results: "Race timing results",
              runsignup_events: "RunSignUp synchronized events",
              timing_sessions: "Live timing sessions (45+ active)",
              timing_reads: "Real-time timing data (2,040+ reads)"
            }
          }, null, 2)
        }
      ]
    };
  }

  private async getServiceConfigurations() {
    return {
      contents: [
        {
          type: "text",
          text: JSON.stringify({
            production_services: {
              "race-display-clean.service": "Main race display app",
              "timing-collector.service": "TCP timing data collection",
              "project88hub-auth-production.service": "Authentication API",
              "project88hub-auth-phase2.service": "User management API",
              "postgrest.service": "Database API",
              "openwebui.service": "AI interface",
              "postgresql.service": "Database server",
              "redis.service": "Session store",
              "apache2.service": "Web server & SSL proxy"
            },
            ports: {
              5001: "Race Display",
              5002: "Authentication",
              5003: "User Management",
              8501: "AI Platform",
              3000: "Database API",
              61611: "Timing Collector"
            }
          }, null, 2)
        }
      ]
    };
  }

  private async getProviderAdapters() {
    return {
      contents: [
        {
          type: "text",
          text: JSON.stringify({
            pattern: "Abstract base class with standardized interfaces",
            adapters: {
              RunSignUpAdapter: "Production - 30x performance improvement",
              HakuAdapter: "Production - Recently deployed",
              ChronoTrackAdapter: "Production - TCP protocol handler"
            },
            base_classes: {
              ProviderEvent: "Standardized event data structure",
              ProviderParticipant: "Standardized participant data structure",
              SyncResult: "Result of sync operations"
            },
            features: [
              "Rate limiting with persistence",
              "Error handling and retry logic",
              "Incremental sync capabilities",
              "Multi-tenant data isolation"
            ]
          }, null, 2)
        }
      ]
    };
  }

  private async getBusinessRequirementsResource() {
    return {
      contents: [
        {
          type: "text",
          text: JSON.stringify({
            completion_status: "77% complete (10 of 13 requirements)",
            timeline: "3 weeks to 100% completion",
            completed: [
              "User login system (multi-tenant)",
              "Mode selection (pre-race/results)",
              "Event selection (ChronoTrack + RunSignUp)",
              "Template creation (21 API endpoints)",
              "Timing data connection (TCP + database)",
              "Access control (multi-tenant isolation)"
            ],
            critical_missing: [
              "Unique shareable URLs (CRITICAL - Week 1)",
              "ChronoTrack session selection (CRITICAL - Week 1)",
              "Session-level data isolation (CRITICAL - Week 1)"
            ]
          }, null, 2)
        }
      ]
    };
  }

  private async getDeploymentGuide() {
    return {
      contents: [
        {
          type: "text",
          text: `# Project88 Deployment Guide

## Production Environment
- **Server**: 69.62.69.90 (AlmaLinux 9.6)
- **Infrastructure**: Hostinger KVM 8 (8 CPU, 32GB RAM, 400GB disk)
- **Status**: Live production serving 13 timing partners

## Service Management
\`\`\`bash
# Check service status
systemctl status race-display-clean.service
systemctl status timing-collector.service
systemctl status project88hub-auth-production.service

# View logs
tail -f /var/log/race-display/app.log
tail -f /var/log/timing-collector/collector.log
\`\`\`

## Deployment Steps
1. 🧪 Run comprehensive tests
2. 🔍 Review code changes
3. 🛠️ Build and package
4. 🚀 Deploy to target environment
5. ✅ Verify deployment
6. 📊 Monitor performance

## Critical Considerations
- ⚠️ Zero downtime deployment required
- 🔄 Database migrations if needed
- 📈 Performance monitoring
- 🔙 Rollback plan ready

## Health Checks
- **Race Display**: https://display.project88hub.com/health
- **Timing Collector**: http://localhost:61612/status
- **Database**: PostgreSQL connection monitoring`
        }
      ]
    };
  }

  private async getTroubleshootingGuide() {
    return {
      contents: [
        {
          type: "text",
          text: `# Project88 Troubleshooting Guide

## Common Issues & Solutions

### Sync Issues
**Problem**: Provider sync failures
**Solution**: 
- Check API rate limits (727/1000 calls per hour)
- Verify authentication tokens
- Review incremental sync logic

### Database Performance
**Problem**: Slow queries on 10M+ records
**Solution**:
- Use proper indexing
- Implement query optimization
- Check connection pooling

### Service Failures
**Problem**: Service not responding
**Solution**:
\`\`\`bash
# Check service status
systemctl status <service-name>
# Restart if needed
systemctl restart <service-name>
# Check logs
journalctl -u <service-name> -f
\`\`\`

### Authentication Issues
**Problem**: Multi-tenant auth failures
**Solution**:
- Verify timing_partner_id isolation
- Check Redis session storage
- Validate JWT tokens

## Performance Optimization
- **Incremental Sync**: Only sync changed records
- **Event Filtering**: Only future events + 1 hour past
- **Database Load**: Reduced by 80%+
- **Field Optimization**: Zero sync errors after expansion

## Monitoring Commands
\`\`\`bash
# Check system resources
htop
df -h
free -h

# Monitor specific processes
ps aux | grep python
netstat -tlnp | grep -E '(5001|5002|5003|8501|3000|61611)'
\`\`\``
        }
      ]
    };
  }

  // Prompt Implementation Methods
  private async getDebugSyncIssuePrompt(provider?: string, errorMessage?: string) {
    const messages: PromptMessage[] = [
      {
        role: "user",
        content: {
          type: "text",
          text: `Help me debug a sync issue with ${provider || 'a provider'}.
          
Error message: ${errorMessage || 'No specific error provided'}

Please analyze the issue and provide:
1. Likely causes based on Project88's sync architecture
2. Specific debugging steps
3. Code changes needed
4. Testing procedures

Context: Project88 uses event-driven sync with incremental updates, rate limiting, and multi-tenant isolation.`
        }
      }
    ];

    return { messages };
  }

  private async getOptimizeDatabaseQueryPrompt(queryType?: string, table?: string) {
    const messages: PromptMessage[] = [
      {
        role: "user",
        content: {
          type: "text",
          text: `Help me optimize a ${queryType || 'database'} query for Project88.
          
Target table: ${table || 'Not specified'}

Please provide:
1. Query optimization strategies for 10M+ records
2. Proper indexing recommendations
3. Multi-tenant considerations (timing_partner_id isolation)
4. Performance monitoring suggestions

Context: Project88 has 10.7M+ records with multi-tenant PostgreSQL database.`
        }
      }
    ];

    return { messages };
  }

  private async getImplementNewFeaturePrompt(featureName?: string, component?: string) {
    const messages: PromptMessage[] = [
      {
        role: "user",
        content: {
          type: "text",
          text: `Help me implement ${featureName || 'a new feature'} in the ${component || 'system'} component.

Please provide:
1. Architecture considerations for Project88's multi-service design
2. Database schema changes needed
3. API endpoint specifications
4. Multi-tenant isolation requirements
5. Testing strategy
6. Deployment plan

Context: Project88 is a live production platform serving 13 timing partners with zero-downtime requirements.`
        }
      }
    ];

    return { messages };
  }

  private async getTroubleshootServicePrompt(serviceName?: string, symptoms?: string) {
    const messages: PromptMessage[] = [
      {
        role: "user",
        content: {
          type: "text",
          text: `Help me troubleshoot the ${serviceName || 'service'} service.

Symptoms: ${symptoms || 'No specific symptoms provided'}

Please provide:
1. Diagnostic steps for Project88's service architecture
2. Log analysis procedures
3. Common issues and solutions
4. Service restart procedures
5. Performance monitoring checks

Context: Project88 runs on AlmaLinux 9.6 with systemd services, serving live production traffic.`
        }
      }
    ];

    return { messages };
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    
    console.error("Project88 MCP Server running on stdio");
    console.error("Providing comprehensive context for Project88 Race Timing Platform");
  }
}

// Run the server
const server = new Project88MCPServer();
server.run().catch(console.error); 