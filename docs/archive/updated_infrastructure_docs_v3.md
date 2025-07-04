# 🏁 Project88Hub VPS - Complete Infrastructure Documentation v3.0

## 📋 **Infrastructure Overview**

**VPS Provider**: Hostinger KVM 8  
**Server IP**: `69.62.69.90`  
**Main Domain**: `project88hub.com`  
**OS**: AlmaLinux 9.6 (Sage Margay)  
**Resources**: 8 CPU cores, 32GB RAM, 400GB disk  

**Deployed Applications**:
1. **ChronoTrack Timing Collector** - 24/7 timing data collection service (NEW ARCHITECTURE)
2. **Race Display System** - Real-time timing display web interface
3. **AI/NLP Platform** - Natural language race timing database queries
4. **Shared Infrastructure** - PostgreSQL, Apache, SSL certificates

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
| **ChronoTrack TCP Collector** | `69.62.69.90:61611` | Hardware timing data collection | ✅ Active 24/7 |
| **Timing Collector Status** | `127.0.0.1:61612` | Internal collector monitoring | ✅ Active |

---

## 🏗️ **System Architecture v3.0**

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
│  │  │ React Frontend          ││  │ │ PostgREST API (Port 3000)       │ │  │
│  │  │ Timing Data APIs        ││  │ │ FastAPI Server (Port 8000)      │ │  │
│  │  │ (Reads from Database)   ││  │ │ Ollama LLM (Port 11434)         │ │  │
│  │  └─────────────────────────┘│  │ └─────────────────────────────────┘ │  │
│  └─────────────────────────────┘  └─────────────────────────────────────┘  │
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
│                                ▲                                           │
│                                │                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │              ChronoTrack Timing Collector Service                   │  │
│  │                          (NEW ARCHITECTURE)                        │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ Standalone Python Service (Always Running)                 │  │  │
│  │  │ • TCP Listener (Port 61611) - ChronoTrack Protocol        │  │  │
│  │  │ • Status API (Port 61612) - Internal monitoring           │  │  │
│  │  │ • Database Writer - Direct to raw_tag_data                │  │  │
│  │  │ • Session Management - Automatic timing sessions          │  │  │
│  │  │ • Protocol Handshake - Proper ChronoTrack timing delays   │  │  │
│  │  │ • 24/7 Operation - Independent of web display             │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                ▲                                           │
│                                │                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      External Integrations                          │  │
│  │                                                                     │  │
│  │  • ChronoTrack Timing Hardware (TCP/IP Port 61611) - Always Available │  │
│  │  • RunSignUp API Integration                                       │  │
│  │  • Race Roster API Integration                                     │  │
│  │  • Multi-tenant Timing Companies                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ **NEW: ChronoTrack Timing Collector Service**

### **Overview**
Dedicated 24/7 service for ChronoTrack timing hardware connections, completely separate from the web display system.

### **Key Features**
- **Always Available**: Runs 24/7 regardless of web app status
- **ChronoTrack Protocol**: Full handshake with proper timing delays
- **Automatic Sessions**: Creates timing sessions automatically
- **Database Integration**: Direct writes to `raw_tag_data` database
- **Status Monitoring**: Built-in HTTP API for health checks
- **Lightweight**: Minimal resource usage (typically <15MB RAM)

### **File Structure**
```
/home/appuser/projects/timing-collector/
├── collector.py              # Main timing collector service
├── requirements.txt          # Python dependencies (psycopg2-binary)
├── venv/                     # Python virtual environment
└── collector.py.backup       # Backup versions
```

### **Service Configuration** (`/etc/systemd/system/timing-collector.service`)
```ini
[Unit]
Description=ChronoTrack Timing Data Collector
After=network.target postgresql.service

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/projects/timing-collector
Environment=PATH=/home/appuser/projects/timing-collector/venv/bin
ExecStart=/home/appuser/projects/timing-collector/venv/bin/python collector.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### **ChronoTrack Protocol Handling**

#### **Handshake Sequence with Proper Timing**
```python
# 1. Read ChronoTrack greeting
# 2. Send server response with 0.5s initial delay
# 3. Send settings individually with 0.1s delays between each
# 4. Send protocol commands with 0.2s delays
# 5. Wait for acknowledgments and data
```

#### **Protocol Configuration**
```python
PROTOCOL_CONFIG = {
    'HOST': '0.0.0.0',          # Accept external connections
    'PORT': 61611,              # ChronoTrack standard port
    'FIELD_SEPARATOR': '~',     # Tilde separator
    'LINE_TERMINATOR': '\r\n',  # Carriage return + line feed
    'FORMAT_ID': 'CT01_33'      # ChronoTrack format identifier
}
```

### **Status API Endpoints**

#### **Health Check** - `GET http://127.0.0.1:61612/health`
```json
{
  "status": "healthy",
  "timestamp": "2025-06-10T15:16:33.080736"
}
```

#### **Detailed Status** - `GET http://127.0.0.1:61612/status`
```json
{
  "service": "timing-collector",
  "status": "running",
  "tcp_port": 61611,
  "connections": 1,
  "total_reads": 25,
  "current_session": 2,
  "timestamp": "2025-06-10T15:16:33.068869",
  "database_connected": true
}
```

---

## 🏁 **UPDATED: Race Display System**

### **Overview**
Pure web application focused on timing data visualization and APIs, now reads from timing collector's database.

### **Components**
- **Flask Application**: Python-based web server (NO TCP functionality)
- **React Frontend**: Modern responsive UI
- **Timing Database Reader**: Reads from `raw_tag_data` populated by collector
- **RESTful APIs**: Real-time access to timing data
- **Real-time Updates**: Server-Sent Events (SSE)

### **File Structure** (Unchanged)
```
/home/appuser/projects/race_display/
├── app.py                    # Main Flask application (TCP removed)
├── config.py                 # Application configuration
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

### **Updated Configuration** (`/home/appuser/projects/race_display/config.py`)
```python
# Flask Application Configuration (TCP functionality removed)

# Random messages for display rotation
RANDOM_MESSAGES = [
    "Welcome to Race Display",
    "Real-time timing data",
    "Live race results",
    "Powered by project88hub.com",
    "Timing system connected",
    "Ready for race data"
]

# Server Configuration (Flask web server only)
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

# Raw Tag Data Database Configuration (reads from timing collector)
RAW_TAG_DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'raw_tag_data',
    'user': 'race_timing_user',
    'password': 'Rt8#mK9$vX2&nQ5@pL7'
}

# Timing collector integration
TIMING_COLLECTOR_CONFIG = {
    'status_api_url': 'http://127.0.0.1:61612',
    'health_check_interval': 30  # seconds
}
```

### **Service Configuration** (`/etc/systemd/system/race-display.service`)
```ini
[Unit]
Description=Race Display Web Application
After=network.target postgresql.service timing-collector.service

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

**Note**: The race display service now depends on `timing-collector.service` and no longer handles TCP connections.

---

## 🔧 **Updated System Services Management**

### **Active Services Status**

| Service | Purpose | Status | Port | User | Dependencies |
|---------|---------|--------|------|------|--------------|
| `timing-collector.service` | ChronoTrack TCP Collection | ✅ Active | 61611/61612 | appuser | postgresql |
| `race-display.service` | Race Display Web App | ✅ Active | 5000 | appuser | timing-collector |
| `openwebui.service` | AI/NLP Web Interface | ✅ Active | 8501 | root | ollama |
| `ollama.service` | Local LLM Server | ✅ Active | 11434 | root | - |
| `httpd.service` | Apache Web Server | ✅ Active | 80/443 | apache | - |
| `postgresql.service` | Database Server | ✅ Active | 5432 | postgres | - |

### **Service Management Commands**

#### **ChronoTrack Timing Collector** (NEW)
```bash
# Service management
sudo systemctl start timing-collector
sudo systemctl stop timing-collector  
sudo systemctl restart timing-collector
sudo systemctl status timing-collector

# View logs
sudo journalctl -u timing-collector -f

# Check status API
curl http://127.0.0.1:61612/status
curl http://127.0.0.1:61612/health

# Test TCP connection
telnet 69.62.69.90 61611
echo "test" | nc 69.62.69.90 61611
```

#### **Race Display System** (UPDATED)
```bash
# Service management
sudo systemctl start race-display
sudo systemctl stop race-display  
sudo systemctl restart race-display
sudo systemctl status race-display

# View logs
sudo journalctl -u race-display -f

# Test web interface
curl http://127.0.0.1:5000
curl http://127.0.0.1:5000/api/timing/stats
```

#### **Service Dependencies**
```bash
# Start services in correct order
sudo systemctl start postgresql
sudo systemctl start timing-collector  # Must be before race-display
sudo systemctl start race-display
sudo systemctl start httpd

# Restart all project88 services
sudo systemctl restart timing-collector race-display httpd
```

---

## 🔐 **Updated Security Configuration**

### **Firewall (UFW)**
```bash
# Current firewall rules (updated)
sudo ufw status verbose

# Key open ports
22/tcp    (SSH)
80/tcp    (HTTP)  
443/tcp   (HTTPS)
61611/tcp (ChronoTrack TCP Collector) # CRITICAL FOR TIMING
```

### **Port Reference** (UPDATED)

| Port | Service | Access | Purpose |
|------|---------|--------|---------|
| **80/443** | Apache | External | Web traffic (HTTP/HTTPS) |
| **5000** | Flask (Race Display) | Internal | Race display web application |
| **8501** | OpenWebUI | Internal | AI/NLP web interface |
| **3000** | PostgREST | Internal | Database REST API |
| **8000** | FastAPI | Internal | Custom business logic API |
| **11434** | Ollama | Internal | Local LLM server |
| **5432** | PostgreSQL | Internal | Database server |
| **61611** | ChronoTrack Collector | External | Hardware timing data (24/7 active) |
| **61612** | Collector Status API | Internal | Timing collector monitoring |

---

## 🚀 **Updated Deployment Guide**

### **Prerequisites** (Unchanged)
- AlmaLinux 9.6 VPS with root access
- Domain name with DNS control
- SSH key authentication configured

### **1. Initial System Setup** (Unchanged)
```bash
# Update system and install packages
sudo dnf update -y
sudo dnf install -y python3 python3-pip nodejs npm postgresql postgresql-server apache2 git
sudo postgresql-setup --initdb
sudo systemctl enable postgresql httpd
sudo systemctl start postgresql httpd
```

### **2. Database Setup** (Unchanged)
```bash
# Create both production and timing databases
# (Same as previous documentation)
```

### **3. NEW: ChronoTrack Timing Collector Deployment**
```bash
# Create timing collector directory
sudo mkdir -p /home/appuser/projects/timing-collector
sudo chown appuser:appuser /home/appuser/projects/timing-collector
cd /home/appuser/projects/timing-collector

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary

# Create collector.py (use the complete script from earlier)
cat > collector.py << 'EOF'
[Complete timing collector script with proper delays]
EOF

chmod +x collector.py

# Create systemd service
sudo tee /etc/systemd/system/timing-collector.service > /dev/null << 'EOF'
[Complete service configuration from above]
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable timing-collector
sudo systemctl start timing-collector

# Verify operation
sudo systemctl status timing-collector
curl http://127.0.0.1:61612/status
```

### **4. UPDATED: Race Display System Deployment**
```bash
# Modify existing race display to remove TCP functionality
cd /home/appuser/projects/race_display

# Update app.py to remove TCP listener code
# Update config.py to add timing collector integration
# Update dependencies if needed

# Restart race display service
sudo systemctl restart race-display
```

### **5. Apache and SSL Configuration** (Unchanged)
```bash
# Same as previous documentation
```

---

## 🔍 **Updated Testing & Verification**

### **ChronoTrack Timing Collector Tests** (NEW)
```bash
# Test timing collector service
sudo systemctl status timing-collector
curl http://127.0.0.1:61612/status
curl http://127.0.0.1:61612/health

# Test TCP port availability
sudo ss -tlnp | grep :61611
telnet 69.62.69.90 61611

# Test ChronoTrack protocol
echo -e "init\r\n" | nc 69.62.69.90 61611

# Monitor real-time connections
sudo journalctl -u timing-collector -f

# Test database connectivity
psql -h localhost -U race_timing_user -d raw_tag_data -c "SELECT COUNT(*) FROM timing_sessions;"
```

### **Race Display System Tests** (UPDATED)
```bash
# Test web application (no TCP functionality)
curl http://127.0.0.1:5000
curl https://display.project88hub.com

# Test timing data APIs (reading from collector database)
curl http://127.0.0.1:5000/api/timing/database-status
curl http://127.0.0.1:5000/api/timing/stats
curl http://127.0.0.1:5000/api/timing/recent-reads
curl http://127.0.0.1:5000/api/timing/sessions

# Check service status
sudo systemctl status race-display
```

### **Integration Tests** (NEW)
```bash
# Test service dependencies
sudo systemctl status timing-collector race-display

# Test data flow (collector -> database -> web app)
# 1. Send test data to collector
echo "CT01_33~1~start~9478~14:02:15.31~0~0F2A38~1" | nc 69.62.69.90 61611

# 2. Check if data appears in database
psql -h localhost -U race_timing_user -d raw_tag_data -c "SELECT * FROM timing_reads ORDER BY read_timestamp DESC LIMIT 3;"

# 3. Check if web app can read the data
curl http://127.0.0.1:5000/api/timing/recent-reads
```

---

## 🛠️ **Updated Troubleshooting Guide**

### **ChronoTrack Timing Collector Issues** (NEW)

#### **Service Not Starting**
```bash
# Check service status and logs
sudo systemctl status timing-collector
sudo journalctl -u timing-collector --no-pager -l

# Check if ports are in use
sudo ss -tlnp | grep -E ':61611|:61612'

# Test database connection
psql -h localhost -U race_timing_user -d raw_tag_data -c "SELECT version();"
```

#### **ChronoTrack Connection Issues**
```bash
# Test external connectivity
telnet 69.62.69.90 61611
nc -zv 69.62.69.90 61611

# Check firewall
sudo ufw status | grep 61611

# Monitor connection attempts
sudo journalctl -u timing-collector -f | grep -i "connected\|disconnected"

# Test handshake timing
echo -e "init\r\n" | nc 69.62.69.90 61611
```

#### **Protocol Handshake Issues**
```bash
# Enable debug logging
sed -i 's/level=logging.INFO/level=logging.DEBUG/' /home/appuser/projects/timing-collector/collector.py
sudo systemctl restart timing-collector

# Monitor detailed protocol exchange
sudo journalctl -u timing-collector -f | grep -E ">>\|<<"
```

### **Race Display System Issues** (UPDATED)

#### **Service Not Reading Timing Data**
```bash
# Check if timing collector is running
sudo systemctl status timing-collector
curl http://127.0.0.1:61612/status

# Test race display database connection
curl http://127.0.0.1:5000/api/timing/database-status

# Check timing data exists
psql -h localhost -U race_timing_user -d raw_tag_data -c "SELECT COUNT(*) FROM timing_reads;"
```

### **Service Dependency Issues** (NEW)
```bash
# Check service startup order
sudo systemctl list-dependencies timing-collector
sudo systemctl list-dependencies race-display

# Restart services in correct order
sudo systemctl restart postgresql
sudo systemctl restart timing-collector
sudo systemctl restart race-display
```

---

## 📊 **Updated System Monitoring & Maintenance**

### **Health Check Commands** (UPDATED)
```bash
# System resources
top
htop
free -h
df -h

# Service statuses (updated)
systemctl status timing-collector race-display openwebui ollama httpd postgresql

# Network connections (updated ports)
sudo ss -tlnp | grep -E ':61611|:61612|:5000|:8501'

# Process monitoring (updated)
ps aux | grep -E "(collector|python|uvicorn|docker|httpd|postgres)"
```

### **Log Monitoring** (UPDATED)
```bash
# Real-time log monitoring
sudo journalctl -u timing-collector -f    # ChronoTrack collector logs
sudo journalctl -u race-display -f        # Race Display logs (no TCP)
sudo journalctl -u openwebui -f           # OpenWebUI logs  
sudo journalctl -u ollama -f              # Ollama logs
sudo journalctl -u httpd -f               # Apache logs
tail -f /root/project88/api/api.log       # FastAPI logs

# Error checking (updated)
sudo journalctl --since "1 hour ago" | grep -i error
sudo journalctl -u timing-collector --since "1 hour ago" | grep -i error
```

### **ChronoTrack Timing Monitoring** (NEW)
```bash
# Check timing collector performance
curl http://127.0.0.1:61612/status | jq '.'

# Monitor timing data flow
sudo journalctl -u timing-collector -f | grep -E "(Connected|timing data|Stored)"

# Check timing database activity
psql -h localhost -U race_timing_user -d raw_tag_data -c "
SELECT 
    COUNT(*) as total_reads,
    COUNT(DISTINCT session_id) as sessions,
    COUNT(DISTINCT location_name) as locations,
    MAX(read_timestamp) as latest_read
FROM timing_reads;"

# Monitor real-time connections
watch "curl -s http://127.0.0.1:61612/status | jq '.connections, .total_reads'"
```

---

## 📋 **Updated Quick Reference**

### **Essential Commands** (UPDATED)

| Task | Command |
|------|---------|
| **Restart ChronoTrack Collector** | `sudo systemctl restart timing-collector` |
| **Restart Race Display** | `sudo systemctl restart race-display` |
| **Restart AI Platform** | `sudo systemctl restart openwebui` |
| **Restart Apache** | `sudo systemctl restart httpd` |
| **Restart Database** | `sudo systemctl restart postgresql` |
| **Check All Services** | `systemctl status timing-collector race-display openwebui ollama httpd postgresql` |
| **View Collector Logs** | `sudo journalctl -u timing-collector -f` |
| **View Race Display Logs** | `sudo journalctl -u race-display -f` |
| **Check Collector Status** | `curl http://127.0.0.1:61612/status` |
| **Test ChronoTrack Connection** | `telnet 69.62.69.90 61611` |

### **Important Files & Locations** (UPDATED)

| Component | Location | Purpose |
|-----------|----------|---------|
| **ChronoTrack Collector** | `/home/appuser/projects/timing-collector/` | Standalone timing service |
| **Collector Config** | `/home/appuser/projects/timing-collector/collector.py` | Service configuration |
| **Race Display App** | `/home/appuser/projects/race_display/` | Web application |
| **Race Display Config** | `/home/appuser/projects/race_display/config.py` | Flask configuration |
| **AI Platform API** | `/root/project88/api/` | FastAPI server |
| **Apache Configs** | `/etc/apache2/conf.d/` | VirtualHost configurations |
| **Collector Service** | `/etc/systemd/system/timing-collector.service` | Collector systemd service |
| **Display Service** | `/etc/systemd/system/race-display.service` | Display systemd service |
| **SSL Certificates** | `/etc/letsencrypt/` | Let's Encrypt certificates |
| **Database Data** | `/var/lib/pgsql/data/` | PostgreSQL data directory |

### **Port Reference** (UPDATED)

| Port | Service | Access | Purpose |
|------|---------|--------|---------|
| **80/443** | Apache | External | Web traffic (HTTP/HTTPS) |
| **5000** | Flask (Race Display) | Internal | Race display web application |
| **8501** | OpenWebUI | Internal | AI/NLP web interface |
| **3000** | PostgREST | Internal | Database REST API |
| **8000** | FastAPI | Internal | Custom business logic API |
| **11434** | Ollama | Internal | Local LLM server |
| **5432** | PostgreSQL | Internal | Database server |
| **61611** | ChronoTrack Collector | External | Hardware timing data (24/7 active) |
| **61612** | Collector Status API | Internal | Timing collector monitoring |

### **API Endpoints Reference** (UPDATED)

| Endpoint | Method | Purpose | Example Response |
|----------|--------|---------|-----------------|
| **`/api/timing/database-status`** | GET | Database connection status | `{"connected": true, "current_session": 1}` |
| **`/api/timing/stats`** | GET | Timing statistics | `{"total_reads": 3, "unique_tags": 2}` |
| **`/api/timing/recent-reads`** | GET | Recent timing reads | `{"reads": [...], "success": true}` |
| **`/api/timing/sessions`** | GET | Active timing sessions | `{"sessions": [...], "success": true}` |
| **`http://127.0.0.1:61612/status`** | GET | Collector service status | `{"service": "timing-collector", "connections": 1}` |
| **`http://127.0.0.1:61612/health`** | GET | Collector health check | `{"status": "healthy"}` |

### **Current Status Summary** (UPDATED)

| System | Status | Version | Architecture | Last Updated |
|--------|--------|---------|--------------|--------------|
| **ChronoTrack Timing Collector** | ✅ Operational | Python 3.9 + psycopg2 | Standalone Service | June 10, 2025 |
| **Race Display System** | ✅ Operational | Flask 2.3 (TCP Removed) | Pure Web App | June 10, 2025 |
| **Raw Timing Database** | ✅ Operational | PostgreSQL 13 + 24/7 Collection | Collector → Database | June 10, 2025 |
| **AI/NLP Platform** | ✅ Operational | OpenWebUI 0.6.13 | Independent Service | June 8, 2025 |
| **Production Database** | ✅ Operational | PostgreSQL 13 | 10.6M Records | June 7, 2025 |
| **Apache Web Server** | ✅ Operational | Apache 2.4 | Proxy + SSL | June 7, 2025 |
| **SSL Certificates** | ✅ Valid | Let's Encrypt | Auto-Renew | Expires Sep 6, 2025 |

---

## 🎯 **Architecture Benefits - Separated Services**

### **Key Improvements in v3.0**
- ✅ **Rock-Solid Timing Collection**: ChronoTrack collector runs 24/7 regardless of web app status
- ✅ **Independent Scaling**: Race display can restart without affecting timing data collection
- ✅ **Better Resource Management**: Lightweight collector vs full web application
- ✅ **Easier Debugging**: Separate logs and configurations for each service
- ✅ **Future-Ready**: Perfect foundation for multiple display apps or event management tools

### **ChronoTrack Hardware Setup**
Configure your ChronoTrack timing equipment with these settings:
- **Target IP**: `69.62.69.90`
- **Port**: `61611`
- **Protocol**: TCP
- **Status**: ✅ Ready to receive data immediately with proper handshake timing

### **Service Interaction Flow**
```
ChronoTrack Hardware → Timing Collector → Raw Database ← Race Display → Web Interface
                           ↓                                    ↓
                    Status API (61612)                 Timing APIs (5000)
```

---

**🏁 Project88Hub VPS Infrastructure - Complete Documentation v3.0**  
**Document Version**: 3.0  
**Last Updated**: June 10, 2025  
**Status**: All systems operational with separated timing collector architecture  
**Major Update**: ChronoTrack timing collector now runs as independent 24/7 service  
**Architecture**: Timing collection and web display completely separated for maximum reliability