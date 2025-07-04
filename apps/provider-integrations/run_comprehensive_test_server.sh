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
