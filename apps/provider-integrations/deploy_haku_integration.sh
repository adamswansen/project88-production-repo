#!/bin/bash
# Deploy Complete Haku Integration to Production Server

echo "🚀 Deploying Haku Integration to Production Server"
echo "============================================================"

# Server configuration  
SERVER="ai.project88hub.com"
SERVER_PATH="/opt/project88/provider-integrations"

echo "📦 Creating Haku integration package..."
tar -czf haku_integration_package.tar.gz \
    haku_event_driven_scheduler.py \
    migrate_haku_credentials.py \
    providers/haku_adapter.py \
    providers/__init__.py \
    requirements.txt

echo "📤 Uploading to server..."
scp haku_integration_package.tar.gz root@${SERVER}:${SERVER_PATH}/

echo "🔧 Installing Haku integration on server..."
ssh root@${SERVER} << 'EOF'
cd /opt/project88/provider-integrations

# Extract the package
tar -xzf haku_integration_package.tar.gz

# Make scripts executable
chmod +x haku_event_driven_scheduler.py
chmod +x migrate_haku_credentials.py

echo "✅ Haku integration files installed successfully!"

# Step 1: Migrate existing Haku credentials
echo ""
echo "🔄 Step 1: Migrating existing Haku credentials..."
python3 migrate_haku_credentials.py

# Step 2: Test Haku adapter authentication
echo ""
echo "🧪 Step 2: Testing Haku authentication..."
python3 -c "
from providers.haku_adapter import HakuAdapter
import psycopg2
import psycopg2.extras

# Test with first migrated credential
conn = psycopg2.connect(
    host='localhost',
    database='project88_myappdb',
    user='project88_myappuser', 
    password='puctuq-cefwyq-3boqRe',
    port=5432
)
cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

cursor.execute('''
    SELECT ppc.principal, ppc.additional_config, tp.company_name
    FROM partner_provider_credentials ppc
    JOIN timing_partners tp ON ppc.timing_partner_id = tp.timing_partner_id
    WHERE ppc.provider_id = (SELECT provider_id FROM providers WHERE name = 'Haku')
    LIMIT 1
''')

result = cursor.fetchone()
if result:
    credentials = {
        'principal': result['principal'],
        'additional_config': result['additional_config'] or {}
    }
    
    adapter = HakuAdapter(credentials)
    if adapter.authenticate():
        print('✅ Haku authentication successful!')
    else:
        print('❌ Haku authentication failed')
else:
    print('⚠️  No Haku credentials found')

conn.close()
"

# Step 3: Run initial events discovery
echo ""
echo "🔍 Step 3: Running initial events discovery..."
python3 haku_event_driven_scheduler.py --discover-only

# Step 4: Show next steps
echo ""
echo "============================================================"
echo "✅ Haku Integration Deployment Complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Start Haku scheduler: python3 haku_event_driven_scheduler.py"
echo "2. Or run in background: nohup python3 haku_event_driven_scheduler.py > haku_scheduler_\$(date +%Y%m%d_%H%M).log 2>&1 &"
echo "3. Monitor logs: tail -f haku_event_driven_*.log"
echo "4. Check status: python3 haku_event_driven_scheduler.py --status"
echo ""
echo "📊 Expected Daily Operations:"
echo "• Events discovery: 6 AM & 6 PM UTC"
echo "• Participant sync: Variable frequency based on event proximity"
echo "• Rate limiting: 2 seconds between API calls (conservative)"
echo ""
EOF

echo "🧹 Cleaning up..."
rm haku_integration_package.tar.gz

echo "============================================================"
echo "✅ Deployment Complete!"
echo ""
echo "📋 Manual Steps on Server:"
echo "1. SSH to server: ssh root@ai.project88hub.com"
echo "2. Navigate to: cd /opt/project88/provider-integrations"  
echo "3. Review migrated credentials: python3 migrate_haku_credentials.py --verify"
echo "4. Start Haku scheduler: python3 haku_event_driven_scheduler.py"
echo ""
echo "🔗 Your Existing Haku Organizations:"
echo "   • BIX (Partners 1 & 7)"
echo "   • Goal Foundation (Partner 3)"
echo "   • Atlanta Track Club (Partner 4)" 