# Infrastructure Technical Details - Current Implementation

## 📋 **Quick Reference**

**Environment**: Live Production SaaS Platform  
**Server**: 69.62.69.90 (Hostinger KVM 8)  
**Status**: 77% complete, serving 13 timing partners  
**Database**: PostgreSQL with 10.7M+ records (100% migrated)

---

## 🚀 **Service Management**

### **Active Production Services**
```bash
# Check service status
systemctl status race-display-clean.service     # Race Display (Port 5001)
systemctl status timing-collector.service       # ChronoTrack TCP (Port 61611)  
systemctl status project88hub-auth-production.service  # Auth API (Port 5002)
systemctl status project88hub-auth-phase2.service      # User Mgmt (Port 5003)
systemctl status postgrest.service              # Database API (Port 3000)
systemctl status openwebui.service              # AI Platform (Port 8501)
systemctl status postgresql.service             # Database
systemctl status redis.service                  # Session Store
systemctl status apache2.service                # Web Server & SSL
```

### **Service Restart Procedures**
```bash
# Safe restart sequence (production)
sudo systemctl restart race-display-clean.service
sudo systemctl restart timing-collector.service
sudo systemctl restart project88hub-auth-production.service

# Check logs after restart
journalctl -u race-display-clean.service -f
journalctl -u timing-collector.service -f
```

---

## 🗂️ **Application File Locations**

### **Race Display Application**
```bash
# Main application directory
/home/appuser/projects/race_display_clean/

# Key files
├── app.py                    # Flask application (23KB, production)
├── frontend/dist/            # Built React app  
├── venv/                     # Production virtual environment
├── templates/                # Jinja2 templates
├── static/                   # Static assets
├── requirements.txt          # Python dependencies
└── .env                      # Environment configuration
```

### **Timing Collector Service**
```bash
# Timing collector directory
/home/appuser/projects/timing-collector/

# Key files  
├── collector.py              # TCP listener service
├── collector.py.working      # Backup of working version
├── requirements.txt          # Dependencies
└── venv/                     # Virtual environment
```

### **Authentication Services**
```bash
# Authentication backend directory
/home/appuser/projects/project88hub_auth/

# Key files
├── app_with_auth_backend.py  # Main auth service
├── enhanced_auth_system.py   # Enhanced features
├── simplified_auth_backend.py # Simplified version
├── requirements.txt          # Dependencies
└── venv/                     # Virtual environment
```

---

## 🔧 **Configuration Management**

### **Apache Virtual Host Configuration**
```apache
# /etc/apache2/sites-available/project88hub.conf
<VirtualHost *:443>
    ServerName display.project88hub.com
    ProxyPass / http://localhost:5001/
    ProxyPassReverse / http://localhost:5001/
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/project88hub.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/project88hub.com/privkey.pem
</VirtualHost>

<VirtualHost *:443>
    ServerName ai.project88hub.com  
    ProxyPass / http://localhost:8501/
    ProxyPassReverse / http://localhost:8501/
    SSLEngine on
</VirtualHost>

<VirtualHost *:443>
    ServerName project88hub.com
    ProxyPass / http://localhost:5002/
    ProxyPassReverse / http://localhost:5002/
    SSLEngine on
</VirtualHost>
```

### **Systemd Service Files**
```ini
# /etc/systemd/system/race-display-clean.service
[Unit]
Description=Race Display Clean Application
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=appuser
WorkingDirectory=/home/appuser/projects/race_display_clean
Environment=PATH=/home/appuser/projects/race_display_clean/venv/bin
ExecStart=/home/appuser/projects/race_display_clean/venv/bin/gunicorn --bind 0.0.0.0:5001 --workers 4 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 🗄️ **Database Configuration**

### **PostgreSQL Settings**
```bash
# Database connection details
Host: localhost
Port: 5432
Databases:
  - project88_myappdb (main application)
  - raw_tag_data (live timing data)

# Key users
- project88_myappuser (main app access)
- race_timing_user (timing data access)
```

### **Database Schema Overview**
```sql
-- Main Application Database (project88_myappdb)
users                    -- User accounts (13 timing partners)
timing_partners          -- Timing company configurations
user_subscriptions       -- Active subscriptions  
payment_history          -- Transaction tracking
user_templates           -- Custom race templates
user_subdomain_access    -- Multi-tenant access control
usage_tracking           -- Platform usage metrics

-- Raw Timing Database (raw_tag_data)  
timing_sessions          -- Live timing sessions (45+ active)
timing_reads            -- Real-time timing data (2,040+ reads)
timing_locations        -- Hardware location configurations
```

### **Database Backup & Maintenance**
```bash
# Daily backup script
pg_dump project88_myappdb > /backup/project88_$(date +%Y%m%d).sql
pg_dump raw_tag_data > /backup/timing_$(date +%Y%m%d).sql

# Cleanup old backups (keep 30 days)
find /backup -name "*.sql" -mtime +30 -delete
```

---

## 🌐 **Network & Security Configuration**

### **Firewall Rules (UFW)**
```bash
# Allow essential ports only
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP  
ufw allow 443/tcp     # HTTPS
ufw allow 61611/tcp   # ChronoTrack TCP
ufw enable

# Block all other ports
ufw default deny incoming
ufw default allow outgoing
```

### **SSL Certificate Management**
```bash
# Let's Encrypt auto-renewal
/etc/cron.d/certbot:
0 12 * * * /usr/bin/certbot renew --quiet

# Manual renewal if needed
sudo certbot renew --dry-run
sudo systemctl reload apache2
```

---

## ⚙️ **Environment Variables & Configuration**

### **Race Display App Environment**
```bash
# /home/appuser/projects/race_display_clean/.env
FLASK_ENV=production
FLASK_APP=app.py
SECRET_KEY=<production-secret>
DATABASE_URL=postgresql://project88_myappuser:pass@localhost/project88_myappdb
REDIS_URL=redis://localhost:6379/0
CHRONOTRACK_HOST=localhost
CHRONOTRACK_PORT=61611
```

### **Authentication Service Environment**
```bash
# /home/appuser/projects/project88hub_auth/.env  
FLASK_ENV=production
SECRET_KEY=<auth-secret>
DATABASE_URL=postgresql://project88_myappuser:pass@localhost/project88_myappdb
JWT_SECRET_KEY=<jwt-secret>
```

---

## 🔍 **Monitoring & Logging**

### **Log File Locations**
```bash
# Application logs
/var/log/race-display/app.log
/var/log/timing-collector/collector.log
/var/log/project88hub-auth/auth.log

# System logs
/var/log/apache2/access.log
/var/log/apache2/error.log
/var/log/postgresql/postgresql-14-main.log

# Service logs via journalctl
journalctl -u race-display-clean.service
journalctl -u timing-collector.service
```

### **Performance Monitoring**
```bash
# Check system resources
htop
df -h
free -h

# Monitor database connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;"

# Check Apache status
sudo systemctl status apache2
sudo apache2ctl status
```

---

## 🚨 **Troubleshooting Common Issues**

### **Service Won't Start**
```bash
# Check service status and logs
systemctl status <service-name>
journalctl -u <service-name> --since "1 hour ago"

# Check port conflicts
netstat -tulpn | grep <port>
lsof -i :<port>
```

### **Database Connection Issues**
```bash
# Test database connectivity
sudo -u postgres psql project88_myappdb
\dt  # List tables
\q   # Quit

# Check PostgreSQL logs
tail -f /var/log/postgresql/postgresql-14-main.log
```

### **SSL Certificate Issues**
```bash
# Check certificate status
sudo certbot certificates

# Test SSL configuration
openssl s_client -connect project88hub.com:443

# Reload Apache after certificate renewal
sudo systemctl reload apache2
```

### **ChronoTrack TCP Connection Issues**
```bash
# Check timing collector status
systemctl status timing-collector.service

# Test TCP port
telnet localhost 61611
nc -zv localhost 61611

# Check timing data in database
sudo -u postgres psql raw_tag_data -c "SELECT COUNT(*) FROM timing_reads;"
```

---

## 🔄 **Development Workflow**

### **Safe Development Process**
1. **Backup**: Create database backup before changes
2. **Testing**: Test changes in local environment first
3. **Staging**: Deploy to staging environment (if available)
4. **Production**: Deploy with zero-downtime procedures
5. **Monitoring**: Monitor logs and performance after deployment

### **Code Deployment**
```bash
# Pull latest changes
cd /home/appuser/projects/race_display_clean
git pull origin main

# Install/update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Build frontend (if needed)
cd frontend
npm install
npm run build

# Restart services
sudo systemctl restart race-display-clean.service
```

---

## 📊 **Performance Optimization**

### **Database Optimization**
```sql
-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- Update statistics
ANALYZE;

-- Reindex if needed
REINDEX DATABASE project88_myappdb;
```

### **Application Performance**
```bash
# Monitor memory usage
ps aux | grep python

# Check for memory leaks
top -p $(pgrep -f "race_display_clean")

# Optimize gunicorn workers
# Adjust workers in systemd service file based on CPU cores
```

---

**Status**: Production Ready | **Uptime**: 99.9%+ | **Monitoring**: Active 