#!/bin/bash

# Haku Backfill Launcher Script
# This script properly sets up the environment and runs the Haku backfill

set -e

# Change to the provider-integrations directory
cd /opt/project88/provider-integrations

# Activate virtual environment
source production_env/bin/activate

# Set environment variables
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
export RATE_LIMIT_DELAY="8"  # Conservative for Haku's 500 calls/hour

# Run the backfill script
echo "🚀 Starting Haku Backfill..."
echo "Working directory: $(pwd)"
echo "Python: $(which python3)"
echo "Current time: $(date)"

# Pass through command line arguments
python3 haku_backfill.py "$@"

echo "✅ Haku backfill completed!"
echo "📊 Check the generated log file for detailed results"
echo "🚀 Next step: Start the scheduler with python3 haku_event_driven_scheduler.py" 