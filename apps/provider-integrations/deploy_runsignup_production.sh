#!/bin/bash
# RunSignUp Production Deployment Script
# This script sets up and runs the RunSignUp sync system on your production server

set -e  # Exit on any error

echo "🚀 RunSignUp Production Deployment"
echo "=================================="

# Check if we're in the right directory
if [[ ! -f "runsignup_production_sync.py" ]]; then
    echo "❌ Error: runsignup_production_sync.py not found"
    echo "Please run this script from the provider-integrations directory"
    exit 1
fi

# Check if database exists
if [[ ! -f "../../race_results.db" ]]; then
    echo "❌ Error: race_results.db not found"
    echo "Please ensure the database is in the correct location"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "production_env" ]]; then
    echo "📦 Creating production virtual environment..."
    python3 -m venv production_env
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source production_env/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install requests urllib3 schedule python-dateutil

# Make sync script executable
chmod +x runsignup_production_sync.py

# Test with first timing partner only
echo ""
echo "🧪 Running test sync (first timing partner only)..."
echo "This will verify everything is working before full sync"
python runsignup_production_sync.py --test

if [[ $? -eq 0 ]]; then
    echo ""
    echo "✅ Test sync completed successfully!"
    echo ""
    echo "🎯 Ready for production sync options:"
    echo ""
    echo "1. Run full sync now:"
    echo "   python runsignup_production_sync.py"
    echo ""
    echo "2. Set up automated sync (daily at 2 AM):"
    echo "   echo '0 2 * * * cd $(pwd) && source production_env/bin/activate && python runsignup_production_sync.py >> sync_cron.log 2>&1' | crontab -"
    echo ""
    echo "3. Monitor sync logs:"
    echo "   tail -f runsignup_sync.log"
    echo ""
    echo "4. View sync summary:"
    echo "   cat runsignup_sync_summary.json"
    echo ""
    
    read -p "Would you like to run the full sync now? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🚀 Starting full production sync..."
        python runsignup_production_sync.py
        echo ""
        echo "📊 Sync Summary:"
        if [[ -f "runsignup_sync_summary.json" ]]; then
            python3 -c "
import json
with open('runsignup_sync_summary.json', 'r') as f:
    data = json.load(f)
print(f\"✅ Synced {data['total_races']} races, {data['total_events']} events, {data['total_participants']} participants\")
print(f\"⏱️  Duration: {data['duration_seconds']:.2f} seconds\")
print(f\"📈 {data['timing_partners_synced']} timing partners processed\")
if data['failed_syncs']:
    print(f\"⚠️  {len(data['failed_syncs'])} partners had errors\")
else:
    print('✅ All partners synced successfully!')
"
        fi
    fi
else
    echo "❌ Test sync failed. Please check the logs and fix any issues before deploying."
    exit 1
fi

echo ""
echo "🎉 RunSignUp Production Deployment Complete!"
echo "Check runsignup_sync.log for detailed logs" 