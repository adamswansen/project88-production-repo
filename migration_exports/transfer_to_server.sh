#!/bin/bash

# Replace with your actual server hostname/IP
SERVER="ai.project88hub.com"

echo "Transferring files to server..."
scp *.csv root@$SERVER:/tmp/
scp ../project88-production-repo/postgresql_migration_script.sql root@$SERVER:/tmp/

echo "Files transferred! You can now run the migration on the server."
echo "Next steps:"
echo "1. SSH to your server: ssh root@$SERVER"  
echo "2. Run: sudo -u postgres psql -d project88_myappdb -f /tmp/postgresql_migration_script.sql"
echo "3. Follow the import steps in MIGRATION_STEPS.md"
