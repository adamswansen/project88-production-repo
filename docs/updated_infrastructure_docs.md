# 🏁 Project88Hub VPS - Complete Infrastructure Documentation

## 📋 **Infrastructure Overview**

**VPS Provider**: Hostinger KVM 8  
**Server IP**: `69.62.69.90`  
**Main Domain**: `project88hub.com`  
**OS**: AlmaLinux 9.6 (Sage Margay)  
**Resources**: 8 CPU cores, 32GB RAM, 400GB disk  

**Deployed Applications**:
1. **Race Display System** - Real-time timing display interface with raw timing data storage
2. **AI/NLP Platform** - Natural language race timing database queries
3. **Shared Infrastructure** - PostgreSQL, Apache, SSL certificates

---

## 🎯 **Access Points & Services**

| Service | URL/Address | Purpose | Status |
|---------|-------------|---------|--------|
| **Race Display Web Interface** | `https://display.project88hub.com` | Real-time race timing display | ✅ Active |
| **Race Display Backup** | `https://project88hub.com/race-display/` | Alternative access point | ✅ Active |
| **Timing Data APIs** | `https://display.project88hub.com/api/timing/*` | RESTful timing data access | ✅ Active |
| **AI/NLP Platform** | `https://ai.project88hub.com` | Natural language database queries | ✅ Active |
| **API Database Access** | `https://ai.project88hub.com/api/db/` | PostgREST API endpoint | ✅ Active |
| **Main Website** | `https://project88hub.com` | Main project hub | ✅ Active |
| **Timing System TCP** | `69.62.69.90:61611` | Timing hardware connection | ✅ Active |

---

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Project88Hub VPS Infrastructure                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        Apache Web Server                            │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌───────────────────┐  │  │
│  │  │ display.project │  │ ai.project88hub │  │ project88hub.com  │  │  │
│  │  │ 88hub.com       │  │ .com            │  │                   │  │  │
│  │  │ (Port 80/443)   │  │ (Port 80/443)   │  │ (Port 80/443)     │  │  │
│  │  └─────────────────┘  └─────────────────┘  └───────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                    │                      │                               │
│                    ▼                      ▼                               │
│  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐  │
│  │     Race Display System     │  │        AI/NLP Platform              │  │
│  │  ┌─────────────────────────┐│  │ ┌─────────────────────────────────┐ │  │
│  │  │ Flask App (Port 5000)   ││  │ │ OpenWebUI (Port 8501)           │ │  │
│  │  │ TCP Listener (Port      ││  │ │ PostgREST API (Port 3000)       │ │  │
│  │  │ 61611)                  ││  │ │ FastAPI Server (Port 8000)      │ │  │
│  │  │ React Frontend          ││  │ │ Ollama LLM (Port 11434)         │ │  │
│  │  │ Timing Data APIs        ││  │ └─────────────────────────────────┘ │  │
│  │  └─────────────────────────┘│  └─────────────────────────────────────┘  │
│  └─────────────────────────────┘                     │                    │
│                    │                                 │                    │
│                    ▼                                 ▼                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL Database                              │  │
│  │                        (Port 5432)                                 │  │
│  │                                                                     │  │
│  │  Production Database: project88_myappdb                             │  │
│  │  User: project88_myappuser                                          │  │
│  │  Production Data: 10.6M+ race timing records                       │  │
│  │  Tables: ct_events, ct_participants, ct_results, etc.              │  │
│  │                                                                     │  │
│  │  Raw Timing Database: raw_tag_data                                  │  │
│  │  User: race_timing_user                                             │  │
│  │  Live Data: Real-time timing reads with 30-day retention           │  │
│  │  Tables: timing_sessions, timing_reads, timing_locations, etc.     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      External Integrations                          │  │
│  │                                                                     │  │
│  │  • ChronoTrack Timing Hardware (TCP/IP Port 61611)                 │  │
│  │  • RunSignUp API Integration                                       │  │
│  │  • Race Roster API Integration                                     │  │
│  │  • Multi-tenant Timing Companies                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏁 **System 1: Race Display System**

### **Overview**
Real-time race timing display system with web interface, timing hardware integration, and comprehensive timing data storage.

### **Components**
- **Flask Application**: Python-based web server with timing database integration
- **React Frontend**: Modern responsive UI
- **TCP Listener**: Direct timing hardware connection (ChronoTrack protocol)
- **Raw Timing Database**: Real-time data storage with automatic archival
- **RESTful APIs**: Real-time access to timing data
- **Real-time Updates**: Server-Sent Events (SSE)

### **File Structure**
```
/home/appuser/projects/race_display/
├── app.py                    # Main Flask application (enhanced with timing DB)
├── config.py                 # Application configuration (includes timing DB config)
├── listener.py               # TCP listener for timing data
├── requirements.txt          # Python dependencies (includes psycopg2-binary)
├── venv/                     # Python virtual environment
├── frontend/                 # React frontend
│   ├── dist/                 # Built frontend files
│   ├── src/                  # Source files
│   ├── package.json         # Node.js dependencies
│   └── vite.config.js       # Build configuration
├── logs/                     # Application logs
├── static/                   # Static assets
└── templates/               # Flask templates
```

### **Configuration** (`/home/appuser/projects/race_display/config.py`)
```python
# Flask Application Configuration

# Random messages for display rotation
RANDOM_MESSAGES = [
    "Welcome to Race Display",
    "Real-time timing data",
    "Live race results",
    "Powered by project88hub.com",
    "Timing system connected",
    "Ready for race data"
]

# Protocol Configuration (TCP Server for timing data)
PROTOCOL_CONFIG = {
    'HOST': '0.0.0.0',  # Accept connections from timing systems
    'PORT': 61611,      # Port for timing data
    'BUFFER_SIZE': 1024,
    'TIMEOUT': 30,
    'FIELD_SEPARATOR': '~',
    'FORMAT_ID': 'CT01_33'
}

# Server Configuration (Flask web server)
SERVER_CONFIG = {
    'HOST': '127.0.0.1',  # Internal only, Apache proxies external requests
    'PORT': 5000,         # Flask app port
    'DEBUG': False,       # Set to True for development
    'SECRET_KEY': 'change-this-super-secret-key-in-production-12345',
    'THREADED': True,
    'USE_RELOADER': False
}

# Main Database Configuration (shared PostgreSQL)
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'project88_myappdb',
    'user': 'project88_myappuser',
    'password': 'puctuq-cefwyq-3boqRe'
}

# Raw Tag Data Database Configuration (separate timing database)
RAW_TAG_DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'raw_tag_data',
    'user': 'race_timing_user',
    'password': 'Rt8#mK9$vX2&nQ5@pL7'
}

# Enhanced timing configuration
TIMING_CONFIG = {
    'store_to_database': True,  # Enable database storage
    'auto_create_session': True,  # Automatically create timing session
    'session_name_format': 'Session_%Y%m%d_%H%M%S',  # Session naming format
    'debug_timing': True  # Enable timing debug logs
}
```

### **Raw Timing Database Schema**

The `raw_tag_data` database contains the following tables:

#### **timing_sessions** - Race event sessions
```sql
CREATE TABLE timing_sessions (
    id SERIAL PRIMARY KEY,
    session_name VARCHAR(255) NOT NULL,
    event_name VARCHAR(255),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **timing_locations** - Timing mat locations
```sql
CREATE TABLE timing_locations (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES timing_sessions(id),
    location_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    reader_id VARCHAR(6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **timing_reads** - Raw timing data
```sql
CREATE TABLE timing_reads (
    id BIGSERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES timing_sessions(id),
    location_id INTEGER REFERENCES timing_locations(id),
    sequence_number INTEGER,
    location_name VARCHAR(100),
    tag_code VARCHAR(8) NOT NULL,
    read_time TIME NOT NULL,
    read_date DATE DEFAULT CURRENT_DATE,
    read_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lap_count INTEGER DEFAULT 1,
    reader_id VARCHAR(6),
    gator_number INTEGER DEFAULT 0,
    raw_data TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, sequence_number, location_name)
);
```

#### **connection_log** - Debug and monitoring
```sql
CREATE TABLE connection_log (
    id SERIAL PRIMARY KEY,
    client_ip INET,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disconnected_at TIMESTAMP,
    session_info JSONB,
    message_count INTEGER DEFAULT 0
);
```

#### **timing_reads_archive** - 30-day archival storage
```sql
CREATE TABLE timing_reads_archive (
    LIKE timing_reads INCLUDING ALL,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Performance Indexes**
```sql
-- Performance indexes for fast queries
CREATE INDEX idx_timing_reads_session_location ON timing_reads(session_id, location_id);
CREATE INDEX idx_timing_reads_tag_time ON timing_reads(tag_code, read_timestamp);
CREATE INDEX idx_timing_reads_timestamp ON timing_reads(read_timestamp DESC);
CREATE INDEX idx_timing_reads_location_name ON timing_reads(location_name, read_timestamp);
```

### **Automatic Archival System**
```sql
-- Function for automatic 30-day archival
CREATE OR REPLACE FUNCTION archive_old_timing_data()
RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- Archive data older than 30 days to archive table
    WITH archived AS (
        DELETE FROM timing_reads 
        WHERE read_timestamp < CURRENT_TIMESTAMP - INTERVAL '30 days'
        RETURNING *
    )
    INSERT INTO timing_reads_archive SELECT *, CURRENT_TIMESTAMP FROM archived;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    
    -- Log the archival
    INSERT INTO connection_log (client_ip, session_info, message_count)
    VALUES ('127.0.0.1'::INET, 
            jsonb_build_object('action', 'archive', 'archived_count', archived_count),
            archived_count);
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;
```

### **RESTful API Endpoints**

The enhanced Flask application now includes comprehensive timing data APIs:

#### **Database Status** - `GET /api/timing/database-status`
```json
{
  "database_enabled": true,
  "connected": true,
  "current_session": 1,
  "database_version": "PostgreSQL 13.20...",
  "error": null
}
```

#### **Timing Statistics** - `GET /api/timing/stats`
```json
{
  "success": true,
  "overall": {
    "total_reads": 3,
    "unique_tags": 2,
    "total_locations": 2,
    "first_read": "2025-06-09T23:56:54.459249",
    "last_read": "2025-06-09T23:56:54.459249"
  },
  "by_location": [
    {
      "location_name": "start",
      "read_count": 2,
      "unique_tags": 2,
      "last_read": "2025-06-09T23:56:54.459249"
    }
  ],
  "generated_at": "2025-06-10T00:15:14.135752"
}
```

#### **Recent Timing Reads** - `GET /api/timing/recent-reads?limit=50`
```json
{
  "success": true,
  "reads": [
    {
      "id": 1,
      "session_id": 1,
      "location_name": "start",
      "tag_code": "12345",
      "read_time": "08:00:00",
      "read_timestamp": "2025-06-09T23:56:54.459249",
      "session_name": "Session_20250609_235438",
      "location_description": "Starting Line",
      "seconds_ago": 1099.6853,
      "raw_data": "{\"bib\": \"12345\", \"location\": \"start\"}"
    }
  ],
  "timestamp": "2025-06-10T00:15:14.145391"
}
```

#### **Timing Sessions** - `GET /api/timing/sessions`
```json
{
  "success": true,
  "sessions": [
    {
      "id": 1,
      "session_name": "Session_20250609_235438",
      "event_name": "Live Event",
      "status": "active",
      "created_at": "2025-06-09T23:54:38.070908",
      "total_reads": 3
    }
  ]
}
```

### **ChronoTrack Protocol Integration**

The system supports the ChronoTrack timing protocol:

#### **Protocol Format**
```
CT01_33~sequence~location~bib~time~gator~tagcode~lap
Example: CT01_33~1~start~9478~14:02:15.31~0~0F2A38~1
```

#### **Protocol Configuration**
- **Field Separator**: `~` (tilde)
- **Line Termination**: `\r\n`
- **Format ID**: `CT01_33`
- **TCP Port**: `61611`

### **Service Configuration** (`/etc/systemd/system/race-display.service`)
```ini
[Unit]
Description=Race Display Application
After=network.target postgresql.service

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/projects/race_display
Environment=PATH=/home/appuser/projects/race_display/venv/bin
ExecStart=/home/appuser/projects/race_display/venv/bin/python app.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## 🤖 **System 2: AI/NLP Platform**

### **Overview**
Natural language processing platform for race timing database queries with 10.6M+ production records.

### **Production Database Stats**
- 📊 **10,656,231 total records** across 17 tables
- 🏃 **8,151,553 race results** from real events  
- 👥 **1,765,021 participant records**
- 🏁 **16,931 races** across **12,882 events**
- 🏢 **Multi-tenant platform** serving 13 timing companies
- 🔄 **Active integrations** with RunSignUp, ChronoTrack, Race Roster

### **Components**

#### **1. OpenWebUI** (Port 8501)
- **Version**: 0.6.13
- **Purpose**: Web interface for natural language queries
- **URL**: https://ai.project88hub.com
- **Authentication**: Disabled for development

#### **2. Ollama LLM** (Port 11434)  
- **Model**: Llama 3.1 8B
- **Purpose**: Local language model processing
- **Integration**: Connected to OpenWebUI

#### **3. PostgREST API** (Port 3000)
- **Purpose**: Automatic REST API for PostgreSQL
- **Access**: https://ai.project88hub.com/api/db/
- **Features**: Auto-generated endpoints for database tables

#### **4. FastAPI Server** (Port 8000)
- **Purpose**: Custom business logic and NLP processing
- **Location**: `/root/project88/api/`
- **Features**: Natural language query processing, multi-tenant API

### **FastAPI Project Structure**
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

### **Natural Language Processing Engine**
The AI platform includes sophisticated NLP capabilities:

#### **Query Understanding**
- **Intent Recognition**: 5 types (count, list, find, analyze, compare)
- **Entity Extraction**: Events, times, dates, demographics, metrics
- **SQL Generation**: Optimized PostgreSQL queries with tenant isolation
- **Confidence Scoring**: 0.7-1.0 confidence on test queries

#### **Example Queries Successfully Processed**
- ✅ "How many runners finished the Boston Marathon under 3 hours?" (Intent: count, Confidence: 1.0)
- ✅ "Show me all participants in the Shamrock Marathon last year" (Intent: list, Confidence: 1.0)
- ✅ "Find all male runners aged 35 in the Chicago Marathon" (Intent: list, Confidence: 0.8)
- ✅ "Analyze performance for the Hartford Marathon" (Intent: analyze, Confidence: 0.7)

### **API Endpoints**

#### **FastAPI Endpoints** (Port 8000)
- `GET /` - API information and status
- `GET /health` - Health check  
- `GET /docs` - Swagger UI documentation
- `POST /api/v1/nl-query` - Natural language processing
- `GET /api/v1/nl-examples` - Example queries and tips
- `POST /api/v1/nl-explain` - Query parsing explanation

#### **PostgREST Endpoints** (Port 3000)
- Auto-generated REST endpoints for all database tables
- Example: `GET /ct_events?limit=5` - List events
- Example: `GET /ct_results?race_id=eq.123` - Results for race

---

## 🗄️ **PostgreSQL Database Configuration**

### **Database Overview**

The system uses two PostgreSQL databases for different purposes:

1. **Production Database** (`project88_myappdb`) - Historical race timing data
2. **Raw Timing Database** (`raw_tag_data`) - Live timing data with automatic archival

### **Production Database Configuration**
- **Host**: localhost
- **Port**: 5432
- **Database**: project88_myappdb
- **User**: project88_myappuser  
- **Password**: puctuq-cefwyq-3boqRe
- **Optimization**: 8GB shared_buffers for 10M+ records

### **Raw Timing Database Configuration**
- **Host**: localhost
- **Port**: 5432
- **Database**: raw_tag_data
- **User**: race_timing_user
- **Password**: Rt8#mK9$vX2&nQ5@pL7
- **Purpose**: Real-time timing data storage with 30-day retention

### **Production Schema** (17 Tables)
```sql
-- Core Timing Tables
ct_events           -- Race events
ct_races            -- Individual races within events
ct_participants     -- Participant registrations
ct_results          -- Race timing results

-- Multi-tenant Management  
timing_partners     -- Timing companies
users              -- System users
events             -- Event management

-- External Integrations
runsignup_events    -- RunSignUp integration data
runsignup_participants
runsignup_races
partner_provider_credentials

-- Analytics & Operations
event_weather       -- Weather data correlation
sync_history        -- Data synchronization logs
sync_queue          -- Pending sync operations
providers           -- Integration providers
timing_partner_haku_orgs
```

### **Performance Optimization**
```sql
-- PostgreSQL configuration optimized for production
shared_buffers = 8GB
effective_cache_size = 24GB  
maintenance_work_mem = 2GB
max_connections = 200
```

### **Database Permissions Setup**
```sql
-- Raw timing database permissions
GRANT ALL PRIVILEGES ON DATABASE raw_tag_data TO race_timing_user;
GRANT ALL ON SCHEMA public TO race_timing_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO race_timing_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO race_timing_user;
```

---

## 🌐 **Apache Web Server Configuration**

### **VirtualHost Configurations**

#### **Race Display Subdomain** (`/etc/apache2/conf.d/display-project88hub.conf`)
```apache
<VirtualHost 69.62.69.90:80>
    ServerName display.project88hub.com
    DocumentRoot /home/project88/public_html/display.project88hub.com
    
    # Proxy all requests to Flask application
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
    
    # Proxy timing API endpoints
    ProxyPass /api/timing/ http://127.0.0.1:5000/api/timing/
    ProxyPassReverse /api/timing/ http://127.0.0.1:5000/api/timing/
    
    # Logging
    ErrorLog /var/log/apache2/display_error.log
    CustomLog /var/log/apache2/display_access.log combined
</VirtualHost>
```

#### **AI Platform Subdomain** (`/etc/apache2/conf.d/ai-project88hub.conf`)
```apache
<VirtualHost 69.62.69.90:80>
    ServerName ai.project88hub.com
    DocumentRoot /home/project88/public_html/ai.project88hub.com
    
    # OpenWebUI proxy with WebSocket support
    ProxyPass / http://127.0.0.1:8501/
    ProxyPassReverse / http://127.0.0.1:8501/
    
    # WebSocket support for real-time features
    ProxyPass /ws ws://127.0.0.1:8501/ws
    ProxyPassReverse /ws ws://127.0.0.1:8501/ws
    
    # PostgREST API proxy
    ProxyPass /api/db/ http://127.0.0.1:3000/
    ProxyPassReverse /api/db/ http://127.0.0.1:3000/
    
    # Security headers
    Header always set X-Frame-Options DENY
    Header always set X-Content-Type-Options nosniff
    
    # Logging
    ErrorLog /var/log/apache2/ai_error.log
    CustomLog /var/log/apache2/ai_access.log combined
</VirtualHost>
```

### **SSL Configuration**
- **Provider**: Let's Encrypt
- **Certificates**: All subdomains covered
- **Auto-renewal**: Active via certbot-renew.timer
- **Expiration**: September 6, 2025

---

## 🔧 **System Services Management**

### **Active Services Status**

| Service | Purpose | Status | Port | User |
|---------|---------|--------|------|------|
| `race-display.service` | Race Display Flask App | ✅ Active | 5000 | appuser |
| `openwebui.service` | AI/NLP Web Interface | ✅ Active | 8501 | root |
| `ollama.service` | Local LLM Server | ✅ Active | 11434 | root |
| `httpd.service` | Apache Web Server | ✅ Active | 80/443 | apache |
| `postgresql.service` | Database Server | ✅ Active | 5432 | postgres |

### **Service Management Commands**

#### **Race Display System**
```bash
# Service management
sudo systemctl start race-display
sudo systemctl stop race-display  
sudo systemctl restart race-display
sudo systemctl status race-display

# View logs
sudo journalctl -u race-display -f
```

#### **AI/NLP Platform**
```bash
# OpenWebUI management
sudo systemctl start openwebui
sudo systemctl restart openwebui
sudo systemctl status openwebui

# Ollama management  
sudo systemctl start ollama
sudo systemctl restart ollama
sudo systemctl status ollama

# FastAPI server management (manual process)
cd /root/project88/api
source venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > api.log 2>&1 &

# Check FastAPI process
ps aux | grep uvicorn
tail -f /root/project88/api/api.log
```

#### **Shared Services**
```bash
# Apache web server
sudo systemctl restart httpd
sudo systemctl status httpd

# PostgreSQL database
sudo systemctl restart postgresql
sudo systemctl status postgresql

# SSL certificate renewal
sudo certbot renew
sudo systemctl status certbot-renew.timer
```

---

## 🔐 **Security Configuration**

### **SSL Certificates**
- **Type**: Let's Encrypt
- **Domains**: project88hub.com, display.project88hub.com, ai.project88hub.com
- **Auto-renewal**: Enabled
- **Status**: ✅ Valid until September 6, 2025

### **Firewall (UFW)**
```bash
# Current firewall rules
sudo ufw status verbose

# Key open ports
22/tcp   (SSH)
80/tcp   (HTTP)  
443/tcp  (HTTPS)
61611/tcp (Timing TCP)
```

### **Security Headers**
```apache
# Configured in Apache VirtualHosts
Header always set X-Frame-Options DENY
Header always set X-Content-Type-Options nosniff
Header always set X-XSS-Protection "1; mode=block"
Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
```

### **Database Security**
- User isolation with dedicated credentials for each database
- No external database access
- Row-level security planned for multi-tenant data
- Separate timing database prevents production data interference

### **PostgreSQL Authentication Configuration**
```bash
# pg_hba.conf entries for timing database access
host    raw_tag_data    race_timing_user    127.0.0.1/32    md5
host    raw_tag_data    race_timing_user    ::1/128         md5
```

---

## 🚀 **Complete Deployment Guide**

### **Prerequisites**
- AlmaLinux 9.6 VPS with root access
- Domain name with DNS control
- SSH key authentication configured

### **1. Initial System Setup**
```bash
# Update system
sudo dnf update -y

# Install required packages
sudo dnf install -y python3 python3-pip nodejs npm postgresql postgresql-server apache2 git

# Configure PostgreSQL
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### **2. Database Setup**

#### **Production Database**
```bash
# Create production database and user
sudo -u postgres psql << EOF
CREATE DATABASE project88_myappdb;
CREATE USER project88_myappuser WITH PASSWORD 'puctuq-cefwyq-3boqRe';
GRANT ALL PRIVILEGES ON DATABASE project88_myappdb TO project88_myappuser;
\q
EOF
```

#### **Raw Timing Database**
```bash
# Create timing database and user
sudo -u postgres psql << EOF
CREATE DATABASE raw_tag_data;
CREATE USER race_timing_user WITH PASSWORD 'Rt8#mK9$vX2&nQ5@pL7';
GRANT ALL PRIVILEGES ON DATABASE raw_tag_data TO race_timing_user;
\q
EOF

# Connect to timing database and create schema
sudo -u postgres psql -d raw_tag_data << EOF
-- Create timing sessions table
CREATE TABLE timing_sessions (
    id SERIAL PRIMARY KEY,
    session_name VARCHAR(255) NOT NULL,
    event_name VARCHAR(255),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create timing locations/mats table
CREATE TABLE timing_locations (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES timing_sessions(id),
    location_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    reader_id VARCHAR(6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create main timing reads table
CREATE TABLE timing_reads (
    id BIGSERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES timing_sessions(id),
    location_id INTEGER REFERENCES timing_locations(id),
    sequence_number INTEGER,
    location_name VARCHAR(100),
    tag_code VARCHAR(8) NOT NULL,
    read_time TIME NOT NULL,
    read_date DATE DEFAULT CURRENT_DATE,
    read_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    lap_count INTEGER DEFAULT 1,
    reader_id VARCHAR(6),
    gator_number INTEGER DEFAULT 0,
    raw_data TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, sequence_number, location_name)
);

-- Create connection log table for debugging
CREATE TABLE connection_log (
    id SERIAL PRIMARY KEY,
    client_ip INET,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disconnected_at TIMESTAMP,
    session_info JSONB,
    message_count INTEGER DEFAULT 0
);

-- Create archive table for historical data
CREATE TABLE timing_reads_archive (
    LIKE timing_reads INCLUDING ALL,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create performance indexes
CREATE INDEX idx_timing_reads_session_location ON timing_reads(session_id, location_id);
CREATE INDEX idx_timing_reads_tag_time ON timing_reads(tag_code, read_timestamp);
CREATE INDEX idx_timing_reads_timestamp ON timing_reads(read_timestamp DESC);
CREATE INDEX idx_timing_reads_location_name ON timing_reads(location_name, read_timestamp);

-- Grant permissions to timing user
GRANT ALL ON SCHEMA public TO race_timing_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO race_timing_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO race_timing_user;
\q
EOF

# Add PostgreSQL authentication entries
sudo bash -c 'echo "host    raw_tag_data    race_timing_user    127.0.0.1/32    md5" >> /var/lib/pgsql/data/pg_hba.conf'
sudo bash -c 'echo "host    raw_tag_data    race_timing_user    ::1/128         md5" >> /var/lib/pgsql/data/pg_hba.conf'
sudo systemctl reload postgresql
```

#### **Optimize PostgreSQL for Production**
```bash
sudo nano /var/lib/pgsql/data/postgresql.conf
# Set: shared_buffers = 8GB, effective_cache_size = 24GB
sudo systemctl restart postgresql
```

### **3. Race Display System Deployment**
```bash
# Create application user
sudo useradd -m appuser
sudo usermod -aG wheel appuser

# Switch to appuser and setup application
sudo -u appuser bash
cd /home/appuser
mkdir -p projects
cd projects

# Clone and setup Race Display
git clone https://github.com/adamswansen/race_display.git
cd race_display

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (including timing database support)
pip install -r requirements.txt
pip install flask-cors psycopg2-binary python-dateutil

# Build React frontend
cd frontend
npm install
npm run build
cd ..

# Update requirements.txt
cat > requirements.txt << 'EOF'
flask>=2.3.0
flask-cors>=4.0.0
gunicorn>=21.2.0
beautifulsoup4>=4.12.0
tinycss2==1.2.1
requests>=2.31.0
psycopg2-binary>=2.9.7
python-dateutil>=2.8.2
EOF

# Update config.py with timing database configuration
cat >> config.py << 'EOF'

# Raw Tag Data Database Configuration (separate from main production DB)
RAW_TAG_DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'raw_tag_data',
    'user': 'race_timing_user',
    'password': 'Rt8#mK9$vX2&nQ5@pL7'
}

# Enhanced timing configuration
TIMING_CONFIG = {
    'store_to_database': True,  # Enable database storage
    'auto_create_session': True,  # Automatically create timing session
    'session_name_format': 'Session_%Y%m%d_%H%M%S',  # Session naming format
    'debug_timing': True  # Enable timing debug logs
}
EOF

# Create systemd service
sudo tee /etc/systemd/system/race-display.service > /dev/null << 'EOF'
[Unit]
Description=Race Display Application
After=network.target postgresql.service

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/projects/race_display
Environment=PATH=/home/appuser/projects/race_display/venv/bin
ExecStart=/home/appuser/projects/race_display/venv/bin/python app.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable race-display
sudo systemctl start race-display
```

### **4. AI/NLP Platform Deployment**
```bash
# Install Docker (for OpenWebUI)
sudo dnf install -y docker
sudo systemctl enable docker
sudo systemctl start docker

# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh
sudo systemctl enable ollama
sudo systemctl start ollama

# Pull Llama model
ollama pull llama3.1:8b

# Install OpenWebUI
sudo docker run -d \
  --name openwebui \
  --restart unless-stopped \
  -p 127.0.0.1:8501:8080 \
  -v openwebui:/app/backend/data \
  --add-host=host.docker.internal:host-gateway \
  ghcr.io/open-webui/open-webui:main

# Install PostgREST
sudo dnf install -y postgrest
# Configure PostgREST with database credentials

# Setup FastAPI server
mkdir -p /root/project88/api
cd /root/project88/api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install FastAPI dependencies
pip install fastapi uvicorn psycopg2-binary pydantic python-multipart

# Create FastAPI application structure
# (Copy application files from documentation)

# Start FastAPI server
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > api.log 2>&1 &
```

### **5. Apache Configuration**
```bash
# Create VirtualHost configurations
sudo tee /etc/apache2/conf.d/display-project88hub.conf > /dev/null << 'EOF'
<VirtualHost 69.62.69.90:80>
    ServerName display.project88hub.com
    ProxyPass / http://127.0.0.1:5000/
    ProxyPassReverse / http://127.0.0.1:5000/
    # Proxy timing API endpoints
    ProxyPass /api/timing/ http://127.0.0.1:5000/api/timing/
    ProxyPassReverse /api/timing/ http://127.0.0.1:5000/api/timing/
</VirtualHost>
EOF

sudo tee /etc/apache2/conf.d/ai-project88hub.conf > /dev/null << 'EOF'  
<VirtualHost 69.62.69.90:80>
    ServerName ai.project88hub.com
    ProxyPass / http://127.0.0.1:8501/
    ProxyPassReverse / http://127.0.0.1:8501/
    ProxyPass /api/db/ http://127.0.0.1:3000/
    ProxyPassReverse /api/db/ http://127.0.0.1:3000/
</VirtualHost>
EOF

# Test configuration and restart Apache
sudo /usr/sbin/httpd -t
sudo systemctl restart httpd
```

### **6. SSL Certificate Installation**
```bash
# Install certbot
sudo dnf install -y certbot python3-certbot-apache

# Obtain SSL certificates
sudo certbot --apache -d project88hub.com -d display.project88hub.com -d ai.project88hub.com

# Verify auto-renewal
sudo systemctl enable certbot-renew.timer
sudo systemctl start certbot-renew.timer
```

### **7. DNS Configuration**
Add DNS A records pointing to your VPS IP (69.62.69.90):
- project88hub.com
- display.project88hub.com  
- ai.project88hub.com

---

## 🔍 **Testing & Verification**

### **Race Display System Tests**
```bash
# Test Flask application internally
curl http://127.0.0.1:5000

# Test external access
curl https://display.project88hub.com

# Test timing database API endpoints
curl http://127.0.0.1:5000/api/timing/database-status
curl http://127.0.0.1:5000/api/timing/stats
curl http://127.0.0.1:5000/api/timing/recent-reads
curl http://127.0.0.1:5000/api/timing/sessions

# Test timing TCP port
telnet 69.62.69.90 61611

# Check service status
sudo systemctl status race-display

# View logs
sudo journalctl -u race-display -f
```

### **Timing Database Tests**
```bash
# Test timing database connection
psql -h localhost -U race_timing_user -d raw_tag_data
# Password: Rt8#mK9$vX2&nQ5@pL7

# In PostgreSQL, test schema
\dt
SELECT * FROM timing_sessions;
SELECT * FROM timing_reads LIMIT 5;
\q
```

### **AI/NLP Platform Tests**
```bash
# Test OpenWebUI internally
curl http://127.0.0.1:8501

# Test external access
curl https://ai.project88hub.com

# Test PostgREST API
curl http://127.0.0.1:3000/
curl https://ai.project88hub.com/api/db/

# Test FastAPI server
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/docs

# Test Ollama LLM
curl http://127.0.0.1:11434/api/generate -d '{"model":"llama3.1:8b","prompt":"test"}'
```

### **Database Tests**
```bash
# Connect to production PostgreSQL
psql -h localhost -U project88_myappuser -d project88_myappdb

# Connect to timing PostgreSQL  
psql -h localhost -U race_timing_user -d raw_tag_data

# Test queries
\dt  # List tables
SELECT version();
SELECT COUNT(*) FROM ct_events;  # If tables exist
SELECT COUNT(*) FROM timing_reads;  # Timing database
```

### **SSL & Security Tests**
```bash
# Test SSL certificates
curl -I https://display.project88hub.com
curl -I https://ai.project88hub.com  
curl -I https://project88hub.com

# Check certificate expiration
sudo certbot certificates

# Test security headers
curl -I https://ai.project88hub.com | grep -i "x-frame\|x-content\|strict-transport"
```

---

## 🛠️ **Troubleshooting Guide**

### **Race Display System Issues**

#### **Service Not Starting**
```bash
# Check service status and logs
sudo systemctl status race-display
sudo journalctl -u race-display --no-pager -l

# Check if port is in use
sudo ss -tlnp | grep :5000

# Restart service
sudo systemctl restart race-display
```

#### **Timing Database Connection Issues**
```bash
# Test timing database connection manually
psql -h localhost -U race_timing_user -d raw_tag_data

# Check PostgreSQL authentication
sudo tail -10 /var/lib/pgsql/data/pg_hba.conf | grep raw_tag_data

# Check API endpoints
curl http://127.0.0.1:5000/api/timing/database-status
```

#### **JSON Serialization Issues**
```bash
# Check app logs for serialization errors
sudo journalctl -u race-display -f | grep -i "json\|serial"

# Test individual API endpoints
curl http://127.0.0.1:5000/api/timing/stats
curl http://127.0.0.1:5000/api/timing/recent-reads
```

#### **Timing Connection Issues**
```bash
# Check if application is listening on timing port
sudo ss -tlnp | grep :61611

# Test internal Flask app
curl http://127.0.0.1:5000

# Check application logs for timing data
sudo journalctl -u race-display -f | grep -i timing
```

### **AI/NLP Platform Issues**

#### **OpenWebUI Not Accessible**
```bash
# Check Docker container
sudo docker ps | grep openwebui
sudo docker logs openwebui

# Restart container
sudo docker restart openwebui
```

#### **FastAPI Server Issues**
```bash
# Check if server is running
ps aux | grep uvicorn

# View logs
tail -f /root/project88/api/api.log

# Restart server
pkill -f "uvicorn app.main:app"
cd /root/project88/api && source venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > api.log 2>&1 &
```

#### **Database Connection Issues**
```bash
# Test PostgreSQL connection
psql -h localhost -U project88_myappuser -d project88_myappdb -c "SELECT version();"
psql -h localhost -U race_timing_user -d raw_tag_data -c "SELECT version();"

# Check PostgreSQL status
sudo systemctl status postgresql

# View PostgreSQL logs
sudo journalctl -u postgresql -f
```

### **Apache & SSL Issues**

#### **Apache Configuration Problems**
```bash
# Test Apache configuration
sudo /usr/sbin/httpd -t

# Check VirtualHost setup
sudo /usr/sbin/httpd -S | grep -E "(display|ai)"

# View Apache error logs
tail -20 /var/log/apache2/error_log
tail -10 /var/log/apache2/display_error.log
tail -10 /var/log/apache2/ai_error.log
```

#### **SSL Certificate Issues**
```bash
# Check certificate status
sudo certbot certificates

# Renew certificates manually
sudo certbot renew

# Test renewal timer
sudo systemctl status certbot-renew.timer
```

### **Network & Connectivity Issues**
```bash
# Check open ports
sudo ss -tlnp | grep -E ':(80|443|5000|8501|3000|8000|61611|11434)'

# Test internal connectivity
curl http://127.0.0.1:5000    # Race Display
curl http://127.0.0.1:8501    # OpenWebUI
curl http://127.0.0.1:3000    # PostgREST
curl http://127.0.0.1:8000    # FastAPI
curl http://127.0.0.1:11434   # Ollama

# Check firewall status
sudo ufw status verbose
```

---

## 📊 **System Monitoring & Maintenance**

### **Health Check Commands**
```bash
# System resources
top
htop
free -h
df -h

# Service statuses
systemctl status race-display openwebui ollama httpd postgresql

# Network connections
sudo ss -tlnp

# Process monitoring
ps aux | grep -E "(python|uvicorn|docker|httpd|postgres)"
```

### **Log Monitoring**
```bash
# Real-time log monitoring
sudo journalctl -u race-display -f    # Race Display logs
sudo journalctl -u openwebui -f       # OpenWebUI logs  
sudo journalctl -u ollama -f          # Ollama logs
sudo journalctl -u httpd -f           # Apache logs
tail -f /root/project88/api/api.log   # FastAPI logs

# Error checking
sudo journalctl --since "1 hour ago" | grep -i error
tail -100 /var/log/apache2/error_log | grep -i error
```

### **Performance Monitoring**
```bash
# Database performance
psql -h localhost -U project88_myappuser -d project88_myappdb -c "
SELECT schemaname,tablename,n_live_tup,n_dead_tup 
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC LIMIT 10;"

psql -h localhost -U race_timing_user -d raw_tag_data -c "
SELECT COUNT(*) as total_reads FROM timing_reads;
SELECT COUNT(*) as active_sessions FROM timing_sessions WHERE status = 'active';"

# Disk usage by component
du -sh /home/appuser/projects/race_display
du -sh /root/project88/api
du -sh /var/lib/pgsql/data
docker system df  # Docker usage

# Connection monitoring
sudo ss -s  # Socket statistics
```

### **Timing System Monitoring**
```bash
# Check timing system performance
curl http://127.0.0.1:5000/api/timing/stats | jq '.'
curl http://127.0.0.1:5000/api/timing/database-status | jq '.'

# Monitor timing data flow
sudo journalctl -u race-display -f | grep -E "(timing|TCP|ChronoTrack)"

# Check timing database activity
psql -h localhost -U race_timing_user -d raw_tag_data -c "
SELECT 
    COUNT(*) as total_reads,
    COUNT(DISTINCT session_id) as sessions,
    COUNT(DISTINCT location_name) as locations,
    MAX(read_timestamp) as latest_read
FROM timing_reads;"
```

### **Backup Procedures**
```bash
# Application backups
sudo tar -czf /tmp/race_display_backup_$(date +%Y%m%d).tar.gz /home/appuser/projects/race_display/
sudo tar -czf /tmp/ai_platform_backup_$(date +%Y%m%d).tar.gz /root/project88/api/

# Database backups
sudo -u postgres pg_dump project88_myappdb > /tmp/production_database_backup_$(date +%Y%m%d).sql
sudo -u postgres pg_dump raw_tag_data > /tmp/timing_database_backup_$(date +%Y%m%d).sql

# Configuration backups  
sudo cp /etc/apache2/conf.d/*.conf /tmp/
sudo cp /etc/systemd/system/race-display.service /tmp/
sudo cp /home/appuser/projects/race_display/config.py /tmp/

# SSL certificate backup
sudo cp -r /etc/letsencrypt /tmp/letsencrypt_backup_$(date +%Y%m%d)
```

### **Update Procedures**

#### **Race Display System Updates**
```bash
cd /home/appuser/projects/race_display
git pull origin main
source venv/bin/activate
pip install -r requirements.txt

# Rebuild frontend if needed
cd frontend && npm install && npm run build && cd ..

sudo systemctl restart race-display
```

#### **Timing Database Maintenance**
```bash
# Run archival function (if needed)
psql -h localhost -U race_timing_user -d raw_tag_data -c "
SELECT archive_old_timing_data();"

# Check database size and performance
psql -h localhost -U race_timing_user -d raw_tag_data -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

#### **AI/NLP Platform Updates**
```bash
# Update OpenWebUI
sudo docker pull ghcr.io/open-webui/open-webui:main
sudo docker stop openwebui
sudo docker rm openwebui
# Restart with new image (use deployment command)

# Update Ollama model
ollama pull llama3.1:8b

# Update FastAPI dependencies
cd /root/project88/api && source venv/bin/activate
pip install --upgrade fastapi uvicorn psycopg2-binary
# Restart FastAPI server
```

#### **System Updates**
```bash
# Update AlmaLinux packages
sudo dnf update -y

# Update SSL certificates
sudo certbot renew

# Restart services after updates
sudo systemctl restart httpd postgresql race-display
```

---

## 📋 **Quick Reference**

### **Essential Commands**

| Task | Command |
|------|---------|
| **Restart Race Display** | `sudo systemctl restart race-display` |
| **Restart AI Platform** | `sudo systemctl restart openwebui` |
| **Restart Apache** | `sudo systemctl restart httpd` |
| **Restart Database** | `sudo systemctl restart postgresql` |
| **Check All Services** | `systemctl status race-display openwebui ollama httpd postgresql` |
| **View Race Display Logs** | `sudo journalctl -u race-display -f` |
| **View AI Platform Logs** | `sudo journalctl -u openwebui -f` |
| **Test Configurations** | `sudo /usr/sbin/httpd -t` |
| **Renew SSL Certificates** | `sudo certbot renew` |

### **Important Files & Locations**

| Component | Location | Purpose |
|-----------|----------|---------|
| **Race Display App** | `/home/appuser/projects/race_display/` | Main application |
| **Race Display Config** | `/home/appuser/projects/race_display/config.py` | Flask configuration |
| **AI Platform API** | `/root/project88/api/` | FastAPI server |
| **Apache Configs** | `/etc/apache2/conf.d/` | VirtualHost configurations |
| **Service Files** | `/etc/systemd/system/` | Systemd service definitions |
| **SSL Certificates** | `/etc/letsencrypt/` | Let's Encrypt certificates |
| **Database Data** | `/var/lib/pgsql/data/` | PostgreSQL data directory |

### **Database Credentials Reference**

| Database | User | Password | Purpose |
|----------|------|----------|---------|
| **project88_myappdb** | project88_myappuser | puctuq-cefwyq-3boqRe | Production timing data |
| **raw_tag_data** | race_timing_user | Rt8#mK9$vX2&nQ5@pL7 | Live timing data |

### **Port Reference**

| Port | Service | Access | Purpose |
|------|---------|--------|---------|
| **80/443** | Apache | External | Web traffic (HTTP/HTTPS) |
| **5000** | Flask (Race Display) | Internal | Race display application |
| **8501** | OpenWebUI | Internal | AI/NLP web interface |
| **3000** | PostgREST | Internal | Database REST API |
| **8000** | FastAPI | Internal | Custom business logic API |
| **11434** | Ollama | Internal | Local LLM server |
| **5432** | PostgreSQL | Internal | Database server |
| **61611** | TCP Listener | External | Timing hardware connection |

### **API Endpoints Reference**

| Endpoint | Method | Purpose | Example Response |
|----------|--------|---------|-----------------|
| **`/api/timing/database-status`** | GET | Database connection status | `{"connected": true, "current_session": 1}` |
| **`/api/timing/stats`** | GET | Timing statistics | `{"total_reads": 3, "unique_tags": 2}` |
| **`/api/timing/recent-reads`** | GET | Recent timing reads | `{"reads": [...], "success": true}` |
| **`/api/timing/sessions`** | GET | Active timing sessions | `{"sessions": [...], "success": true}` |

### **Current Status Summary**

| System | Status | Version | Last Updated |
|--------|--------|---------|--------------|
| **Race Display System** | ✅ Operational | Flask 2.3 + Timing DB | June 10, 2025 |
| **Raw Timing Database** | ✅ Operational | PostgreSQL 13 | June 10, 2025 |
| **AI/NLP Platform** | ✅ Operational | OpenWebUI 0.6.13 | June 8, 2025 |
| **Production Database** | ✅ Operational | PostgreSQL 13 | June 7, 2025 |
| **Apache Web Server** | ✅ Operational | Apache 2.4 | June 7, 2025 |
| **SSL Certificates** | ✅ Valid | Let's Encrypt | Expires Sep 6, 2025 |

---

## 🎯 **Production Migration Status**

### **Current Database Migration Progress**
- ✅ **Infrastructure Ready**: VPS optimized for 10M+ records
- ✅ **NLP Engine Complete**: Sophisticated query understanding with 0.7-1.0 confidence
- ✅ **Raw Timing Database**: Live timing data storage with 30-day retention
- ✅ **Timing APIs**: 4 working endpoints for real-time data access
- 🔄 **Database Migration In Progress**: Transferring 6GB production database (10.6M records)
- ⏳ **Multi-tenant API**: FastAPI redesign for production scale pending
- ⏳ **Integration Testing**: Real-world query testing with production data

### **Raw Timing System Capabilities**
With the new timing database integration, users can now:

- **Real-time Data Storage**: All timing hardware data automatically stored
- **Live API Access**: RESTful endpoints for timing statistics and recent reads
- **Session Management**: Automatic organization by race events
- **ChronoTrack Protocol**: Full support for industry-standard timing hardware
- **Automatic Archival**: 30-day retention with historical data preservation
- **Performance Monitoring**: Real-time insights into timing system health

### **End User Experience Goals**
With the production migration complete, users will be able to:

- **Natural Language Queries**: "Show me Michael Wardian's marathon PR" → 02:24:37 from Hartford Marathon
- **Complex Analytics**: "How many people finished under 3 hours in marathons last year?" → Analysis of 8M+ results  
- **Multi-tenant Access**: "I'm from Big River Race Management, show me our active events" → Filtered company data
- **Integration Insights**: "Which RunSignUp events have the highest registration fees?" → Cross-platform analysis
- **Dynamic Reports**: "Generate CSV of Boston qualifiers with contact info" → Real-time data export
- **Live Timing Access**: "What's the current timing data for session 1?" → Real-time race progress

---

**🏁 Project88Hub VPS Infrastructure - Complete Documentation**  
**Document Version**: 2.0  
**Last Updated**: June 10, 2025  
**Status**: Both systems operational with raw timing database integration complete  
**Major Update**: Raw timing database system and API endpoints fully operational  
**Next Phase**: Complete production database migration and multi-tenant API implementation