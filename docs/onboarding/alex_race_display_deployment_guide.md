# 🏁 Race Display Deployment Guide - Based on Actual Codebase

## 📋 **Code Review Summary**

I've reviewed the actual Race Display repository (`race_display-branch2-2.1`) and here's what Alex needs to know:

### **Application Architecture (Confirmed)**
- **Backend**: Flask application (`app.py` - 3,380 lines, very comprehensive)
- **Frontend**: React + Vite application (modern setup)
- **Database**: PostgreSQL integration for timing data storage
- **TCP Listener**: Port 61611 for timing hardware connections
- **Multiple Providers**: ChronoTrack and RunSignUp integration support

### **Two Versions Available**
1. **`app.py`** - Full featured version (3,380 lines) with complete functionality
2. **`app_unified.py`** - Simplified version (1,239 lines) with database integration

---

## 🏗️ **Actual Dependencies & Requirements**

### **Python Dependencies (from requirements.txt)**
```
Flask==3.1.1
flask-cors==6.0.0
psycopg2-binary==2.9.10
requests==2.32.3
beautifulsoup4==4.13.4
gunicorn==23.0.0
python-dotenv==1.1.0
pillow==11.2.1
```

### **Frontend Dependencies (React + Vite)**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.21.0",
    "grapesjs": "^0.21.3",
    "animate.css": "^4.1.1",
    "react-image-crop": "^11.0.10"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.0.0",
    "vite": "^4.0.0"
  }
}
```

---

## 🎯 **Deployment Steps for Alex**

### **Step 1: VPS Environment Setup**
```bash
# SSH into VPS
ssh appuser@69.62.69.90

# Navigate to projects directory
cd /home/appuser/projects

# Clone the repository
git clone https://github.com/huttonAlex/race_display.git
cd race_display

# Check if we're on the right branch
git branch -a
# Switch to branch2-2.1 if needed
git checkout branch2-2.1
```

### **Step 2: Python Environment Setup**
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Verify Python version (should be 3.x)
python --version

# Install Python dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### **Step 3: Node.js Environment Setup**
```bash
# Check if Node.js is installed
node --version
npm --version

# If not installed, install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install frontend dependencies
cd frontend
npm install

# Build React application for production
npm run build

# Verify build completed
ls -la dist/
```

### **Step 4: Configuration Setup**
```bash
# Copy and modify configuration
cd /home/appuser/projects/race_display
cp config.py config.py.backup

# Edit configuration for production
nano config.py
```

**Configuration Changes Needed**:
```python
# config.py - Production settings

# Random messages for display (keep existing)
RANDOM_MESSAGES = [
    "Welcome to the race!",
    "Great job runners!",
    # ... existing messages
]

# API Configuration for ChronoTrack
API_CONFIG = {
    'BASE_URL': 'https://api.chronotrack.com/api',
    'FORMAT': 'json',
    'CLIENT_ID': 'your_client_id',  # Get from ChronoTrack
    'DEFAULT_USER_ID': '',
    'DEFAULT_PASSWORD': '',
    'DEFAULT_EVENT_ID': ''
}

# Protocol Configuration for TCP communication
PROTOCOL_CONFIG = {
    'HOST': '0.0.0.0',  # Accept connections from anywhere
    'PORT': 61611,
    'FIELD_SEPARATOR': '\t',
    'LINE_TERMINATOR': '\n',
    'FORMAT_ID': 'CT'
}

# Server Configuration for Flask
SERVER_CONFIG = {
    'DEBUG': False,  # IMPORTANT: Set to False for production
    'HOST': '127.0.0.1',  # Internal only, Apache will proxy
    'PORT': 5000
}

# Timing Configuration
TIMING_CONFIG = {
    'store_to_database': True  # Enable database storage
}

# Add PostgreSQL configuration for unified version
RAW_TAG_DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'project88_myappdb',
    'user': 'project88_myappuser',
    'password': 'NEW_SECURE_PASSWORD'  # Use new password after security hardening
}
```

### **Step 5: Database Schema Setup**
**Important**: The `app_unified.py` version expects PostgreSQL tables that may not exist yet.

```bash
# Connect to PostgreSQL
sudo -u postgres psql -d project88_myappdb

# Create timing tables (if using unified version)
CREATE TABLE IF NOT EXISTS timing_sessions (
    id SERIAL PRIMARY KEY,
    session_name VARCHAR(255) NOT NULL,
    event_name VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS timing_locations (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES timing_sessions(id),
    location_name VARCHAR(255) NOT NULL,
    reader_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS timing_reads (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES timing_sessions(id),
    location_id INTEGER REFERENCES timing_locations(id),
    sequence_number INTEGER,
    location_name VARCHAR(255),
    tag_code VARCHAR(100),
    read_time VARCHAR(50),
    lap_count INTEGER DEFAULT 1,
    reader_id VARCHAR(100),
    gator_number INTEGER DEFAULT 0,
    raw_data JSONB,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(session_id, sequence_number, location_name)
);
```

### **Step 6: Systemd Service Setup**
```bash
# Create systemd service file
sudo nano /etc/systemd/system/race-display.service
```

**Service Configuration**:
```ini
[Unit]
Description=Race Display Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/projects/race_display
Environment=PATH=/home/appuser/projects/race_display/venv/bin
Environment=RACE_DISPLAY_MODE=server
ExecStart=/home/appuser/projects/race_display/venv/bin/python app.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/home/appuser/projects/race_display

[Install]
WantedBy=multi-user.target
```

### **Step 7: Apache Virtual Host Setup**
The documentation shows this is already configured, but verify:

```bash
# Check Apache configuration
sudo cat /etc/apache2/conf.d/display-project88hub.conf

# Should contain:
# ProxyPass / http://127.0.0.1:5000/
# ProxyPassReverse / http://127.0.0.1:5000/
```

### **Step 8: Start and Test Services**
```bash
# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable race-display.service
sudo systemctl start race-display.service

# Check service status
sudo systemctl status race-display.service

# Check logs
sudo journalctl -u race-display.service -f

# Test local access
curl http://localhost:5000/

# Test external access
curl https://display.project88hub.com
```

---

## 🔍 **Application Features Discovered**

### **Core Functionality**
- **Real-time Race Display**: Shows runner information as timing data comes in
- **Multiple Provider Support**: ChronoTrack Live and RunSignUp integration
- **TCP Listener**: Accepts timing data directly from hardware
- **Background Refresh**: Automatic data synchronization
- **Template System**: Customizable display templates
- **Image Upload**: Support for custom images and logos

### **API Endpoints (From Code Review)**
```python
# Authentication & Setup
POST /api/login
POST /api/test-connection
GET  /api/providers

# Race Data
POST /api/select-event
POST /api/select-mode
GET  /api/current-runner
GET  /api/queue-status

# Real-time Updates
GET  /stream  # Server-Sent Events

# Templates & Customization
GET/POST /api/templates
POST /api/upload-image
GET/POST /api/messages

# Timing Integration
POST /api/start-test-listener
GET  /api/timing/database-status
GET  /api/timing/stats
```

### **Frontend Routes (React)**
```javascript
// From App.jsx
/           - Login page
/builder    - Canvas/Template builder
/display    - Fullscreen race display
/runner-display - Individual runner display
```

---

## ⚠️ **Critical Issues Alex Must Address**

### **1. Version Decision**
**Question**: Which version should be deployed?
- **`app.py`** - Full featured (3,380 lines) but complex
- **`app_unified.py`** - Simplified (1,239 lines) with database integration

**Recommendation**: Start with `app_unified.py` for simpler deployment, then migrate to full version if needed.

### **2. Database Schema Missing**
**Issue**: The PostgreSQL database is empty but the unified version expects timing tables.

**Solution**: Create the timing tables (provided above) or modify config to not require them initially.

### **3. ChronoTrack API Credentials**
**Issue**: The app expects ChronoTrack API credentials which aren't configured.

**Action**: Get actual credentials or set up test mode.

### **4. Frontend Build Process**
**Verified**: The React app uses Vite (modern build tool) and needs to be built before deployment.

---

## 🚀 **Deployment Decision Matrix**

### **Option A: Deploy Full Version (`app.py`)**
**Pros**: Complete functionality, all features available  
**Cons**: Complex, 3,380 lines, harder to debug  
**Time**: 6-8 hours

### **Option B: Deploy Unified Version (`app_unified.py`)**  
**Pros**: Simpler, database-integrated, easier to debug  
**Cons**: Missing some features from full version  
**Time**: 3-4 hours

### **Option C: Hybrid Approach**
**Pros**: Start simple, upgrade later  
**Cons**: Requires migration later  
**Time**: 4-6 hours total

---

## 📋 **Alex's First Day Checklist**

### **Prerequisites (Security First)**
- [ ] Change database passwords
- [ ] Enable firewall
- [ ] Audit all service configurations

### **Environment Setup**
- [ ] Clone repository to VPS
- [ ] Set up Python virtual environment
- [ ] Install Node.js and npm
- [ ] Install all dependencies

### **Configuration**
- [ ] Choose app version (unified recommended)
- [ ] Configure database connection
- [ ] Set production settings
- [ ] Create necessary database tables

### **Deployment**
- [ ] Build React frontend
- [ ] Create systemd service
- [ ] Test local functionality
- [ ] Verify Apache proxy
- [ ] Test external access

### **Validation**
- [ ] Login page loads
- [ ] TCP listener starts
- [ ] Database connection works
- [ ] Real-time updates function

---

## 💡 **Recommendations for Production**

1. **Start with `app_unified.py`** - simpler and more maintainable
2. **Create staging environment** first for testing
3. **Test TCP connections** before going live
4. **Set up monitoring** for the service
5. **Document all configuration changes**

**Estimated Time**: 4-6 hours for basic deployment, 8-12 hours for full production setup with testing.

This is a sophisticated timing application with real enterprise features - much more robust than initially described in the documentation! 