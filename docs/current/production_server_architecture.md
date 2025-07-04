# Production Server Architecture - Current State

## 🏗️ **Infrastructure Overview**

**VPS Provider**: Hostinger KVM 8  
**Server IP**: `69.62.69.90`  
**Main Domain**: `project88hub.com`  
**OS**: AlmaLinux 9.6 (Sage Margay)  
**Resources**: 8 CPU cores, 32GB RAM, 400GB disk  

**Status**: ✅ **Live Production Environment** serving real customers

---

## 🚀 **Active Production Services**

### **Web Services & Domains**
| Service | URL | Port | Status | Purpose |
|---------|-----|------|--------|---------|
| **Race Display** | https://display.project88hub.com | 5001 | ✅ Live | Real-time race timing display |
| **AI Platform** | https://ai.project88hub.com | 8501 | ✅ Live | Natural language database queries |
| **Main Authentication** | https://project88hub.com | 5002 | ✅ Live | Multi-tenant user authentication |
| **User Management** | Internal API | 5003 | ✅ Live | Subscription and user management |
| **Database API** | Internal API | 3000 | ✅ Live | PostgreSQL API via PostgREST |
| **Timing Collector** | TCP Listener | 61611 | ✅ Live | ChronoTrack hardware data collection |

### **Backend Services**
```bash
# Verified running services:
✅ race-display-clean.service          # Main race display app
✅ timing-collector.service            # TCP timing data collection  
✅ project88hub-auth-production.service # Authentication API
✅ project88hub-auth-phase2.service    # User management API
✅ postgrest.service                   # Database API
✅ openwebui.service                   # AI interface
✅ postgresql.service                  # Database server
✅ redis.service                       # Session store
✅ apache2.service                     # Web server & SSL proxy
```

---

## 📊 **System Architecture Diagram**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Production VPS (69.62.69.90)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        Apache Web Server (SSL)                     │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │  │
│  │  │ display.project │  │ ai.project88hub │  │ project88hub.com  │  │  │
│  │  │ 88hub.com       │  │ .com            │  │                   │  │  │
│  │  │ → Port 5001     │  │ → Port 8501     │  │ → Port 5002       │  │  │
│  │  └─────────────────┘  └─────────────────┘  └───────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                    │                      │                │              │
│                    ▼                      ▼                ▼              │
│  ┌─────────────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │     Race Display        │  │   AI Platform   │  │ Auth & User Mgmt│    │
│  │   (Flask + React)       │  │  (OpenWebUI +   │  │  (Multi-tenant) │    │
│  │                         │  │   Ollama)       │  │                 │    │
│  │ • Template Builder ✅   │  │ • LLM Queries ✅│  │ • User Auth ✅  │    │
│  │ • Live Timing ✅        │  │ • Natural Lang ✅│  │ • Subscriptions✅   │
│  │ • Multi-user ✅         │  │ • PostgreSQL ✅ │  │ • Multi-tenant ✅   │
│  │ • Display Mode ✅       │  │                 │  │                 │    │
│  │                         │  │                 │  │                 │    │
│  │ ❌ Missing Features:    │  │                 │  │                 │    │
│  │ • Unique URLs           │  │                 │  │                 │    │
│  │ • Session Selection     │  │                 │  │                 │    │
│  │ • Data Isolation        │  │                 │  │                 │    │
│  └─────────────────────────┘  └─────────────────┘  └─────────────────┘    │
│                    │                      │                │              │
│                    └──────────────────────┼────────────────┘              │
│                                           ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                   Redis Session Store (Port 6379)                  │  │
│  │                                                                     │  │
│  │  • User session management                                          │  │
│  │  • Template caching                                                 │  │
│  │  • Real-time pub/sub                                                │  │
│  │  ❌ Missing: Session-level data isolation                           │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                           ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL Database (Port 5432)                 │  │
│  │                                                                     │  │
│  │  ✅ PRODUCTION DATABASE: project88_myappdb                          │  │
│  │  • User accounts and subscriptions                                  │  │
│  │  • Payment history and usage tracking                              │  │
│  │  • Multi-tenant access control                                     │  │
│  │  • 10.7M+ migrated timing records                                  │  │
│  │                                                                     │  │
│  │  ✅ RAW TIMING DATABASE: raw_tag_data                               │  │
│  │  • Live timing sessions (45+ active)                               │  │
│  │  • Real-time timing reads (2,040+ processed)                       │  │
│  │  • 30-day data retention policy                                    │  │
│  │                                                                     │  │
│  │  ❌ MISSING TABLES FOR NEW FEATURES:                                │  │
│  │  • display_urls (unique URL generation)                            │  │
│  │  • display_sessions (session isolation)                            │  │
│  │  • session_timing_streams (stream isolation)                       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                ▲                                           │
│                                │                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │              ChronoTrack Timing Collector Service                   │  │
│  │                          ✅ FULLY OPERATIONAL                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ Python TCP Service (Always Running)                        │  │  │
│  │  │ • TCP Listener (Port 61611) - ChronoTrack Protocol        │  │  │
│  │  │ • Status API (Port 61612) - Internal monitoring           │  │  │
│  │  │ • Database Writer - Direct to raw_tag_data                │  │  │
│  │  │ • 24/7 Operation - Independent of web services            │  │  │
│  │  │                                                             │  │  │
│  │  │ ❌ MISSING SESSION FEATURES:                                │  │  │
│  │  │ • Session listing API for builder interface                │  │  │
│  │  │ • Session selection and binding capability                 │  │  │
│  │  │ • Session data preview functionality                       │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ **Service Details**

### **Race Display Application** (Port 5001)
- **Framework**: Flask backend + React frontend
- **Status**: ✅ Production ready
- **Features**: Template builder, live timing, multi-user support
- **Process**: Gunicorn with 4 workers
- **Location**: `/home/appuser/projects/race_display_clean/`

### **Timing Collector Service** (Port 61611)
- **Protocol**: ChronoTrack TCP
- **Status**: ✅ 24/7 operational  
- **Data Flow**: Hardware → TCP → PostgreSQL → Display
- **Process**: Standalone Python service
- **Location**: `/home/appuser/projects/timing-collector/`

### **Authentication Services** (Ports 5002, 5003)
- **Multi-tenant**: 13 timing partners active
- **Features**: User management, subscriptions, payment tracking
- **Status**: ✅ Production ready
- **Location**: `/home/appuser/projects/project88hub_auth/`

### **AI Platform** (Port 8501)
- **Framework**: OpenWebUI + Ollama
- **Models**: DeepSeek-R1, Llama 3.1
- **Features**: Natural language database queries
- **Status**: ✅ Operational
- **Location**: `/opt/openwebui/`

---

## 📊 **Database Architecture**

### **PostgreSQL Configuration**
- **Version**: PostgreSQL 14+
- **Databases**: 
  - `project88_myappdb` (main application data)
  - `raw_tag_data` (live timing data)
- **Users**: Multi-tenant with proper isolation
- **Optimization**: Configured for 10.7M+ records

### **Key Database Tables**
```sql
-- Main Application Database
users                    -- User accounts (13 timing partners)
timing_partners          -- Timing company configurations  
user_subscriptions       -- Active subscriptions
payment_history          -- Transaction tracking
user_templates           -- Custom race templates

-- Raw Timing Database  
timing_sessions          -- Live timing sessions (45+ active)
timing_reads            -- Real-time timing data (2,040+ reads)
timing_locations        -- Hardware location configurations
```

---

## 🔄 **Deployment & Monitoring**

### **Service Management**
```bash
# Service status checking
systemctl status race-display-clean.service
systemctl status timing-collector.service  
systemctl status project88hub-auth-production.service

# Log monitoring
tail -f /var/log/race-display/app.log
tail -f /var/log/timing-collector/collector.log
```

### **Health Checks**
- **Race Display**: https://display.project88hub.com/health
- **Timing Collector**: http://localhost:61612/status
- **Database**: PostgreSQL connection monitoring
- **SSL Certificates**: Auto-renewal via Let's Encrypt

### **Backup Strategy**
- **Database**: Daily PostgreSQL dumps
- **Application Files**: Git-based version control
- **Configuration**: Automated backup of service configs
- **Monitoring**: Systemd service status monitoring

---

## 🔧 **Development Environment**

### **Local Development Setup**
```bash
# Clone and setup applications
git clone <repo> 
cd apps/race-display/race_display_clean
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment configuration
cp .env.example .env
# Configure database connections and API keys
```

### **Production Deployment Process**
1. **Testing**: Staging environment validation
2. **Deployment**: Zero-downtime service updates
3. **Monitoring**: Real-time health checks
4. **Rollback**: Automated rollback procedures

---

## 🚨 **Critical Production Notes**

⚠️ **LIVE CUSTOMER DATA**: This system serves real timing partners with live race events. All changes must be tested thoroughly.

⚠️ **ZERO DOWNTIME**: Services are interconnected. Use proper deployment procedures to maintain service availability.

⚠️ **DATA INTEGRITY**: Multi-tenant isolation is critical. Test all changes for data leakage between timing partners.

⚠️ **SECURITY**: All services run with proper security contexts. Maintain principle of least privilege.

---

**Status**: Live Production Environment | **Uptime**: 99.9%+ | **Users**: 13 Active Timing Partners 