# Project88Hub Provider Integration Deployment Guide

## 🚀 Recommended Production Setup

### **Option 1: GitHub + Docker (RECOMMENDED)**

This is the most robust, maintainable approach for production:

#### **Step 1: Repository Setup**
```bash
# Create a private GitHub repository
# Upload this provider-integrations folder to:
# https://github.com/yourusername/project88-provider-integrations

# On your production server:
git clone https://github.com/yourusername/project88-provider-integrations.git
cd project88-provider-integrations
```

#### **Step 2: Initial Deployment**
```bash
# Run setup and deploy with Docker
./deploy.sh --setup --docker

# Edit environment variables
nano .env
# Set your database credentials, SMTP settings, etc.

# Start the system
./deploy.sh --docker
```

#### **Step 3: Verify Operation**
```bash
# Check health
./deploy.sh --health

# View logs
./deploy.sh --logs

# Monitor system
python monitor.py
```

### **Option 2: GitHub + Systemd Service**

If you prefer running directly on the server without Docker:

```bash
# Clone repository
git clone https://github.com/yourusername/project88-provider-integrations.git
cd project88-provider-integrations

# Setup and deploy as systemd service
./deploy.sh --setup --systemd

# Check status
sudo systemctl status project88-provider-sync
```

## 🔧 Configuration

### **Environment Variables**
Create `.env` file with your settings:

```bash
# Database Configuration
DB_HOST=your-postgres-host
DB_PORT=5432
DB_NAME=project88_myappdb
DB_USER=project88_myappuser
DB_PASSWORD=your_secure_password

# Email Alerts (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=alerts@yourdomain.com
SMTP_PASSWORD=your_email_password
ALERT_FROM_EMAIL=alerts@yourdomain.com
ALERT_TO_EMAIL=admin@yourdomain.com

# Logging
LOG_LEVEL=INFO
```

### **Provider Credentials Setup**
Add credentials to your database:

```sql
-- RunSignUp
INSERT INTO partner_provider_credentials (
    timing_partner_id, provider_id, principal, secret
) VALUES (
    1, -- Your timing partner ID
    (SELECT provider_id FROM providers WHERE name = 'RunSignUp'),
    'your-runsignup-api-key',
    'your-runsignup-api-secret'
);

-- Race Roster
INSERT INTO partner_provider_credentials (
    timing_partner_id, provider_id, principal, secret
) VALUES (
    1,
    (SELECT provider_id FROM providers WHERE name = 'Race Roster'),
    'your-raceroster-client-id',
    'your-raceroster-client-secret'
);

-- Haku
INSERT INTO partner_provider_credentials (
    timing_partner_id, provider_id, principal, secret, haku_event_name
) VALUES (
    1,
    (SELECT provider_id FROM providers WHERE name = 'Haku'),
    'your-haku-api-key',
    'your-haku-api-secret',
    'your-organization-id'
);

-- Let's Do This
INSERT INTO partner_provider_credentials (
    timing_partner_id, provider_id, principal
) VALUES (
    1,
    (SELECT provider_id FROM providers WHERE name = 'Let''s Do This'),
    'your-letsdothis-jwt-token'
);
```

## 📊 Monitoring & Maintenance

### **Automated Monitoring**
Add to crontab for regular health checks:

```bash
# Check every 15 minutes
*/15 * * * * cd /path/to/project88-provider-integrations && python monitor.py --quiet --email-alerts

# Daily summary report
0 8 * * * cd /path/to/project88-provider-integrations && python monitor.py --json > /var/log/project88/daily_health_$(date +\%Y\%m\%d).json
```

### **Updates & Deployments**
```bash
# Update to latest code
./deploy.sh --update

# Check health after update
./deploy.sh --health

# View recent logs
./deploy.sh --logs
```

### **Backup Strategy**
```bash
# Database backup (add to daily cron)
pg_dump project88_myappdb > /backups/project88_$(date +%Y%m%d).sql

# Application logs rotation (logrotate)
sudo tee /etc/logrotate.d/project88 << EOF
/var/log/project88/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
```

## 🚨 Troubleshooting

### **Common Issues**

1. **Service Won't Start**
   ```bash
   # Check logs
   ./deploy.sh --logs
   
   # Test database connection
   python main.py --test-connection
   
   # Verify credentials
   python monitor.py --json
   ```

2. **No Sync Jobs Running**
   ```bash
   # Check if events exist in database
   psql project88_myappdb -c "SELECT COUNT(*) FROM unified_events WHERE event_date > NOW() - INTERVAL '1 hour';"
   
   # Check credentials
   psql project88_myappdb -c "SELECT timing_partner_id, provider_id FROM partner_provider_credentials;"
   
   # Manual sync test
   python main.py --manual-sync "1:RunSignUp"
   ```

3. **High Memory/CPU Usage**
   ```bash
   # Reduce workers
   # Edit docker-compose.yml or systemd service
   # Change: --workers 2 to --workers 1
   
   # Check for stuck jobs
   python monitor.py
   ```

### **Performance Tuning**

1. **Database Optimization**
   ```sql
   -- Add indexes for performance
   CREATE INDEX IF NOT EXISTS idx_sync_queue_status_priority 
   ON sync_queue(status, priority, scheduled_time);
   
   CREATE INDEX IF NOT EXISTS idx_sync_history_timing_provider 
   ON sync_history(timing_partner_id, provider_id, sync_time);
   
   CREATE INDEX IF NOT EXISTS idx_unified_events_date 
   ON unified_events(event_date, source_provider);
   ```

2. **System Resources**
   - **RAM**: Minimum 2GB, recommended 4GB
   - **CPU**: 2+ cores recommended
   - **Disk**: 10GB+ for logs and database
   - **Network**: Stable internet for API calls

## 🔐 Security Considerations

### **Production Hardening**
```bash
# Use non-root user
sudo useradd -m -s /bin/bash project88
sudo usermod -aG docker project88

# Secure file permissions
chmod 600 .env
chown project88:project88 .env

# Firewall rules (if needed)
sudo ufw allow from your-database-server-ip to any port 5432
```

### **Credential Management**
- Store API keys in environment variables, not in code
- Use database encryption for sensitive credentials
- Rotate API keys regularly
- Monitor API usage for anomalies

## 📈 Scaling Considerations

### **Horizontal Scaling**
```bash
# Run multiple worker instances
docker-compose up --scale provider-sync=3

# Or run workers on different servers
python main.py --worker-only --workers 1
```

### **Database Scaling**
- Consider read replicas for monitoring queries
- Partition large tables by timing_partner_id
- Archive old sync_history records

## 🎯 Best Practices

1. **Start with one provider** (RunSignUp recommended)
2. **Monitor closely** during first week of operation
3. **Set up alerts** for critical failures
4. **Regular backups** of database and configuration
5. **Document any customizations** for your specific providers
6. **Test failover procedures** regularly

## 📞 Support & Maintenance

### **Log Locations**
- **Docker**: `./logs/` directory
- **Systemd**: `journalctl -u project88-provider-sync -f`
- **Application**: `/var/log/project88/`

### **Key Metrics to Monitor**
- Sync success rate (>95% target)
- Job queue depth (<100 pending jobs)
- Database connection health
- API rate limit usage
- Upcoming event coverage

This setup provides a production-ready, maintainable system that can scale with your business needs while ensuring reliable registration data synchronization. 