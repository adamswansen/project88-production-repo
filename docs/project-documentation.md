# OpenWebUI + PostgreSQL + API Server Setup Documentation

## Project Overview

**Goal**: Create a VPS-hosted system where users can:
- Ask natural language questions to query a race timing database
- Trigger business workflows (data syncing, scoring processes, etc.)
- Access via web interface and mobile apps
- Authenticate through natural language in the LLM interface

**End User Experience Examples:**
- "How many runners finished the Shamrock Marathon last year?" → Database query
- "Score Boston Marathon in Copernico" → Workflow trigger + Lambda calls
- "I'm John from Acme Racing, show me my events" → Authentication + filtered data
- "Generate CSV of award winners with mailing addresses" → Dynamic report generation

## Infrastructure Setup

### VPS Specifications
- **Provider**: Hostinger
- **Plan**: KVM 8
- **OS**: AlmaLinux 9.6 (Sage Margay)
- **Resources**: 8 CPU cores, 32GB RAM, 400GB disk
- **IP**: 69.62.69.90
- **Domain**: project88hub.com
- **AI Subdomain**: ai.project88hub.com

## Current Status (June 7, 2025)

### ✅ COMPLETED COMPONENTS

#### 1. SSH Access
- **Status**: ✅ Working
- **Key Type**: ED25519 keypair
- **Users**: root, appuser (with sudo)
- **Location**: ~/.ssh/id_ed25519

#### 2. PostgreSQL Database
- **Status**: ✅ Working
- **Version**: PostgreSQL 13
- **Database**: project88_myappdb
- **User**: project88_myappuser
- **Password**: puctuq-cefwyq-3boqRe
- **Schema**: Race timing database (ct_events, ct_participants, ct_results, etc.)

#### 3. PostgREST API
- **Status**: ✅ Working
- **Port**: 127.0.0.1:3000
- **Access**: https://ai.project88hub.com/api/db/

#### 4. OpenWebUI
- **Status**: ✅ Working
- **Version**: 0.6.13
- **Port**: 127.0.0.1:8501
- **URL**: https://ai.project88hub.com
- **Auth**: Disabled for development
- **Secret Key**: Auto-generated

#### 5. Local LLM (Ollama)
- **Status**: ✅ Working
- **Model**: Llama 3.1 8B
- **Port**: 127.0.0.1:11434
- **Integration**: Connected to OpenWebUI

#### 6. Apache Proxy
- **Status**: ✅ Working
- **SSL**: Self-signed certificate (needs Let's Encrypt)
- **WebSocket**: Configured but not fully working

#### 7. System Services
- **Status**: ✅ Working
- **Auto-start**: Enabled via systemd
- **Services**: openwebui.service, ollama.service

### ⚠️ LIMITATIONS DISCOVERED

1. **OpenWebUI Functions**: Actually "Filters" for message processing, not tools
2. **OpenWebUI Tools**: Only supports external OpenAI-compatible APIs
3. **MCP Support**: Not available in OpenWebUI
4. **Pipelines**: Not detected/available in current installation
5. **WebSocket**: Issues with Apache proxy configuration

## New Architecture Plan

### System Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                        VPS Server                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐     ┌─────────────────────────────┐  │
│  │   OpenWebUI     │────▶│    Race Timing API         │  │
│  │  (Local LLM)    │     │   (FastAPI + Auth)         │  │
│  └─────────────────┘     └──────────┬──────────────────┘  │
│                                     │                      │
│  ┌─────────────────┐     ┌─────────▼──────────────────┐  │
│  │ Mobile Apps     │────▶│   PostgreSQL Database      │  │
│  │ (React Native)  │     │   (Multi-tenant)           │  │
│  └─────────────────┘     └──────────┬──────────────────┘  │
│                                     │                      │
│  ┌─────────────────────────────────▼──────────────────┐  │
│  │          Background Services                        │  │
│  ├─────────────────────────────────────────────────────┤  │
│  │ • Registration Scheduler (pre-event)                │  │
│  │ • Results Scheduler (post-event)                   │  │
│  │ • Report Generator                                 │  │
│  │ • KML/Geospatial Processor                        │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │          External Integrations                      │  │
│  │  RunSignUp, RaceRoster, Copernico, CTLive          │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **API Server Approach**: Build a FastAPI server to handle all business logic
2. **Authentication**: Natural language through LLM ("I'm John from Acme Racing")
3. **Multi-tenancy**: Row-level security in PostgreSQL
4. **Mobile**: React Native with Expo for easy cross-platform development
5. **Deployment**: All on VPS, minimize AWS dependencies
6. **Code Management**: GitHub repository with CI/CD

## Implementation Phases

### Phase 1: Core API Development 🚧 IN PROGRESS
- [ ] Create GitHub repository structure
- [ ] Build FastAPI server with basic endpoints
- [ ] Implement natural language query processing
- [ ] Connect to PostgreSQL with proper pooling
- [ ] Create OpenWebUI filter to call API

### Phase 2: Authentication & Multi-tenancy 📋 PLANNED
- [ ] Design multi-tenant database schema
- [ ] Implement LLM-based authentication
- [ ] Add row-level security
- [ ] Create organization/user management

### Phase 3: Schedulers & Workflows 📋 PLANNED
- [ ] Registration sync scheduler (pre-event)
- [ ] Results sync scheduler (post-event)
- [ ] Systemd timers for automation
- [ ] Workflow orchestration system

### Phase 4: External Integrations 📋 PLANNED
- [ ] RunSignUp API integration
- [ ] RaceRoster API integration
- [ ] Copernico scoring integration
- [ ] CTLive integration

### Phase 5: Mobile Application 📋 PLANNED
- [ ] React Native setup with Expo
- [ ] API client implementation
- [ ] Natural language interface
- [ ] Push notifications for results

### Phase 6: Advanced Features 📋 PLANNED
- [ ] KML file processing for course analysis
- [ ] Dynamic report generation from natural language
- [ ] Predictive analytics
- [ ] Real-time result updates

## Current Working Examples

### Database Query Filter (Temporary Solution)
```python
# In OpenWebUI Functions as a Filter
# Allows queries like "Query database: SELECT COUNT(*) FROM ct_participants"
# Limited but functional for testing
```

### Access Points
- **OpenWebUI**: https://ai.project88hub.com
- **PostgREST API**: https://ai.project88hub.com/api/db/
- **Future API**: https://api.project88hub.com (to be created)

## Next Immediate Steps

1. **Create GitHub Repository**
   ```bash
   mkdir race-timing-system
   cd race-timing-system
   git init
   # Create folder structure
   ```

2. **Set up FastAPI Server**
   ```bash
   cd api
   python -m venv venv
   pip install fastapi uvicorn sqlalchemy
   ```

3. **Design Multi-tenant Schema**

4. **Create First Natural Language Endpoint**

## Security Considerations

### Current Status
- ✅ SSH key authentication
- ✅ Non-root user for applications
- ✅ PostgreSQL user isolation
- ⚠️ Self-signed SSL certificate
- ⚠️ No firewall rules configured
- ⚠️ Authentication disabled in OpenWebUI

### Production Requirements
- [ ] Let's Encrypt SSL certificate
- [ ] Firewall configuration (UFW)
- [ ] API rate limiting
- [ ] Audit logging
- [ ] Encrypted credential storage
- [ ] GDPR compliance measures

## Important Commands

### Service Management
```bash
# Check service status
sudo systemctl status openwebui.service ollama.service

# Restart services
sudo systemctl restart openwebui.service
sudo systemctl restart httpd

# View logs
sudo journalctl -u openwebui.service -f
```

### Database Access
```bash
# Connect to PostgreSQL
psql -h localhost -U project88_myappuser -d project88_myappdb

# Test PostgREST
curl http://localhost:3000/ct_events?limit=5
```

## Lessons Learned

1. **OpenWebUI Limitations**: Not designed for complex integrations, better as a UI layer
2. **MCP Not Suitable**: Designed for desktop apps, not web platforms
3. **API Server Necessity**: Required for proper business logic and integrations
4. **Database Queries**: Need proper abstraction layer, not direct SQL in chat

## Migration Notes

- Existing user credentials will be migrated incrementally
- Test with single organization first
- Keep existing system running during migration
- Data sync will be scheduled, not real-time initially

---

**Document Version**: 2.0  
**Last Updated**: June 7, 2025  
**Updated By**: Development Team  
**Next Review**: After Phase 1 completion