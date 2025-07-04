# OpenWebUI + PostgreSQL + API Server Setup Documentation

## Project Overview

**UPDATED SCOPE**: This project involves migrating a **production race timing SaaS platform** with 10.6M+ records from SQLite to PostgreSQL and adding natural language capabilities.

**Production Database Stats**:
- 📊 **10,656,231 total records** across 17 tables
- 🏃 **8,151,553 race results** from real events
- 👥 **1,765,021 participant records** 
- 🏁 **16,931 races** across **12,882 events**
- 🏢 **Multi-tenant platform** serving 13 timing companies
- 🔄 **Active integrations** with RunSignUp, ChronoTrack, Race Roster

**Goal**: Create a VPS-hosted system where users can:
- Ask natural language questions to query a race timing database
- Trigger business workflows (data syncing, scoring processes, etc.)
- Access via web interface and mobile apps
- Authenticate through natural language in the LLM interface

**End User Experience Examples (With Production Data)**:
- "Show me Michael Wardian's marathon PR" → 02:24:37 from Hartford Marathon
- "How many people finished under 3 hours in marathons last year?" → Complex analytics on 8M results
- "I'm from Big River Race Management, show me our active events" → Multi-tenant filtered data
- "What's the weather correlation with slow race times?" → Weather data analysis
- "Generate CSV of Boston qualifiers with contact info" → Dynamic report from real data
- "Which RunSignUp events have the highest registration fees?" → Integration data analysis

## Infrastructure Setup

### VPS Specifications
- **Provider**: Hostinger
- **Plan**: KVM 8
- **OS**: AlmaLinux 9.6 (Sage Margay)
- **Resources**: 8 CPU cores, 32GB RAM, 400GB disk
- **IP**: 69.62.69.90
- **Domain**: project88hub.com
- **AI Subdomain**: ai.project88hub.com

## Current Status (June 7, 2025 - Late Evening)

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
- **Schema**: ⚠️ **Tables missing** - need to create ct_events, ct_participants, ct_results, etc.

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

#### 6. Apache Proxy & SSL
- **Status**: ✅ **Production Ready**
- **SSL Certificates**: Let's Encrypt (expires Sep 6, 2025)
- **Domains**: https://ai.project88hub.com, https://project88hub.com
- **Auto-renewal**: Active (certbot-renew.timer running)
- **Security Headers**: Configured
- **WebSocket**: Configured for OpenWebUI integration

#### 7. System Services
- **Status**: ✅ Working
- **Auto-start**: Enabled via systemd
- **Services**: openwebui.service, ollama.service

#### 8. FastAPI Server - **NEW** 🚀
- **Status**: ✅ **Working** (as of June 7, 2025)
- **Port**: 127.0.0.1:8000
- **Location**: `/root/project88/api/`
- **Virtual Environment**: Active (`(venv)` prompt)
- **Dependencies**: fastapi, uvicorn, psycopg2, pydantic
- **Process ID**: 3209899 (running via nohup)
- **Documentation**: http://localhost:8000/docs (Swagger UI working)

### 🚧 CURRENT STATUS - PRODUCTION MIGRATION

**Database Migration In Progress**: Transferring 6GB production database with 10.6M records from laptop to VPS.

**Timeline**:
- ✅ Database analysis complete (17 tables identified)
- 🔄 **File transfer in progress** (race_results.db.gz → VPS)
- ⏳ Migration script ready for execution
- ⏳ FastAPI redesign for production scale
- ⏳ Multi-tenant security implementation
- `ct_events` - relation does not exist
- `ct_participants` - relation does not exist  
- `ct_races` - relation does not exist
- `ct_results` - relation does not exist

### Production Platform Features Discovered 🎯

This is not a simple database - it's a **full race timing SaaS platform** with:
- ✅ **Multi-tenant architecture** (timing_partner_id throughout)
- ✅ **External API integrations** (RunSignUp, ChronoTrack, Race Roster)
- ✅ **Comprehensive sync system** (676k sync history records)
- ✅ **Financial transaction tracking**
- ✅ **Weather data integration** 
- ✅ **Elite race results** (sub-2:30 marathons, major events)
- ✅ **Production credentials** for external services

### ⚠️ LIMITATIONS DISCOVERED

1. **OpenWebUI Functions**: Actually "Filters" for message processing, not tools
2. **OpenWebUI Tools**: Only supports external OpenAI-compatible APIs
3. **MCP Support**: Not available in OpenWebUI
4. **Pipelines**: Not detected/available in current installation
5. **WebSocket**: Issues with Apache proxy configuration

## FastAPI Implementation Details

### Project Structure
```
/root/project88/api/
├── venv/                    # Python virtual environment
├── app/
│   ├── __init__.py
│   ├── main.py             # FastAPI application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   └── database.py     # PostgreSQL connection handling
│   └── routers/
│       ├── __init__.py
│       └── query.py        # Database query endpoints
├── api.log                 # Server logs
└── requirements.txt        # Python dependencies
```

### Current API Endpoints

#### Root Endpoints
- `GET /` - API information and status
- `GET /health` - Health check
- `GET /docs` - Swagger UI documentation (✅ Working)

#### Query Endpoints (prefix: `/api/v1`)
- `GET /api/v1/test` - Simple test endpoint
- `GET /api/v1/events` - List events (⚠️ needs tables)
- `GET /api/v1/participants/count` - Count participants (⚠️ needs tables)
- `POST /api/v1/query` - Execute custom SQL queries (⚠️ needs tables)

### Database Configuration
```python
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "project88_myappdb",
    "user": "project88_myappuser",
    "password": "puctuq-cefwyq-3boqRe"
}
```

### Server Status
- **Running**: ✅ Process 3209899
- **Command**: `nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > api.log 2>&1 &`
- **Logs**: Available in `/root/project88/api/api.log`
- **Auto-reload**: Enabled for development

### CORS Configuration
```python
allow_origins=[
    "https://ai.project88hub.com",
    "http://localhost:3000",
]
```

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

## Implementation Phases

### Phase 1: Infrastructure & Architecture 🚧 **IN PROGRESS**
- [x] Create project structure
- [x] Set up Python virtual environment
- [x] Install FastAPI dependencies (fastapi, uvicorn, psycopg2, pydantic)
- [x] Build FastAPI server with basic endpoints
- [x] Create database connection module
- [x] Create query router for database operations
- [x] Configure CORS for OpenWebUI integration
- [x] Set up development server with auto-reload
- [x] Analyze production database (17 tables, 10.6M records)
- [x] Create production-scale migration script
- [x] **COMPLETED: Install Let's Encrypt SSL certificates**
- [x] **COMPLETED: Configure SSL auto-renewal**
- [ ] **CURRENT: Configure UFW firewall**
- [ ] Optimize PostgreSQL for production
- [ ] Design multi-tenant API architecture
- [ ] Implement authentication framework
- [ ] Create natural language processing framework
- [ ] Set up testing infrastructure

### Phase 2: Database Integration 📋 **PLANNED** (After database cleanup)
- [ ] Migrate production database to PostgreSQL
- [ ] Update FastAPI endpoints for real schema
- [ ] Implement multi-tenant security
- [ ] Test with production data
- [ ] Create OpenWebUI integration

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

## IMMEDIATE NEXT STEPS (Current Infrastructure Focus)

### 1. ✅ SSL Certificate Setup - **COMPLETED**
**Result**: Production Let's Encrypt certificates active
- Both domains: https://ai.project88hub.com & https://project88hub.com
- Auto-renewal configured (expires Sep 6, 2025)
- Security headers implemented

### 2. UFW Firewall Configuration 🔥 **IN PROGRESS**
**Objective**: Lock down VPS ports and improve security
**Time**: 15 minutes
**Impact**: Block unnecessary access, allow only required services

### 3. PostgreSQL Production Optimization ⚡ **NEXT**
**Objective**: Configure PostgreSQL for large dataset migration
**Time**: 10 minutes
**Impact**: Ready for 10M+ record migration when database is complete

### 4. Multi-Tenant API Architecture Design 🏗️ **TODAY**
**Objective**: Design scalable API structure for timing partners
**Time**: 2-3 hours
**Impact**: Production-ready architecture foundation
```sql
-- Production migration will create all 17 tables:
-- Core timing: ct_events, ct_races, ct_participants, ct_results
-- Multi-tenant: timing_partners, users, events
-- Integrations: runsignup_*, partner_provider_credentials
-- Analytics: event_weather, sync_history
-- Management: providers, sync_queue, timing_partner_haku_orgs
```

### 2. FastAPI Production Redesign
**Estimated Time**: 2-3 hours after migration completes
- 🏢 Multi-tenant endpoint structure (/api/v1/{timing_partner_id}/...)
- 🔐 Timing partner authentication and row-level security  
- 📊 Complex race analytics endpoints
- 🔄 Integration management endpoints
- 📈 Performance optimized for 10M+ records

### 3. Natural Language Processing for Production Data
**Estimated Time**: 3-4 hours
Advanced queries possible with real data:
- "Show me all sub-3:00 marathon times from 2024"
- "Which timing partner has the most active events?"
- "What's the average 5K time by age group and gender?"
- "Show weather conditions for races with unusually slow times"

### 4. OpenWebUI Integration
Create filter to call FastAPI from OpenWebUI chat interface.

## Current Working Examples

### API Server Status Check
```bash
# Check if server is running
ps aux | grep uvicorn

# View logs
tail -f /root/project88/api/api.log

# Test endpoints
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### Database Connection Test
```bash
# Connect to PostgreSQL
psql -h localhost -U project88_myappuser -d project88_myappdb

# List tables
\dt

# Test table creation script (pending)
```

### Access Points
- **OpenWebUI**: https://ai.project88hub.com ✅ **SSL Secured**
- **PostgREST API**: https://ai.project88hub.com/api/db/ ✅ **SSL Secured**
- **FastAPI Server**: http://localhost:8000 (docs at /docs)
- **Main Site**: https://project88hub.com ✅ **SSL Secured**
- **Future Public API**: https://api.project88hub.com (to be created)

## Security Considerations

### Current Status
- ✅ SSH key authentication
- ✅ Non-root user for applications
- ✅ PostgreSQL user isolation
- ✅ FastAPI CORS configuration
- ✅ **Production SSL certificates (Let's Encrypt)**
- ✅ **SSL auto-renewal configured**
- ✅ **Security headers implemented**
- 🔄 **UFW firewall setup in progress**
- ⚠️ Authentication disabled in OpenWebUI
- ⚠️ FastAPI running on localhost only

### Production Requirements
- [ ] Let's Encrypt SSL certificate
- [ ] Firewall configuration (UFW)
- [ ] API rate limiting
- [ ] Audit logging
- [ ] Encrypted credential storage
- [ ] GDPR compliance measures

## Important Commands

### FastAPI Server Management
```bash
# Check server status
ps aux | grep uvicorn

# Restart FastAPI server
pkill -f "uvicorn app.main:app"
cd /root/project88/api
source venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > api.log 2>&1 &

# View logs
tail -f api.log

# Test endpoints
curl http://localhost:8000/
curl http://localhost:8000/docs
```

### System Service Management
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
5. **FastAPI Success**: Quick setup, excellent documentation, perfect for our needs
6. **Development Flow**: Virtual environments and auto-reload make development efficient

## Migration Notes

- Existing user credentials will be migrated incrementally
- Test with single organization first
- Keep existing system running during migration
- Data sync will be scheduled, not real-time initially

## Troubleshooting

### FastAPI Server Won't Start
```bash
cd /root/project88/api
source venv/bin/activate
python -c "import fastapi, uvicorn, psycopg2; print('Dependencies OK')"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Database Connection Issues
```bash
psql -h localhost -U project88_myappuser -d project88_myappdb -c "SELECT version();"
```

### OpenWebUI Integration Issues
- Verify CORS settings in FastAPI
- Check that OpenWebUI can reach localhost:8000
- Test endpoints directly first

---

**Document Version**: 5.0  
**Last Updated**: June 8, 2025 - 1:40 AM UTC  
**Updated By**: Development Team  
**Current Phase**: Infrastructure Development - SSL ✅ Complete, Firewall 🔄 In Progress  
**Next Review**: After firewall and PostgreSQL optimization completion  
**Major Achievement**: Production-grade SSL certificates successfully deployed