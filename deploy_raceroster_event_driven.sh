#!/bin/bash

# Deploy Race Roster Event-Driven Scheduler
# This replaces the simple daily sync with sophisticated event-driven scheduling

set -e

echo "🚀 Deploying Race Roster Event-Driven Scheduler..."

# Deploy the new scheduler
echo "📤 Uploading event-driven scheduler..."
scp raceroster_scheduler.py root@ai.project88hub.com:/opt/project88/provider-integrations/
scp raceroster_daily_sync.sh root@ai.project88hub.com:/opt/project88/provider-integrations/

# Make scripts executable
ssh root@ai.project88hub.com 'cd /opt/project88/provider-integrations && chmod +x raceroster_scheduler.py raceroster_daily_sync.sh'

# Stop any existing simple scheduler
echo "🛑 Stopping any existing Race Roster processes..."
ssh root@ai.project88hub.com 'pkill -f "raceroster_backfill\|raceroster_production_sync" || true'

# Update crontab to use event-driven scheduler as a daemon
echo "⚙️  Setting up cron job for event-driven scheduler..."
ssh root@ai.project88hub.com 'cat > /tmp/raceroster_cron.txt << EOF
# Race Roster Event-Driven Scheduler - runs continuously as daemon
# Check every minute if scheduler is running, restart if needed
* * * * * /opt/project88/provider-integrations/raceroster_daily_sync.sh > /dev/null 2>&1

EOF'

# Install the new cron job
ssh root@ai.project88hub.com 'crontab -l | grep -v raceroster | cat - /tmp/raceroster_cron.txt | crontab -'

# Create a systemd service for the event-driven scheduler
echo "🔧 Creating systemd service for Race Roster Event-Driven Scheduler..."
ssh root@ai.project88hub.com 'cat > /etc/systemd/system/raceroster-scheduler.service << EOF
[Unit]
Description=Race Roster Event-Driven Scheduler
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/project88/provider-integrations
ExecStart=/usr/bin/python3 /opt/project88/provider-integrations/raceroster_scheduler.py
Restart=always
RestartSec=30
StandardOutput=append:/opt/project88/provider-integrations/raceroster_event_driven.log
StandardError=append:/opt/project88/provider-integrations/raceroster_event_driven.log

[Install]
WantedBy=multi-user.target
EOF'

# Enable and start the service
ssh root@ai.project88hub.com 'systemctl daemon-reload && systemctl enable raceroster-scheduler.service'

# Start the scheduler
echo "🚀 Starting Race Roster Event-Driven Scheduler..."
ssh root@ai.project88hub.com 'systemctl start raceroster-scheduler.service'

# Check status
echo "📊 Checking scheduler status..."
ssh root@ai.project88hub.com 'systemctl status raceroster-scheduler.service --no-pager -l'

# Show recent logs
echo "📋 Recent scheduler logs:"
ssh root@ai.project88hub.com 'cd /opt/project88/provider-integrations && tail -n 20 raceroster_event_driven*.log 2>/dev/null || echo "No logs yet - scheduler just started"'

echo ""
echo "✅ Race Roster Event-Driven Scheduler deployed successfully!"
echo ""
echo "📊 Key Features:"
echo "   🔍 Event discovery: 6 AM and 6 PM daily"
echo "   ⏰ Dynamic frequency based on event proximity:"
echo "      • Outside 24 hours: Every 4 hours"
echo "      • Within 24 hours: Every 15 minutes"
echo "      • Within 4 hours: Every minute"
echo "      • Stop: 1 hour after event start"
echo "   🎯 Priority-based processing with cycle limits"
echo ""
echo "🔧 Management commands:"
echo "   systemctl status raceroster-scheduler     # Check status"
echo "   systemctl restart raceroster-scheduler    # Restart scheduler"
echo "   systemctl stop raceroster-scheduler       # Stop scheduler"
echo "   tail -f /opt/project88/provider-integrations/raceroster_event_driven*.log  # View logs"
echo ""
echo "🎉 Race Roster now matches RunSignUp's sophisticated event-driven scheduling!" 