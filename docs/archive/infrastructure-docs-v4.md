# 🏁 Project88Hub VPS - Complete Infrastructure Documentation v4.0

## 📋 **Infrastructure Overview**

**VPS Provider**: Hostinger KVM 8  
**Server IP**: `69.62.69.90`  
**Main Domain**: `project88hub.com`  
**OS**: AlmaLinux 9.6 (Sage Margay)  
**Resources**: 8 CPU cores, 32GB RAM, 400GB disk  

**Deployed Applications**:
1. **ChronoTrack Timing Collector** - 24/7 timing data collection service ✅ OPERATIONAL
2. **Race Display System** - Real-time timing display web interface (Currently offline - needs restart)
3. **AI/NLP Platform** - Natural language race timing database queries
4. **Shared Infrastructure** - PostgreSQL, Apache, SSL certificates

## 🤖 **AI/NLP Platform - OPERATIONAL**

### **Overview**
OpenWebUI interface for natural language queries against race timing data using Ollama and local LLMs.

### **Configuration**
- **Service**: OpenWebUI v0.6.13
- **Port**: 8501 (proxied through Apache)
- **Authentication**: **DISABLED** (`WEBUI_AUTH=False`)
- **LLM Backend**: Ollama with DeepSeek-R1 and other models
- **Data Access**: PostgREST API to PostgreSQL databases

### **Installed Models**
- **DeepSeek-R1**: Advanced reasoning model (downloaded June 9)
- **Llama 3.1 8B**: General purpose model
- Additional models available via Ollama

### **Service File** (`/etc/systemd/system/openwebui.service`)
```ini
[Unit]
Description=Open WebUI Service
After=network.target ollama.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/home/appuser/openwebui
Environment=PATH=/home/appuser/openwebui-venv/bin:/usr/local/bin:/usr/bin:/bin
Environment=WEBUI_SECRET_KEY_FILE=/home/appuser/openwebui/.webui_secret_key
Environment=OLLAMA_BASE_URL=http://localhost:11434
Environment=WEBUI_AUTH=False
Environment=DEFAULT_MODELS=llama3.1:8b
Environment=ENABLE_OLLAMA_API=True
ExecStart=/home/appuser/openwebui-venv/bin/open-webui serve --host 127.0.0.1 --port 8501
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### **Common Issues & Solutions**
- **Login Screen Appears**: Clear browser cache/cookies (auth is disabled)
- **High CPU Usage**: Normal during model downloads/extraction
- **Memory Usage**: Each model requires 8-16GB RAM when loaded

### **Completed Fixes (June 10, 2025)**

1. **Firewall Configuration** ✅
   ```bash
   # Added iptables rule for ChronoTrack
   sudo iptables -I INPUT 1 -p tcp --dport 61611 -j ACCEPT
   # Note: Need to save permanently with:
   sudo sh -c 'iptables-save > /etc/sysconfig/iptables'
   ```

2. **Timestamp Parser Fix** ✅
   - Modified `/home/appuser/projects/timing-collector/collector.py`
   - Splits ISO timestamp (`2025-06-01T09:23:22.03`) into:
     - date: `2025-06-01`
     - time: `09:23:22.03`

3. **AI Platform Access** ✅
   - Authentication is disabled (`WEBUI_AUTH=False`)
   - Clear browser cache if login screen appears
   - Access directly at https://ai.project88hub.com

---

## 🎯 **Access Points & Services**

| Service | URL/Address | Purpose | Status |
|---------|-------------|---------|--------|
| **Race Display Web Interface** | `https://display.project88hub.com` | Real-time race timing display | ⚠️ Needs restart |
| **Race Display Backup** | `https://project88hub.com/race-display/` | Alternative access point | ⚠️ Needs restart |
| **Timing Data APIs** | `https://display.project88hub.com/api/timing/*` | RESTful timing data access | ⚠️ Needs restart |
| **AI/NLP Platform** | `https://ai.project88hub.com` | Natural language database queries | ✅ Active (No Auth) |
| **API Database Access** | `https://ai.project88hub.com/api/db/` | PostgREST API endpoint | ✅ Active |
| **Main Website** | `https://project88hub.com` | Main project hub | ✅ Active |
| **ChronoTrack TCP Collector** | `69.62.69.90:61611` | Hardware timing data collection | ✅ Active 24/7 |
| **Timing Collector Status** | `127.0.0.1:61612` | Internal collector monitoring | ✅ Active |

---

## 🏗️ **System Architecture v4.0**

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
│  │  Current: 2000+ reads from ChronoTrack (as of June 10, 2025)       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                ▲                                           │
│                                │                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │              ChronoTrack Timing Collector Service                   │  │
│  │                          ✅ FULLY OPERATIONAL                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │ Standalone Python Service (Always Running)                 │  │  │
│  │  │ • TCP Listener (Port 61611) - ChronoTrack Protocol        │  │  │
│  │  │ • Status API (Port 61612) - Internal monitoring           │  │  │
│  │  │ • Database Writer - Direct to raw_tag_data                │  │  │
│  │  │ • Session Management - Automatic timing sessions          │  │  │
│  │  │ • Protocol Handshake - Proper ChronoTrack timing delays   │  │  │
│  │  │ • 24/7 Operation - Independent of web display             │  │  │
│  │  │ • Fixed: Timestamp parsing (splits date/time correctly)   │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                ▲                                           │
│                                │                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      External Integrations                          │  │
│  │                                                                     │  │
│  │  • ChronoTrack Timing Hardware (TCP/IP Port 61611) ✅ CONNECTED    │  │
│  │    - Currently connected from: 44.195.193.123                      │  │
│  │    - Sending timing data in batches of ~2000 reads                 │  │
│  │  • RunSignUp API Integration                                       │  │
│  │  • Race Roster API Integration                                     │  │
│  │  • Multi-tenant Timing Companies                                   │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ **ChronoTrack Timing Collector Service - OPERATIONAL**

### **Overview**
Dedicated 24/7 service for ChronoTrack timing hardware connections, completely separate from the web display system. **Currently receiving and storing timing data successfully.**

### **Key Features**
- **Always Available**: Runs 24/7 regardless of web app status ✅
- **ChronoTrack Protocol**: Full handshake with proper timing delays ✅
- **Automatic Sessions**: Creates timing sessions automatically ✅
- **Database Integration**: Direct writes to `raw_tag_data` database ✅
- **Status Monitoring**: Built-in HTTP API for health checks ✅
- **Lightweight**: Minimal resource usage (typically <15MB RAM) ✅

### **Recent Fixes Applied (June 10, 2025)**
1. **Firewall Configuration**: Added iptables rule to allow port 61611
2. **Timestamp Parsing**: Fixed to split ISO timestamp format (YYYY-MM-DDTHH:MM:SS.ms) into separate date and time fields
3. **Database Schema Compatibility**: Collector now correctly handles the separate read_date and read_time columns

### **File Structure**
```
/home/appuser/projects/timing-collector/
├── collector.py              # Main timing collector service (FIXED)
├── collector.py.backup       # Original version
├── collector.py.backup2      # Pre-timestamp fix version
├── collector.py.backup3      # Latest backup
├── requirements.txt          # Python dependencies (psycopg2-binary)
└── venv/                     # Python virtual environment
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

### **Current Statistics (as of June 10, 2025, 16:14 UTC)**
- **Status**: Running
- **Active Connections**: 1 (ChronoTrack at 44.195.193.123)
- **Total Reads Received**: 2000+
- **Current Session ID**: 28
- **Database**: Connected and writing successfully

### **ChronoTrack Data Format**
```
Format: CT01_33~SEQUENCE~LOCATION~BIB~TIMESTAMP~GATOR~TAGCODE~LAP
Example: CT01_33~2000~PHASER~3132~2025-06-01T08:30:22.04~1~23H016~1
```

---

## 🏁 **Race Display System - NEEDS RESTART**

### **Overview**
Pure web application focused on timing data visualization and APIs. Currently offline and needs to be restarted.

### **Components**
- **Flask Application**: Python-based web server (NO TCP functionality)
- **React Frontend**: Modern responsive UI
- **Timing Database Reader**: Reads from `raw_tag_data` populated by collector
- **RESTful APIs**: Real-time access to timing data
- **Real-time Updates**: Server-Sent Events (SSE)

### **Required Action**
```bash
sudo systemctl start race-display
sudo systemctl enable race-display
```

---

## 🔧 **System Services Management**

### **Active Services Status**

| Service | Purpose | Status | Port | User | Dependencies |
|---------|---------|--------|------|------|--------------|
| `timing-collector.service` | ChronoTrack TCP Collection | ✅ Active | 61611/61612 | appuser | postgresql |
| `race-display.service` | Race Display Web App | ⚠️ Needs Start | 5000 | appuser | timing-collector |
| `openwebui.service` | AI/NLP Web Interface | ✅ Active | 8501 | root | ollama |
| `ollama.service` | Local LLM Server | ✅ Active | 11434 | root | - |
| `httpd.service` | Apache Web Server | ✅ Active | 80/443 | apache | - |
| `postgresql.service` | Database Server | ✅ Active | 5432 | postgres | - |

---

## 🔐 **Security Configuration - UPDATED**

### **Firewall Rules**

#### **UFW Status**
```bash
# Current UFW rules
22/tcp    (SSH)              ALLOW
80/tcp    (HTTP)             ALLOW
443/tcp   (HTTPS)            ALLOW
61611/tcp (ChronoTrack)      ALLOW
```

#### **iptables Configuration (Active)**
```bash
# Critical rule added for ChronoTrack
iptables -I INPUT 1 -p tcp --dport 61611 -j ACCEPT

# Rule needs to be saved permanently:
sudo sh -c 'iptables-save > /etc/sysconfig/iptables'
```

**Note**: System is using both UFW and iptables. The iptables rule for port 61611 was critical for allowing ChronoTrack connections.

---

## 🛠️ **Troubleshooting Guide - UPDATED**

### **ChronoTrack Connection Issues - RESOLVED**

#### **Problem**: ChronoTrack couldn't connect (SYN packets arriving but no SYN-ACK)
**Solution**: Added iptables ACCEPT rule for port 61611

#### **Problem**: "invalid input syntax for type time" errors
**Solution**: Modified collector.py to split ISO timestamp format:
```python
# Split "2025-06-01T09:23:22.03" into:
date_part = data['time'].split('T')[0]  # "2025-06-01"
time_part = data['time'].split('T')[1]  # "09:23:22.03"
```

### **Current Data Flow**
1. ChronoTrack hardware (44.195.193.123) → TCP 61611 → Timing Collector
2. Timing Collector → PostgreSQL (raw_tag_data database)
3. Race Display (when running) → Reads from PostgreSQL → Web Interface

---

## 📊 **Database Schema Reference**

### **timing_reads Table Structure**
```sql
Column           | Type                        | Description
-----------------|-----------------------------|-----------------------
id               | bigint                      | Primary key
session_id       | integer                     | Links to timing_sessions
location_id      | integer                     | Links to timing_locations
sequence_number  | integer                     | ChronoTrack sequence
location_name    | varchar(100)                | Location identifier (e.g., "PHASER")
tag_code         | varchar(8)                  | RFID tag code
read_time        | time                        | Time of day (HH:MM:SS.ms)
read_date        | date                        | Date (YYYY-MM-DD)
read_timestamp   | timestamp                   | Full timestamp (auto-generated)
lap_count        | integer                     | Lap number
reader_id        | varchar(6)                  | ChronoTrack reader ID
gator_number     | integer                     | Gator/mat number
raw_data         | text                        | Original data as JSON
processed_at     | timestamp                   | When record was processed
```

---

## 📋 **Quick Reference - UPDATED**

### **Essential Commands**

| Task | Command |
|------|---------|
| **Check ChronoTrack Collector** | `sudo systemctl status timing-collector` |
| **Check Collector Stats** | `curl http://127.0.0.1:61612/status \| jq .` |
| **View Collector Logs** | `sudo journalctl -u timing-collector -f` |
| **Start Race Display** | `sudo systemctl start race-display` |
| **Watch TCP Connections** | `sudo tcpdump -i any -n port 61611` |
| **Check Timing Data** | `psql -h localhost -U race_timing_user -d raw_tag_data -c "SELECT COUNT(*) FROM timing_reads;"` |
| **Save Firewall Rules** | `sudo sh -c 'iptables-save > /etc/sysconfig/iptables'` |

### **Key Fixes Applied**

1. **Firewall Fix** (June 10, 2025)
   ```bash
   sudo iptables -I INPUT 1 -p tcp --dport 61611 -j ACCEPT
   ```

2. **Timestamp Parser Fix** (June 10, 2025)
   - Modified `/home/appuser/projects/timing-collector/collector.py`
   - Splits ISO timestamp into date and time components
   - Handles format: `YYYY-MM-DDTHH:MM:SS.ms`

### **Current Data Statistics**
- **Total Timing Reads**: 2000+
- **Unique Tags**: 2 (including 23H016)
- **Locations**: 1 (PHASER)
- **Date Range**: June 1, 2025 (06:23 - 08:30)
- **Active Hardware**: ChronoTrack at 44.195.193.123

### **System Resource Usage**
- **CPU Spike (June 9, 20:00-23:00)**: DeepSeek-R1 model download and extraction
- **Normal RAM Usage**: ~4GB baseline, spikes to 10-16GB during AI model operations
- **Disk Usage**: ~10GB for AI models, growing ~2.5GB/day for timing data

### **Next Steps**
1. ✅ ~~Fix ChronoTrack connection~~ (COMPLETED)
2. ✅ ~~Receive timing data~~ (2000+ reads stored)
3. ✅ ~~Fix AI platform access~~ (COMPLETED)
4. ⏳ Start race-display service: `sudo systemctl start race-display`
5. ⏳ Save iptables rules permanently
6. ⏳ Set up automated backups
7. ⏳ Configure resource limits for Ollama

---

**🏁 Project88Hub VPS Infrastructure - Complete Documentation v4.0**  
**Document Version**: 4.0  
**Last Updated**: June 10, 2025  
**Status**: Timing Collector ✅ OPERATIONAL | AI Platform ✅ OPERATIONAL | Race Display ⏳ NEEDS START  
**Today's Achievements**: 
- Fixed ChronoTrack connection issues (firewall + timestamp parsing)
- Received and stored 2000+ timing reads
- Resolved AI platform authentication issue
- Identified DeepSeek-R1 as cause of CPU spike

**Key Infrastructure Notes**:
- **Firewall**: Using both UFW and iptables (iptables takes precedence)
- **AI Auth**: Disabled for easier access (`WEBUI_AUTH=False`)
- **Database**: PostgreSQL with separate production and timing databases
- **Architecture**: Separated services for maximum reliability