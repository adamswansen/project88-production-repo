#!/bin/bash

# RunSignUp Comprehensive Test Server Deployment Script
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
echo "🧪 RunSignUp Comprehensive Test Deployment"
echo "========================================="
echo -e "${NC}"

# Check if test file exists
if [[ ! -f "test_runsignup_comprehensive.py" ]]; then
    error "test_runsignup_comprehensive.py not found in current directory"
fi

# Test server connectivity
log "Testing server connectivity..."
if ! ssh -o ConnectTimeout=10 ${SERVER_USER}@${SERVER} "echo 'Connection successful'" 2>/dev/null; then
    error "Cannot connect to server ${SERVER}. Please check your SSH configuration."
fi

# Create server directory structure
log "Setting up server directory structure..."
ssh ${SERVER_USER}@${SERVER} "mkdir -p ${SERVER_PATH} ${SERVER_PATH}/logs ${SERVER_PATH}/test_results"

# Upload comprehensive test script
log "Uploading comprehensive test script to server..."
scp test_runsignup_comprehensive.py ${SERVER_USER}@${SERVER}:${SERVER_PATH}/

# Upload provider modules (needed for the test)
log "Uploading provider modules..."
scp -r providers/ ${SERVER_USER}@${SERVER}:${SERVER_PATH}/

# Upload requirements if needed
if [[ -f "requirements.txt" ]]; then
    log "Uploading requirements.txt..."
    scp requirements.txt ${SERVER_USER}@${SERVER}:${SERVER_PATH}/
fi

# Create and upload server test runner script
log "Creating server test runner script..."
cat > run_comprehensive_test_server.sh << 'EOF'
#!/bin/bash

# Server-side test runner for RunSignUp Comprehensive Test
set -e

SERVER_PATH="/opt/project88/provider-integrations"
cd ${SERVER_PATH}

echo "🚀 Starting RunSignUp Comprehensive Test on Production Server"
echo "=============================================================="

# Check if virtual environment exists, create if not
if [[ ! -d "test_env" ]]; then
    echo "📦 Creating test virtual environment..."
    python3 -m venv test_env
fi

# Activate virtual environment
source test_env/bin/activate

# Install/upgrade required packages
echo "📚 Installing required packages..."
pip install --upgrade pip
pip install psycopg2-binary requests python-dateutil

# Check PostgreSQL connection
echo "🔍 Testing PostgreSQL connection..."
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
    cursor.execute('SELECT version()')
    version = cursor.fetchone()
    print(f'✅ PostgreSQL connection successful: {version[0][:50]}...')
    conn.close()
except Exception as e:
    print(f'❌ PostgreSQL connection failed: {e}')
    exit(1)
"

# Run the comprehensive test
echo "🧪 Running comprehensive RunSignUp integration test..."
echo "Test started at: $(date)"

# Set environment variables for production database
export DB_HOST="localhost"
export DB_NAME="project88_myappdb"
export DB_USER="project88_myappuser"
export DB_PASSWORD="puctuq-cefwyq-3boqRe"
export DB_PORT="5432"

# Run the test with output to both console and log file
python3 test_runsignup_comprehensive.py 2>&1 | tee test_results/comprehensive_test_$(date +%Y%m%d_%H%M%S).log

echo "🎉 Test completed at: $(date)"
echo "📊 Test results saved in: test_results/"
echo "📋 Detailed logs available in: logs/"

# Show final summary
echo ""
echo "=== Test Summary ==="
if [[ -f "test_results/test_summary.json" ]]; then
    cat test_results/test_summary.json
fi

deactivate
EOF

# Upload the server runner script
scp run_comprehensive_test_server.sh ${SERVER_USER}@${SERVER}:${SERVER_PATH}/
ssh ${SERVER_USER}@${SERVER} "chmod +x ${SERVER_PATH}/run_comprehensive_test_server.sh"

# Option to run the test immediately
echo ""
info "✅ Deployment complete! Files uploaded to server."
echo ""
echo "📋 What was deployed:"
echo "   • test_runsignup_comprehensive.py - Main test script"
echo "   • providers/ - RunSignUp adapter modules"
echo "   • run_comprehensive_test_server.sh - Server test runner"
echo ""
echo "🚀 Next Steps:"
echo "   1. SSH to server: ssh ${SERVER_USER}@${SERVER}"
echo "   2. Navigate to: cd ${SERVER_PATH}"
echo "   3. Run test: ./run_comprehensive_test_server.sh"
echo ""

read -p "Would you like to run the test immediately? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log "🧪 Starting comprehensive test on production server..."
    echo ""
    
    # Run the test on the server
    ssh -t ${SERVER_USER}@${SERVER} "cd ${SERVER_PATH} && ./run_comprehensive_test_server.sh"
    
    log "🎉 Test execution complete!"
    echo ""
    echo "📊 Test results are available on the server at:"
    echo "   ${SERVER_PATH}/test_results/"
    echo "   ${SERVER_PATH}/logs/"
    
else
    info "Test deployment complete. Run manually when ready."
    echo ""
    echo "To run the test later:"
    echo "   ssh ${SERVER_USER}@${SERVER}"
    echo "   cd ${SERVER_PATH}"
    echo "   ./run_comprehensive_test_server.sh"
fi

echo ""
log "✅ RunSignUp Comprehensive Test deployment complete!" 