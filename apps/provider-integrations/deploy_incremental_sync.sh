#!/bin/bash

# Deploy Incremental Sync Optimization to Production Server
# This script safely deploys the optimized sync worker

echo "🚀 Deploying Incremental Sync Optimization to Production"
echo "======================================================"

# Production server details
SERVER="2a02:4780:2d:44b3::1"
USER="root"
REMOTE_DIR="/opt/project88/provider-integrations"
LOCAL_DIR="."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we can connect to server
echo "🔍 Checking server connectivity..."
if ! ssh -6 -o ConnectTimeout=10 "$USER@$SERVER" "echo 'Connected successfully'" >/dev/null 2>&1; then
    print_error "Cannot connect to server $SERVER"
    exit 1
fi
print_status "Server connection successful"

# Backup current production sync script
echo "💾 Creating backup of current production sync script..."
ssh -6 "$USER@$SERVER" "cp $REMOTE_DIR/runsignup_production_sync.py $REMOTE_DIR/runsignup_production_sync.py.backup.$(date +%Y%m%d_%H%M%S)"
print_status "Backup created"

# Copy optimized sync script
echo "📁 Copying optimized sync script to server..."
scp -6 runsignup_production_sync.py "$USER@$SERVER:$REMOTE_DIR/"
print_status "Optimized sync script deployed"

# Copy test script
echo "📁 Copying test script to server..."
scp -6 test_incremental_sync.py "$USER@$SERVER:$REMOTE_DIR/"
print_status "Test script deployed"

# Run a quick test to validate the optimization
echo "🧪 Running validation test on server..."
ssh -6 "$USER@$SERVER" "cd $REMOTE_DIR && python3 runsignup_production_sync.py --test --timing-partner 2 --incremental-days 1 2>&1 | head -20"

# Check if test was successful
if [ $? -eq 0 ]; then
    print_status "Validation test completed successfully"
else
    print_warning "Validation test had issues - check logs"
fi

# Show current cron schedule
echo "⏰ Current cron schedule:"
ssh -6 "$USER@$SERVER" "crontab -l | grep sync"

# Provide next steps
echo ""
echo "🎯 Next Steps:"
echo "1. Monitor tonight's sync performance (starts at 2:00 AM UTC)"
echo "2. Check sync logs: ssh -6 $USER@$SERVER 'tail -f $REMOTE_DIR/runsignup_sync.log'"
echo "3. Run manual test: ssh -6 $USER@$SERVER 'cd $REMOTE_DIR && python3 test_incremental_sync.py'"
echo "4. View sync summary: ssh -6 $USER@$SERVER 'cat $REMOTE_DIR/runsignup_sync_summary.json'"
echo ""
echo "🔄 To force a full sync (if needed):"
echo "   ssh -6 $USER@$SERVER 'cd $REMOTE_DIR && python3 runsignup_production_sync.py --force-full-sync'"
echo ""
echo "⚡ To test single timing partner:"
echo "   ssh -6 $USER@$SERVER 'cd $REMOTE_DIR && python3 runsignup_production_sync.py --timing-partner 2'"
echo ""

print_status "Deployment completed successfully! 🎉"
print_warning "Monitor tonight's sync to confirm performance improvement" 