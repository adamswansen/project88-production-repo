#!/bin/bash
# Deploy Event-Driven Scheduler to Production Server

echo "🚀 Deploying Event-Driven Scheduler to Production Server"
echo "============================================================"

# Server configuration  
SERVER="ai.project88hub.com"
SERVER_PATH="/opt/project88/provider-integrations"

echo "📦 Creating server package..."
tar -czf runsignup_event_driven_scheduler.tar.gz runsignup_event_driven_scheduler.py providers/ requirements.txt

echo "📤 Uploading to server..."
scp runsignup_event_driven_scheduler.tar.gz root@${SERVER}:${SERVER_PATH}/

echo "🔧 Installing on server..."
ssh root@${SERVER} "cd ${SERVER_PATH} && tar -xzf runsignup_event_driven_scheduler.tar.gz && chmod +x runsignup_event_driven_scheduler.py && echo \"✅ Event-Driven Scheduler installed successfully!\""

echo "🧹 Cleaning up..."
rm runsignup_event_driven_scheduler.tar.gz

echo "============================================================"
echo "✅ Deployment Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. SSH to server: ssh root@ai.project88hub.com"
echo "2. Navigate to: cd /opt/project88/provider-integrations"  
echo "3. Start scheduler: python3 runsignup_event_driven_scheduler.py"
echo "4. Or test discovery: python3 runsignup_event_driven_scheduler.py --discover-only"
echo "5. Check status: python3 runsignup_event_driven_scheduler.py --status"
