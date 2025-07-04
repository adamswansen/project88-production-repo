# 🏁 Project88Hub VPS - Complete Infrastructure Documentation

## 📋 **Infrastructure Overview**

**VPS Provider**: Hostinger KVM 8  
**Server IP**: `69.62.69.90`  
**Main Domain**: `project88hub.com`  
**OS**: AlmaLinux 9.6 (Sage Margay)  
**Resources**: 8 CPU cores, 32GB RAM, 400GB disk  

**Deployed Applications**:
1. **Race Display System** - Real-time timing display interface
2. **AI/NLP Platform** - Natural language race timing database queries
3. **Shared Infrastructure** - PostgreSQL, Apache, SSL certificates

---

## 🎯 **Access Points & Services**

| Service | URL/Address | Purpose | Status |
|---------|-------------|---------|--------|
| **Race Display Web Interface** | `https://display.project88hub.com` | Real-time race timing display | ✅ Active |
| **Race Display Backup** | `https://project88hub.com/race-display/` | Alternative access point | ✅ Active |
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
│  │  └─────────────────────────┘│  │ └─────────────────────────────────┘ │  │
│  └─────────────────────────────┘  └─────────────────────────────────────┘  │
│                    │                      │                               │
│                    └──────────────────────┼───────────────────────────────┤
│                                           ▼                               │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL Database                              │  │
│  │                        (Port 5432)                                 │  │
│  │                                                                     │  │
│  │  Database: project88_myappdb                                        │  │
│  │  User: project88_myappuser                                          │  │
│  │  Production Data: 10.6M+ race timing records                       │  │
│  │  Tables: ct_events, ct_participants, ct_results, etc.              │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      External Integrations                          │  │
│  │                                                                     │  │
│  │  • Timing Hardware Systems (TCP/IP)                                │  │
│  │  • RunSignUp API Integration                                       │  │
│  │  • Race Roster API Integration                                     │  │
│  │  • ChronoTrack Integration                                         │  │
│  │  • Multi-tenant Timing Companies                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🏁 **System 1: Race Display System**

### **Overview**
Real-time race timing display system with web interface and timing hardware integration.

### **Components**
- **Flask Application**: Python-based web server
- **React Frontend**: Modern responsive UI
- **TCP Listener**: Direct timing hardware connection
- **Real-time Updates**: Server-Sent Events (SSE)

### **File Structure**
```
/home/appuser/projects/race_display/
├── app.py                    # Main Flask application
├── config.py                 # Application configuration
├── listener.py               # TCP listener for timing data
├── requirements.txt          # Python dependencies
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
    'TIMEOUT': 30
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

# Database Configuration (shared PostgreSQL)
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'project88_myappdb',
    'user': 'project88_myappuser',
    'password': 'puctuq-cefwyq-3boqRe'
}
```

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

## 🗄️ **Shared PostgreSQL Database**

### **Database Configuration**
- **Host**: localhost
- **Port**: 5432
- **Database**: project88_myappdb
- **User**: project88_myappuser  
- **Password**: puctuq-cefwyq-3boqRe
- **Optimization**: 8GB shared_buffers for 10M+ records

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
- User isolation with dedicated credentials
- No external database access
- Row-level security planned for multi-tenant data

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
```bash
# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE project88_myappdb;
CREATE USER project88_myappuser WITH PASSWORD 'puctuq-cefwyq-3boqRe';
GRANT ALL PRIVILEGES ON DATABASE project88_myappdb TO project88_myappuser;
\q
EOF

# Optimize PostgreSQL for production
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

# Install dependencies
pip install -r requirements.txt
pip install flask-cors

# Build React frontend
cd frontend
npm install
npm run build
cd ..

# Create config file
cp config.py.example config.py
# Edit config.py with database credentials

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

# Test timing TCP port
telnet 69.62.69.90 61611

# Check service status
sudo systemctl status race-display

# View logs
sudo journalctl -u race-display -f
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
# Connect to PostgreSQL
psql -h localhost -U project88_myappuser -d project88_myappdb

# Test queries
\dt  # List tables
SELECT version();
SELECT COUNT(*) FROM ct_events;  # If tables exist
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

#### **Timing Connection Issues**
```bash
# Check if application is listening on timing port
sudo ss -tlnp | grep :61611

# Test internal Flask app
curl http://127.0.0.1:5000

# Check application logs for timing data
sudo journalctl -u race-display -f
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

# Disk usage by component
du -sh /home/appuser/projects/race_display
du -sh /root/project88/api
du -sh /var/lib/pgsql/data
docker system df  # Docker usage

# Connection monitoring
sudo ss -s  # Socket statistics
```

### **Backup Procedures**
```bash
# Application backups
sudo tar -czf /tmp/race_display_backup_$(date +%Y%m%d).tar.gz /home/appuser/projects/race_display/
sudo tar -czf /tmp/ai_platform_backup_$(date +%Y%m%d).tar.gz /root/project88/api/

# Database backup
sudo -u postgres pg_dump project88_myappdb > /tmp/database_backup_$(date +%Y%m%d).sql

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
sudo systemctl restart httpd postgresql
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

### **Current Status Summary**

| System | Status | Version | Last Updated |
|--------|--------|---------|--------------|
| **Race Display System** | ✅ Operational | Flask 2.3 | June 9, 2025 |
| **AI/NLP Platform** | ✅ Operational | OpenWebUI 0.6.13 | June 8, 2025 |
| **PostgreSQL Database** | ✅ Operational | PostgreSQL 13 | June 7, 2025 |
| **Apache Web Server** | ✅ Operational | Apache 2.4 | June 7, 2025 |
| **SSL Certificates** | ✅ Valid | Let's Encrypt | Expires Sep 6, 2025 |

---

## 🎯 **Production Migration Status**

### **Current Database Migration Progress**
- ✅ **Infrastructure Ready**: VPS optimized for 10M+ records
- ✅ **NLP Engine Complete**: Sophisticated query understanding with 0.7-1.0 confidence
- 🔄 **Database Migration In Progress**: Transferring 6GB production database (10.6M records)
- ⏳ **Multi-tenant API**: FastAPI redesign for production scale pending
- ⏳ **Integration Testing**: Real-world query testing with production data

### **End User Experience Goals**
With the production migration complete, users will be able to:

- **Natural Language Queries**: "Show me Michael Wardian's marathon PR" → 02:24:37 from Hartford Marathon
- **Complex Analytics**: "How many people finished under 3 hours in marathons last year?" → Analysis of 8M+ results  
- **Multi-tenant Access**: "I'm from Big River Race Management, show me our active events" → Filtered company data
- **Integration Insights**: "Which RunSignUp events have the highest registration fees?" → Cross-platform analysis
- **Dynamic Reports**: "Generate CSV of Boston qualifiers with contact info" → Real-time data export

---

**🏁 Project88Hub VPS Infrastructure - Complete Documentation**  
**Document Version**: 1.0  
**Last Updated**: June 9, 2025  
**Status**: Both systems operational and production-ready  
**Next Phase**: Complete production database migration and multi-tenant API implementation