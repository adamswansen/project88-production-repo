#!/usr/bin/env node

/**
 * Project88 MCP Server - Simplified Working Version
 * A comprehensive Model Context Protocol server for Project88 Race Timing Platform
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  PromptMessage,
  TextContent,
} from "@modelcontextprotocol/sdk/types.js";

class Project88MCPServer {
  private server: Server;

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

    this.setupHandlers();
  }

  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "analyze_system",
            description: "Analyze the Project88 system architecture and current status",
            inputSchema: {
              type: "object",
              properties: {
                component: {
                  type: "string",
                  description: "Specific component to analyze (optional)",
                }
              }
            }
          },
          {
            name: "get_project_info",
            description: "Get comprehensive Project88 project information",
            inputSchema: {
              type: "object",
              properties: {}
            }
          }
        ],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "analyze_system":
          return this.analyzeSystem(args?.component as string);
        case "get_project_info":
          return this.getProjectInfo();
        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });

    // List available resources
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return {
        resources: [
          {
            uri: "project88://overview",
            name: "Project88 Overview",
            description: "Complete overview of the Project88 race timing platform",
            mimeType: "application/json"
          },
          {
            uri: "project88://architecture",
            name: "System Architecture",
            description: "Detailed system architecture and service information",
            mimeType: "application/json"
          }
        ],
      };
    });

    // Handle resource requests
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const uri = request.params.uri;
      
      switch (uri) {
        case "project88://overview":
          return this.getProjectOverview();
        case "project88://architecture":
          return this.getSystemArchitecture();
        default:
          throw new Error(`Unknown resource: ${uri}`);
      }
    });
  }

  // Tool implementations
  private async analyzeSystem(component?: string) {
    const systemInfo = {
      platform: "Project88 Race Timing Platform",
      status: "77% Complete & Live Production",
      completion: "10 of 13 business requirements complete",
      timeline: "3 weeks to 100% completion",
      
      services: {
        "race-display": {
          url: "https://display.project88hub.com",
          port: 5001,
          technology: "Flask + React",
          status: "✅ Production"
        },
        "timing-collector": {
          port: 61611,
          protocol: "ChronoTrack TCP",
          technology: "Python",
          status: "✅ Production 24/7"
        },
        "authentication": {
          url: "https://project88hub.com",
          port: 5002,
          technology: "Multi-tenant Python",
          status: "✅ Production"
        },
        "ai-platform": {
          url: "https://ai.project88hub.com",
          port: 8501,
          technology: "OpenWebUI + Ollama",
          status: "✅ Production"
        }
      },

      infrastructure: {
        server: "69.62.69.90",
        os: "AlmaLinux 9.6",
        resources: "8 CPU cores, 32GB RAM, 400GB disk",
        database: "PostgreSQL with 10.7M+ records",
        users: "13 timing partners"
      },

      critical_missing: [
        "Unique shareable URLs (CRITICAL - Week 1)",
        "ChronoTrack session selection (CRITICAL - Week 1)", 
        "Session-level data isolation (CRITICAL - Week 1)"
      ]
    };

    if (component) {
      const serviceInfo = systemInfo.services[component as keyof typeof systemInfo.services];
      if (serviceInfo) {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({ component, ...serviceInfo }, null, 2)
            }
          ]
        };
      }
    }

    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(systemInfo, null, 2)
        }
      ]
    };
  }

  private async getProjectInfo() {
    const projectInfo = {
      name: "Project88 Race Timing Platform",
      description: "Live production SaaS platform serving 13 timing partners",
      scale: "10.7M+ records across 45+ timing sessions",
      
      key_features: [
        "Real-time race timing display",
        "Multi-tenant user authentication", 
        "Provider integrations (RunSignUp, Haku, ChronoTrack)",
        "Natural language AI queries",
        "24/7 timing data collection"
      ],

      recent_achievements: [
        "30x performance improvement in sync operations",
        "Event-driven scheduler deployed successfully", 
        "Zero sync errors after database optimization",
        "Comprehensive provider integration system"
      ],

      next_priorities: [
        "Implement unique shareable URLs",
        "Add ChronoTrack session selection",
        "Enhance session-level data isolation"
      ],

      technology_stack: {
        backend: "Python (FastAPI, Flask)",
        frontend: "React, Node.js", 
        database: "PostgreSQL, Redis",
        ai: "OpenWebUI, Ollama, LLM models",
        infrastructure: "VPS (AlmaLinux 9.6)"
      }
    };

    return {
      content: [
        {
          type: "text" as const,
          text: JSON.stringify(projectInfo, null, 2)
        }
      ]
    };
  }

  // Resource implementations
  private async getProjectOverview() {
    return {
      contents: [
        {
          type: "text" as const,
          text: JSON.stringify({
            project: "Project88 Race Timing Platform",
            status: "Live Production SaaS Platform",
            completion: "77% (10 of 13 business requirements)",
            timeline: "3 weeks to 100% completion",
            scale: "13 timing partners, 10.7M+ records",
            
            current_production_services: {
              race_display: "https://display.project88hub.com",
              ai_platform: "https://ai.project88hub.com", 
              authentication: "https://project88hub.com",
              timing_collector: "ChronoTrack TCP (Port 61611)"
            },

            recent_major_achievements: [
              "30x performance improvement in provider sync",
              "Event-driven scheduler successfully deployed",
              "Zero sync errors after database field optimization"
            ],

            immediate_priorities: [
              "Unique shareable URLs (Week 1)",
              "ChronoTrack session selection (Week 1)",
              "Session-level data isolation (Week 1)"
            ]
          }, null, 2)
        }
      ]
    };
  }

  private async getSystemArchitecture() {
    return {
      contents: [
        {
          type: "text" as const,
          text: JSON.stringify({
            architecture: "Multi-service Python architecture on VPS",
            infrastructure: {
              server: "69.62.69.90 (AlmaLinux 9.6)",
              resources: "8 CPU cores, 32GB RAM, 400GB disk",
              database: "PostgreSQL with 10.7M+ records"
            },
            
            production_services: {
              race_display: "Port 5001 - Flask + React",
              timing_collector: "Port 61611 - ChronoTrack TCP", 
              authentication: "Port 5002 - Multi-tenant Python",
              user_management: "Port 5003 - User & subscription API",
              ai_platform: "Port 8501 - OpenWebUI + Ollama",
              database_api: "Port 3000 - PostgreSQL via PostgREST"
            },

            provider_integrations: {
              runsignup: "✅ Production - 30x performance improvement",
              haku: "✅ Production - Recently deployed", 
              chronotrack: "✅ Production - TCP protocol handler"
            },

            database_tables: {
              user_data: "users, timing_partners, user_subscriptions",
              race_data: "ct_events, ct_races, ct_participants, ct_results",
              provider_data: "runsignup_events, runsignup_participants",
              live_timing: "timing_sessions, timing_reads, raw_tag_data"
            }
          }, null, 2)
        }
      ]
    };
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    
    console.error("Project88 MCP Server running on stdio");
    console.error("Providing context for Project88 Race Timing Platform");
  }
}

// Run the server
const server = new Project88MCPServer();
server.run().catch(console.error);

export { Project88MCPServer }; 