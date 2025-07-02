# RunSignUp Production Server Deployment Guide

## Overview

This guide walks through deploying the RunSignUp sync system to your production server. The system needs to run on the server where your Project88Hub database resides and where it can access the RunSignUp APIs.

## Prerequisites

### Server Requirements
- **Linux/Unix server** with Python 3.x
- **Database access** to Project88Hub database
- **Internet connectivity** for RunSignUp API calls
- **SSH access** to the server
- **Sufficient disk space** for logs and virtual environment

### Local Development Status
✅ **Development Complete**: RunSignUp sync system fully implemented and tested
✅ **Documentation**: Complete implementation and deployment guides created
✅ **Ready for Server Deployment**: All files prepared for production deployment

## Files to Transfer to Server

The following files need to be uploaded to your production server:

```
provider-integrations/
├── runsignup_production_sync.py           # Main sync orchestrator
├── deploy_runsignup_production.sh         # Deployment script
├── providers/
│   ├── __init__.py
│   ├── base_adapter.py
│   └── runsignup_adapter.py               # RunSignUp API adapter
├── requirements.txt                       # Python dependencies
├── RUNSIGNUP_PRODUCTION_IMPLEMENTATION.md # Implementation docs
└── SERVER_DEPLOYMENT_GUIDE.md             # This guide
```

## Step-by-Step Server Deployment

### Step 1: Upload Files to Server

#### Option A: Using SCP
```bash
# From your local machine, upload the provider-integrations directory
scp -r project88-production-repo/apps/provider-integrations/ user@your-server:/path/to/project88/

# Or upload individual files
scp project88-production-repo/apps/provider-integrations/runsignup_production_sync.py user@your-server:/path/to/project88/provider-integrations/
scp project88-production-repo/apps/provider-integrations/deploy_runsignup_production.sh user@your-server:/path/to/project88/provider-integrations/
scp -r project88-production-repo/apps/provider-integrations/providers/ user@your-server:/path/to/project88/provider-integrations/
```

#### Option B: Using Git (if your server has git access)
```bash
# On your server
git clone your-repo-url
cd project88-production-repo/apps/provider-integrations
```

#### Option C: Using rsync
```bash
# From your local machine
rsync -avz project88-production-repo/apps/provider-integrations/ user@your-server:/path/to/project88/provider-integrations/
```

### Step 2: Connect to Your Server

```bash
# SSH into your production server
ssh user@your-production-server

# Navigate to the project directory
cd /path/to/project88/provider-integrations
```

### Step 3: Verify Database Location

```bash
# Check if your database exists and note the path
ls -la ../../race_results.db
# OR
find /path -name "race_results.db" 2>/dev/null

# If database is in a different location, update the path in runsignup_production_sync.py
```

### Step 4: Update Database Path (if needed)

If your database is not at `../../race_results.db`, update the path:

```bash
# Edit the sync script to point to correct database location
nano runsignup_production_sync.py

# Look for this line and update the path:
# def __init__(self, db_path: str = "../../race_results.db"):
# Change to your actual database path, e.g.:
# def __init__(self, db_path: str = "/var/lib/project88/race_results.db"):
```

### Step 5: Run Server Deployment

```bash
# Make deployment script executable
chmod +x deploy_runsignup_production.sh

# Run the deployment script
./deploy_runsignup_production.sh
```

The deployment script will:
1. ✅ Validate environment and dependencies
2. ✅ Create production virtual environment
3. ✅ Install required packages (requests, urllib3, schedule, python-dateutil)
4. ✅ Run test sync with first timing partner
5. ✅ Offer options for full production sync

### Step 6: Production Sync Options

After successful deployment, you'll see these options:

#### Option A: Run Full Sync Immediately
```bash
# If prompted during deployment, choose 'y' to run full sync
# OR run manually:
source production_env/bin/activate
python runsignup_production_sync.py
```

#### Option B: Test with Single Partner First
```bash
source production_env/bin/activate
python runsignup_production_sync.py --test
```

#### Option C: Set Up Automated Daily Sync
```bash
# Set up cron job for daily sync at 2 AM
echo '0 2 * * * cd /path/to/project88/provider-integrations && source production_env/bin/activate && python runsignup_production_sync.py >> sync_cron.log 2>&1' | crontab -

# Verify cron job
crontab -l
```

## Server-Specific Considerations

### Database Permissions
```bash
# Ensure the database is accessible
ls -la /path/to/race_results.db

# If permission issues, adjust ownership
sudo chown your-user:your-group /path/to/race_results.db
```

### Log File Locations
```bash
# Logs will be created in the deployment directory
/path/to/project88/provider-integrations/runsignup_sync.log       # Detailed sync logs
/path/to/project88/provider-integrations/sync_cron.log            # Cron job logs
/path/to/project88/provider-integrations/runsignup_sync_summary.json  # Sync summary
```

### Firewall/Network Access
```bash
# Ensure server can reach RunSignUp API
curl -I https://runsignup.com/rest/

# Should return HTTP 200 OK
```

### System Service Setup (Optional)
For more robust deployment, you can set up a systemd service:

```bash
# Create service file
sudo nano /etc/systemd/system/runsignup-sync.service
```

```ini
[Unit]
Description=RunSignUp Sync Service
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/project88/provider-integrations
ExecStart=/path/to/project88/provider-integrations/production_env/bin/python runsignup_production_sync.py
StandardOutput=append:/var/log/runsignup-sync.log
StandardError=append:/var/log/runsignup-sync.log

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable runsignup-sync.service
sudo systemctl start runsignup-sync.service

# Check service status
sudo systemctl status runsignup-sync.service
```

## Monitoring on Server

### Real-time Log Monitoring
```bash
# Follow sync logs
tail -f runsignup_sync.log

# Follow cron logs  
tail -f sync_cron.log

# Follow system logs (if using systemd)
sudo journalctl -u runsignup-sync.service -f
```

### Check Sync Results
```bash
# View sync summary
cat runsignup_sync_summary.json | python3 -m json.tool

# Quick summary
python3 -c "
import json
try:
    with open('runsignup_sync_summary.json', 'r') as f:
        data = json.load(f)
    print(f'✅ Synced {data[\"total_races\"]} races, {data[\"total_events\"]} events, {data[\"total_participants\"]} participants')
    print(f'⏱️  Duration: {data[\"duration_seconds\"]:.2f} seconds')
    print(f'📈 {data[\"timing_partners_synced\"]} timing partners processed')
    if data['failed_syncs']:
        print(f'⚠️  {len(data[\"failed_syncs\"])} partners had errors')
    else:
        print('✅ All partners synced successfully!')
except FileNotFoundError:
    print('❌ No sync summary found - sync may not have completed yet')
except Exception as e:
    print(f'❌ Error reading sync summary: {e}')
"
```

### Database Verification
```bash
# Check if data was synced (replace with your actual database path)
sqlite3 /path/to/race_results.db "
SELECT 
    COUNT(*) as total_runsignup_participants,
    COUNT(DISTINCT timing_partner_id) as timing_partners
FROM runsignup_participants;
"

# Check recent sync history
sqlite3 /path/to/race_results.db "
SELECT 
    sync_time,
    num_of_synced_records,
    status,
    reason
FROM sync_history 
WHERE sync_time >= datetime('now', '-1 day')
ORDER BY sync_time DESC
LIMIT 10;
"
```

## Troubleshooting Server Issues

### Common Server-Specific Problems

#### Database Connection Issues
```bash
# Check database file exists and permissions
ls -la /path/to/race_results.db
file /path/to/race_results.db

# Test database connection
sqlite3 /path/to/race_results.db "SELECT COUNT(*) FROM partner_provider_credentials WHERE provider_id = 2;"
```

#### Python/Virtual Environment Issues
```bash
# Check Python version
python3 --version

# Recreate virtual environment if needed
rm -rf production_env
python3 -m venv production_env
source production_env/bin/activate
pip install requests urllib3 schedule python-dateutil
```

#### Network/API Access Issues
```bash
# Test RunSignUp API connectivity
curl -v https://runsignup.com/rest/race

# Check DNS resolution
nslookup runsignup.com

# Test with actual credentials (replace with real values)
curl -X GET "https://runsignup.com/rest/races?api_key=YOUR_KEY&api_secret=YOUR_SECRET&format=json"
```

#### Permission Issues
```bash
# Fix file permissions
chmod +x runsignup_production_sync.py
chmod +x deploy_runsignup_production.sh

# Fix directory permissions
chmod 755 providers/
chmod 644 providers/*.py
```

### Log Analysis on Server

#### Success Indicators
```bash
# Look for these patterns in logs
grep "✅" runsignup_sync.log | tail -5
grep "Authentication successful" runsignup_sync.log
grep "RunSignUp Production Sync Complete" runsignup_sync.log
```

#### Error Indicators
```bash
# Look for error patterns
grep "❌\|ERROR\|Failed" runsignup_sync.log | tail -10
grep "Authentication failed" runsignup_sync.log
grep "Critical error" runsignup_sync.log
```

## Production Maintenance

### Regular Tasks
- **Daily**: Check sync logs for errors
- **Weekly**: Review sync summary reports
- **Monthly**: Update API credentials if needed
- **Quarterly**: Review and archive old log files

### Log Rotation
```bash
# Set up log rotation to prevent disk space issues
sudo nano /etc/logrotate.d/runsignup-sync

# Add this content:
/path/to/project88/provider-integrations/runsignup_sync.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 644 your-user your-group
}
```

### Backup Strategy
```bash
# Backup database before major syncs
cp /path/to/race_results.db /path/to/backups/race_results_$(date +%Y%m%d_%H%M%S).db

# Backup sync configuration
tar -czf runsignup_sync_backup_$(date +%Y%m%d).tar.gz runsignup_production_sync.py providers/ production_env/
```

## Next Steps After Deployment

1. ✅ **Verify first sync completes successfully**
2. ✅ **Set up automated daily sync schedule**
3. ✅ **Configure monitoring and alerting**
4. ✅ **Document server-specific paths and procedures**
5. ✅ **Plan integration with other provider sync systems**

---

**Server Deployment Status**: 📋 Ready for Production  
**Required Action**: Upload files and run deployment script on server  
**Estimated Deployment Time**: 10-15 minutes  
**Post-Deployment Testing**: 5-10 minutes 