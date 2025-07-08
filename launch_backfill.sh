#!/bin/bash

# RunSignUp Backfill Launcher Script
# This script properly sets up the environment and runs the backfill

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
export RATE_LIMIT_DELAY="2"

# Run the backfill script from the correct directory
echo "🚀 Starting RunSignUp Backfill..."
echo "Working directory: $(pwd)"
echo "Python: $(which python3)"

# Run the backfill script, but modify it to run from parent directory
python3 -c "
import sys
import os
sys.path.insert(0, '/opt/project88/provider-integrations')
os.chdir('/opt/project88/provider-integrations')

# Import and run the backfill
from backfill_system.runsignup_backfill import RunSignUpBackfill
import argparse

# Parse arguments
parser = argparse.ArgumentParser(description='RunSignUp Complete Backfill')
parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no data written)')
parser.add_argument('--limit', type=int, help='Limit number of timing partners (for testing)')
parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')

args = parser.parse_args()

# Create and run backfill
backfill = RunSignUpBackfill(dry_run=args.dry_run)
try:
    results = backfill.run_complete_backfill(partner_limit=args.limit)
    if results['stats']['errors'] == 0:
        print('🎉 Backfill completed successfully!')
        sys.exit(0)
    else:
        print(f'⚠️  Backfill completed with {results[\"stats\"][\"errors\"]} errors')
        sys.exit(1)
except KeyboardInterrupt:
    print('⏸️  Backfill interrupted by user')
    sys.exit(130)
except Exception as e:
    print(f'💥 Fatal error: {e}')
    sys.exit(1)
" "$@" 