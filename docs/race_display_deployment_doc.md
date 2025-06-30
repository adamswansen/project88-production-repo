# 🏁 Race Display System - Complete Deployment Documentation

## 📋 **Server Specifications**

- **Provider**: Hostinger VPS
- **Plan**: KVM 8
- **OS**: AlmaLinux 9.6 (Sage Margay)
- **Resources**: 8 CPU cores, 32GB RAM, 400GB disk
- **IP Address**: `69.62.69.90`
- **Main Domain**: `project88hub.com`
- **Race Display Subdomain**: `display.project88hub.com`

## 🎯 **Access Points**

| Service | URL/Address | Purpose |
|---------|-------------|---------|
| **Race Display Web Interface** | `https://display.project88hub.com` | Main user interface |
| **Race Display Backup** | `https://project88hub.com/race-display/` | Alternative access point |
| **Timing System TCP** | `69.62.69.90:61611` | Timing hardware connection |
| **Flask Internal** | `http://127.0.0.1:5000` | Internal application (localhost only) |

## 📁 **File Structure & Locations**

### **Application Files**
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

### **Web Server Files**
```
/home/project88/public_html/
├── race-display/            # Working directory proxy
│   └── .htaccess           # Proxy configuration
└── display.project88hub.com/  # Subdomain directory
    └── .htaccess           # Subdomain proxy configuration
```

### **Configuration Files**
```
/etc/apache2/conf.d/display-project88hub.conf    # Apache VirtualHost
/etc/systemd/system/race-display.service         # Systemd service
/home/appuser/projects/race_display/config.py    # Flask configuration
```

## ⚙️ **Configuration Details**

### **Flask Application Configuration** (`config.py`)

```python
# config.py - Race Display Configuration

# Random messages for display rotation
RANDOM_MESSAGES = [
    "Welcome to Race Display",
    "Real-time timing data",
    "Live race results",
    "Powered by project88hub.com",
    "Timing system connected",
    "Ready for race data"
]

# API Configuration
API_CONFIG = {
    'base_url': 'https://display.project88hub.com',
    'timeout': 30,
    'retries': 3,
    'headers': {
        'User-Agent': 'RaceDisplay/1.0',
        'Content-Type': 'application/json'
    }
}

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

# Database Configuration (optional - using existing PostgreSQL)
DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'project88_myappdb',
    'user': 'project88_myappuser',
    'password': 'puctuq-cefwyq-3boqRe'
}

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': '/home/appuser/projects/race_display/logs/app.log'
}

# CORS Configuration
CORS_CONFIG = {
    'origins': [
        'https://display.project88hub.com',
        'https://project88hub.com',
        'https://ai.project88hub.com'
    ],
    'methods': ['GET', 'POST', 'PUT', 'DELETE'],
    'allow_headers': ['Content-Type', 'Authorization']
}
```

### **Apache VirtualHost Configuration**

```apache
# /etc/apache2/conf.d/display-project88hub.conf

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

# Note: SSL (HTTPS) configuration would be auto-added by certbot if SSL certificate is installed
```

### **Systemd Service Configuration**

```ini
# /etc/systemd/system/race-display.service

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

### **Backup Directory Proxy Configuration**

```apache
# /home/project88/public_html/race-display/.htaccess
# Backup access point: https://project88hub.com/race-display/

RewriteEngine On
RewriteRule ^(.*)$ http://127.0.0.1:5000/$1 [P,L]
```

### **Subdomain Directory Proxy Configuration**

```apache
# /home/project88/public_html/display.project88hub.com/.htaccess
# Subdomain access point: https://display.project88hub.com

RewriteEngine On
RewriteRule ^(.*)$ http://127.0.0.1:5000/$1 [P,L]
```

## 🔧 **Services & Processes**

### **Active Services**
| Service | Status | Purpose | Start Command |
|---------|--------|---------|---------------|
| `race-display.service` | ✅ Active | Main Flask application | `sudo systemctl start race-display` |
| `httpd.service` | ✅ Active | Apache web server (cPanel managed) | `sudo systemctl start httpd` |

### **Port Configuration**
| Port | Service | Access | Purpose |
|------|---------|--------|---------|
| **80** | Apache HTTP | External | Web traffic (redirects to HTTPS) |
| **443** | Apache HTTPS | External | Secure web traffic |
| **5000** | Flask App | Internal only | Race display application |
| **61611** | TCP Server | External | Timing system data input |

### **Network & Security**
- **Firewall**: Disabled (managed by hosting provider)
- **cPanel**: EasyApache manages Apache configuration
- **SSL**: Available via Let's Encrypt (certbot)

## 🚀 **Complete Deployment Steps**

### **1. Initial Setup**
```bash
# SSH into server
ssh appuser@69.62.69.90

# Navigate to projects directory
mkdir -p ~/projects
cd ~/projects

# Clone repository
git clone https://github.com/adamswansen/race_display.git
cd race_display

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
pip install flask-cors

# Build React frontend
cd frontend
npm install
npm run build
cd ..

# Create logs directory
mkdir -p logs
```

### **2. Configuration Setup**
```bash
# Create Flask configuration file
nano config.py
# (Copy the configuration from the section above)

# Set proper permissions
chown -R appuser:appuser /home/appuser/projects/race_display
```

### **3. Service Configuration**
```bash
# Create systemd service file
sudo nano /etc/systemd/system/race-display.service
# (Copy the service configuration from the section above)

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable race-display
sudo systemctl start race-display

# Check service status
sudo systemctl status race-display
```

### **4. Apache VirtualHost Setup**
```bash
# Create Apache VirtualHost configuration
sudo nano /etc/apache2/conf.d/display-project88hub.conf
# (Copy the Apache configuration from the section above)

# Test Apache configuration
sudo /usr/sbin/httpd -t

# Restart Apache
sudo systemctl restart httpd
```

### **5. Directory-Based Backup Setup**
```bash
# Create backup directory proxy
sudo mkdir -p /home/project88/public_html/race-display

# Create .htaccess proxy file
sudo tee /home/project88/public_html/race-display/.htaccess > /dev/null <<'EOF'
RewriteEngine On
RewriteRule ^(.*)$ http://127.0.0.1:5000/$1 [P,L]
EOF

# Set proper ownership
sudo chown -R project88:project88 /home/project88/public_html/race-display
```

### **6. Subdomain Directory Setup**
```bash
# Create subdomain directory
sudo mkdir -p /home/project88/public_html/display.project88hub.com

# Create .htaccess proxy file
sudo tee /home/project88/public_html/display.project88hub.com/.htaccess > /dev/null <<'EOF'
RewriteEngine On
RewriteRule ^(.*)$ http://127.0.0.1:5000/$1 [P,L]
EOF

# Set proper ownership
sudo chown -R project88:project88 /home/project88/public_html/display.project88hub.com
```

### **7. DNS Configuration**
- Create DNS A record: `display.project88hub.com` → `69.62.69.90`
- Allow 5-30 minutes for DNS propagation

### **8. SSL Certificate Setup (Optional)**
```bash
# Install SSL certificate for subdomain
sudo certbot --apache -d display.project88hub.com

# This automatically updates Apache configuration with SSL settings
```

## 🔍 **Testing & Verification**

### **Test Commands**
```bash
# Test Flask application internally
curl http://127.0.0.1:5000

# Test subdomain access
curl https://display.project88hub.com

# Test backup directory access
curl https://project88hub.com/race-display/

# Check service status
sudo systemctl status race-display

# Check Apache status
sudo systemctl status httpd

# View application logs
sudo journalctl -u race-display -f

# View Apache logs
tail -f /var/log/apache2/display_error.log

# Check open ports
sudo ss -tlnp | grep -E ':(80|443|5000|61611)'

# Test Apache configuration
sudo /usr/sbin/httpd -t

# Check VirtualHost configuration
sudo /usr/sbin/httpd -S | grep display
```

## 🏁 **Timing System Integration**

### **Connection Settings**
- **Protocol**: TCP
- **Server IP**: `69.62.69.90`
- **Port**: `61611`
- **Data Format**: As defined by `listener.py` in the application

### **Application Features**
- Real-time race timing display
- Runner information lookup
- Web-based interface with React frontend
- Server-Sent Events (SSE) for live updates
- TCP/IP connection to timing systems
- Support for multiple race locations
- Gun times integration
- Authentication support
- Bootstrap-based responsive UI

## 🛠️ **Troubleshooting Guide**

### **Common Issues**

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

#### **Web Interface Not Accessible**
```bash
# Check Apache status
sudo systemctl status httpd

# Check Apache configuration
sudo /usr/sbin/httpd -t

# Check VirtualHost setup
sudo /usr/sbin/httpd -S | grep display

# Check Apache error logs
tail -20 /var/log/apache2/error_log
tail -10 /var/log/apache2/display_error.log
```

#### **Timing System Cannot Connect**
```bash
# Check if application is listening on correct port
sudo ss -tlnp | grep :61611

# Test internal Flask app
curl http://127.0.0.1:5000

# Check application logs for timing data
sudo journalctl -u race-display -f
```

### **File Permissions**
```bash
# Application files (appuser)
sudo chown -R appuser:appuser /home/appuser/projects/race_display
sudo chmod +x /home/appuser/projects/race_display/venv/bin/python

# Web server files (project88)
sudo chown -R project88:project88 /home/project88/public_html/race-display
sudo chown -R project88:project88 /home/project88/public_html/display.project88hub.com
sudo chmod 644 /home/project88/public_html/race-display/.htaccess
sudo chmod 644 /home/project88/public_html/display.project88hub.com/.htaccess
```

### **Restart All Services**
```bash
# Restart race display application
sudo systemctl restart race-display

# Restart Apache web server
sudo systemctl restart httpd

# Check all services are running
sudo systemctl status race-display httpd
```

## 📝 **Maintenance & Updates**

### **Application Updates**
```bash
# Navigate to application directory
cd /home/appuser/projects/race_display

# Pull latest code from repository
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Update Python dependencies if needed
pip install -r requirements.txt

# Rebuild frontend if needed
cd frontend
npm install
npm run build
cd ..

# Restart application service
sudo systemctl restart race-display
```

### **System Maintenance**
```bash
# Update system packages
sudo dnf update

# Check disk space
df -h

# Check service logs for issues
sudo journalctl -u race-display --since "1 week ago"

# Clean up old logs if needed
sudo journalctl --vacuum-time=30d
```

### **SSL Certificate Renewal**
```bash
# Check certificate expiration
sudo certbot certificates

# Renew certificates (automatic renewal should be configured)
sudo certbot renew

# Manual renewal if needed
sudo certbot --apache -d display.project88hub.com
```

### **Backup Procedures**
```bash
# Backup application directory
sudo tar -czf /tmp/race_display_backup_$(date +%Y%m%d).tar.gz /home/appuser/projects/race_display/

# Backup configuration files
sudo cp /etc/apache2/conf.d/display-project88hub.conf /tmp/
sudo cp /etc/systemd/system/race-display.service /tmp/
sudo cp /home/appuser/projects/race_display/config.py /tmp/

# Backup database (if applicable)
# sudo -u postgres pg_dump project88_myappdb > /tmp/race_display_db_backup_$(date +%Y%m%d).sql
```

## 📊 **System Monitoring**

### **Health Check Commands**
```bash
# Check system resources
top
free -h
df -h

# Check network connections
sudo ss -tlnp

# Check service status
systemctl status race-display httpd

# Check application performance
curl -w "@-" -o /dev/null -s http://127.0.0.1:5000 <<< "time_namelookup:  %{time_namelookup}s\ntime_connect:     %{time_connect}s\ntime_appconnect:  %{time_appconnect}s\ntime_pretransfer: %{time_pretransfer}s\ntime_redirect:    %{time_redirect}s\ntime_starttransfer: %{time_starttransfer}s\ntime_total:       %{time_total}s\n"
```

### **Log Monitoring**
```bash
# Monitor application logs in real-time
sudo journalctl -u race-display -f

# Monitor Apache access logs
tail -f /var/log/apache2/display_access.log

# Monitor Apache error logs
tail -f /var/log/apache2/display_error.log

# Check for errors in logs
sudo journalctl -u race-display --since "1 hour ago" | grep -i error
```

---

## 📋 **Quick Reference**

### **Important Commands**
| Task | Command |
|------|---------|
| **Restart Race Display** | `sudo systemctl restart race-display` |
| **Restart Apache** | `sudo systemctl restart httpd` |
| **Check Logs** | `sudo journalctl -u race-display -f` |
| **Test Configuration** | `sudo /usr/sbin/httpd -t` |
| **Test Internal App** | `curl http://127.0.0.1:5000` |
| **Test External Access** | `curl https://display.project88hub.com` |

### **Important Files**
| File | Purpose |
|------|---------|
| `/home/appuser/projects/race_display/config.py` | Flask configuration |
| `/etc/apache2/conf.d/display-project88hub.conf` | Apache VirtualHost |
| `/etc/systemd/system/race-display.service` | Systemd service |
| `/home/project88/public_html/race-display/.htaccess` | Backup proxy |

### **Key Information**
- **Deployment Date**: June 9, 2025
- **Primary Access**: `https://display.project88hub.com`
- **Backup Access**: `https://project88hub.com/race-display/`
- **Timing Input**: `69.62.69.90:61611` (TCP)
- **Status**: ✅ Operational

---

**Race Display System successfully deployed and operational!** 🏁