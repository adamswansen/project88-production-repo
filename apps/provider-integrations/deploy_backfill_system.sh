#!/bin/bash

# RunSignUp Backfill & Scheduler System Deployment Script
set -e

# Server configuration
SERVER="ai.project88hub.com"
SERVER_USER="root"
SERVER_PATH="/opt/project88/provider-integrations"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

echo -e "${BLUE}"
echo "========================================="
echo "🚀 RunSignUp Backfill & Scheduler System"
echo "========================================="
echo -e "${NC}"

# Check if required files exist
REQUIRED_FILES=(
    "runsignup_backfill.py"
    "runsignup_scheduler.py"
    "providers/runsignup_adapter.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        error "Required file not found: $file"
    fi
done

log "✅ All required files present"

# Test SSH connection
info "🔗 Testing SSH connection to $SERVER..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes "$SERVER_USER@$SERVER" exit 2>/dev/null; then
    error "Cannot connect to $SERVER. Please check SSH configuration."
fi

log "✅ SSH connection successful"

# Deploy files to server
info "📦 Deploying backfill and scheduler system..."

# Create deployment directory structure
ssh "$SERVER_USER@$SERVER" "mkdir -p $SERVER_PATH/backfill_system"

# Upload backfill system files
log "📤 Uploading backfill script..."
scp runsignup_backfill.py "$SERVER_USER@$SERVER:$SERVER_PATH/backfill_system/"

log "📤 Uploading scheduler script..."
scp runsignup_scheduler.py "$SERVER_USER@$SERVER:$SERVER_PATH/backfill_system/"

# Upload updated adapter (if it exists)
if [ -f "providers/runsignup_adapter.py" ]; then
    log "📤 Uploading updated RunSignUp adapter..."
    scp providers/runsignup_adapter.py "$SERVER_USER@$SERVER:$SERVER_PATH/providers/"
fi

# Make scripts executable
ssh "$SERVER_USER@$SERVER" "chmod +x $SERVER_PATH/backfill_system/*.py"

log "✅ Files deployed successfully"

# Create environment setup script
info "🛠️ Creating environment setup script..."

cat << 'EOF' > temp_setup.sh
#!/bin/bash

# Environment setup for RunSignUp backfill system
cd /opt/project88/provider-integrations

# Check if virtual environment exists
if [ ! -d "production_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv production_env
fi

# Activate virtual environment
source production_env/bin/activate

# Install/update required packages
echo "Installing required packages..."
pip install -q --upgrade pip
pip install -q psycopg2-binary requests python-dateutil

# Set up environment variables
export DB_HOST="localhost"
export DB_NAME="project88_myappdb"
export DB_USER="project88_myappuser"
export DB_PASSWORD="puctuq-cefwyq-3boqRe"
export DB_PORT="5432"

# Configure sync settings
export SYNC_HOUR="2"
export LOOKBACK_HOURS="72"
export FUTURE_LOOKBACK_DAYS="7"
export RETRY_ATTEMPTS="3"
export RETRY_DELAY="5"
export RATE_LIMIT_DELAY="2"

echo "Environment setup complete!"
EOF

# Upload and run setup script
scp temp_setup.sh "$SERVER_USER@$SERVER:$SERVER_PATH/setup_backfill_env.sh"
ssh "$SERVER_USER@$SERVER" "chmod +x $SERVER_PATH/setup_backfill_env.sh"
rm temp_setup.sh

log "📤 Environment setup script uploaded"

# Run environment setup
info "🔧 Setting up environment on server..."
ssh "$SERVER_USER@$SERVER" "cd $SERVER_PATH && ./setup_backfill_env.sh"

log "✅ Environment setup complete"

# Create monitoring and management scripts
info "📊 Creating management scripts..."

# Create status check script
cat << 'EOF' > temp_status.sh
#!/bin/bash
cd /opt/project88/provider-integrations
source production_env/bin/activate

echo "========================================="
echo "🔍 RunSignUp System Status"
echo "========================================="

# Check database connection
echo "📊 Database Status:"
python3 -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'project88_myappdb'),
        user=os.getenv('DB_USER', 'project88_myappuser'),
        password=os.getenv('DB_PASSWORD', 'puctuq-cefwyq-3boqRe'),
        port=int(os.getenv('DB_PORT', '5432'))
    )
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM runsignup_events')
    events = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM runsignup_participants')
    participants = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(DISTINCT timing_partner_id) FROM partner_provider_credentials WHERE provider_id = 2')
    partners = cursor.fetchone()[0]
    print(f'✅ Database Connected - {partners} partners, {events} events, {participants} participants')
    conn.close()
except Exception as e:
    print(f'❌ Database Error: {e}')
"

# Check recent sync history
echo -e "\n📅 Recent Sync History:"
python3 -c "
import psycopg2
import os
from datetime import datetime, timedelta
try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'project88_myappdb'),
        user=os.getenv('DB_USER', 'project88_myappuser'),
        password=os.getenv('DB_PASSWORD', 'puctuq-cefwyq-3boqRe'),
        port=int(os.getenv('DB_PORT', '5432'))
    )
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timing_partner_id, sync_type, status, sync_time, events_synced, participants_synced
        FROM sync_history 
        WHERE provider_id = 2 AND sync_time > NOW() - INTERVAL '7 days'
        ORDER BY sync_time DESC LIMIT 10
    ''')
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f'   Partner {row[0]}: {row[1]} sync {row[2]} at {row[3]} - Events: {row[4]}, Participants: {row[5]}')
    else:
        print('   No recent sync history found')
    conn.close()
except Exception as e:
    print(f'❌ Error checking sync history: {e}')
"

# Check lock file
echo -e "\n🔒 Sync Lock Status:"
if [ -f /tmp/runsignup_sync.lock ]; then
    echo "⚠️  Sync lock active:"
    cat /tmp/runsignup_sync.lock
else
    echo "✅ No active sync lock"
fi

# Check log files
echo -e "\n📄 Recent Log Files:"
ls -la /opt/project88/provider-integrations/backfill_system/*backfill*.log 2>/dev/null | tail -3
ls -la /opt/project88/provider-integrations/backfill_system/*sync*.log 2>/dev/null | tail -3

echo "========================================="
EOF

scp temp_status.sh "$SERVER_USER@$SERVER:$SERVER_PATH/backfill_system/check_status.sh"
ssh "$SERVER_USER@$SERVER" "chmod +x $SERVER_PATH/backfill_system/check_status.sh"
rm temp_status.sh

log "✅ Status check script created"

# Show deployment summary
echo -e "\n${GREEN}========================================="
echo "🎉 DEPLOYMENT COMPLETE!"
echo "=========================================${NC}"

echo -e "\n📋 Available Commands on Server:"
echo -e "${BLUE}cd $SERVER_PATH/backfill_system${NC}"
echo ""
echo "🔄 Run complete backfill:"
echo -e "${YELLOW}python3 runsignup_backfill.py${NC}"
echo ""
echo "🧪 Test backfill (dry run):"
echo -e "${YELLOW}python3 runsignup_backfill.py --dry-run --limit 1${NC}"
echo ""
echo "📅 Run incremental sync:"
echo -e "${YELLOW}python3 runsignup_scheduler.py${NC}"
echo ""
echo "🧪 Test incremental sync:"
echo -e "${YELLOW}python3 runsignup_scheduler.py --test${NC}"
echo ""
echo "📊 Check system status:"
echo -e "${YELLOW}./check_status.sh${NC}"
echo ""
echo "📅 Set up cron job:"
echo -e "${YELLOW}python3 runsignup_scheduler.py --setup-cron${NC}"

# Offer to run backfill immediately
echo -e "\n${BLUE}Would you like to run the backfill now? (y/n)${NC}"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    info "🚀 Starting backfill on server..."
    
    # Run backfill with progress monitoring
    ssh -t "$SERVER_USER@$SERVER" "
        cd $SERVER_PATH/backfill_system
        source ../production_env/bin/activate
        export DB_HOST=localhost
        export DB_NAME=project88_myappdb
        export DB_USER=project88_myappuser
        export DB_PASSWORD=puctuq-cefwyq-3boqRe
        export DB_PORT=5432
        echo '🚀 Starting RunSignUp backfill...'
        python3 runsignup_backfill.py --limit 2  # Start with 2 partners for testing
    "
else
    info "⏸️ Backfill not started. Run manually when ready."
fi

echo -e "\n${GREEN}🎉 Deployment and setup complete!${NC}"

# Clean up any temporary files
rm -f temp_*.sh 