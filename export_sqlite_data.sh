#!/bin/bash

# ========================================================================
# SQLite Data Export Script for Project88Hub Migration
# Run this on your desktop to export data from race_results.db
# ========================================================================

set -e  # Exit on any error

# Configuration
SQLITE_DB_PATH="/Users/adamswansen/Desktop/race_results.db"
EXPORT_DIR="/Users/adamswansen/Desktop/Project88/migration_exports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================================================${NC}"
echo -e "${BLUE}PROJECT88HUB - SQLite Data Export Script${NC}"
echo -e "${BLUE}========================================================================${NC}"

# Check if SQLite database exists
if [ ! -f "$SQLITE_DB_PATH" ]; then
    echo -e "${RED}ERROR: SQLite database not found at: $SQLITE_DB_PATH${NC}"
    echo -e "${YELLOW}Please check the path and try again.${NC}"
    exit 1
fi

# Create export directory
echo -e "${BLUE}Creating export directory...${NC}"
mkdir -p "$EXPORT_DIR"

# Backup the original database first
echo -e "${BLUE}Creating backup of original database...${NC}"
cp "$SQLITE_DB_PATH" "$EXPORT_DIR/race_results_backup_$TIMESTAMP.db"
echo -e "${GREEN}✓ Backup created: race_results_backup_$TIMESTAMP.db${NC}"

# Change to export directory
cd "$EXPORT_DIR"

# Function to export table data
export_table() {
    local table_name="$1"
    local filename="${table_name}.csv"
    
    echo -e "${YELLOW}Exporting table: $table_name${NC}"
    
    sqlite3 "$SQLITE_DB_PATH" <<EOF
.mode csv
.headers on
.output $filename
SELECT * FROM $table_name;
.quit
EOF
    
    if [ -f "$filename" ]; then
        local row_count=$(tail -n +2 "$filename" | wc -l | tr -d ' ')
        echo -e "${GREEN}✓ Exported $row_count rows to $filename${NC}"
    else
        echo -e "${RED}✗ Failed to export $table_name${NC}"
    fi
}

# Function to check if table exists
table_exists() {
    local table_name="$1"
    local result=$(sqlite3 "$SQLITE_DB_PATH" "SELECT name FROM sqlite_master WHERE type='table' AND name='$table_name';")
    [ "$result" = "$table_name" ]
}

echo -e "${BLUE}Starting data export...${NC}"

# Export core tables
echo -e "\n${BLUE}--- Core Infrastructure Tables ---${NC}"
table_exists "timing_partners" && export_table "timing_partners"
table_exists "users" && export_table "users"  
table_exists "providers" && export_table "providers"
table_exists "partner_provider_credentials" && export_table "partner_provider_credentials"

# Export sync infrastructure
echo -e "\n${BLUE}--- Sync Infrastructure Tables ---${NC}"
table_exists "sync_queue" && export_table "sync_queue"
table_exists "sync_history" && export_table "sync_history"

# Export RunSignUp tables
echo -e "\n${BLUE}--- RunSignUp Tables ---${NC}"
table_exists "runsignup_races" && export_table "runsignup_races"
table_exists "runsignup_events" && export_table "runsignup_events"
table_exists "runsignup_participants" && export_table "runsignup_participants"
table_exists "runsignup_participant_counts" && export_table "runsignup_participant_counts"

# Export ChronoTrack tables
echo -e "\n${BLUE}--- ChronoTrack Tables ---${NC}"
table_exists "ct_events" && export_table "ct_events"
table_exists "ct_races" && export_table "ct_races"
table_exists "ct_participants" && export_table "ct_participants"
table_exists "ct_results" && export_table "ct_results"
table_exists "ct_archived_events" && export_table "ct_archived_events"

# Export Haku tables (if they exist)
echo -e "\n${BLUE}--- Haku Tables ---${NC}"
table_exists "timing_partner_haku_orgs" && export_table "timing_partner_haku_orgs"
table_exists "haku_events" && export_table "haku_events"
table_exists "haku_participants" && export_table "haku_participants"

# List all exported files
echo -e "\n${BLUE}--- Export Summary ---${NC}"
echo -e "${YELLOW}Files exported to: $EXPORT_DIR${NC}"
ls -la *.csv 2>/dev/null || echo -e "${RED}No CSV files found${NC}"

# Create a manifest file
echo -e "\n${BLUE}Creating export manifest...${NC}"
echo "# Project88Hub SQLite Export Manifest" > export_manifest.txt
echo "# Generated: $(date)" >> export_manifest.txt
echo "# Source: $SQLITE_DB_PATH" >> export_manifest.txt
echo "# Export Directory: $EXPORT_DIR" >> export_manifest.txt
echo "" >> export_manifest.txt

for csv_file in *.csv; do
    if [ -f "$csv_file" ]; then
        row_count=$(tail -n +2 "$csv_file" | wc -l | tr -d ' ')
        echo "$csv_file: $row_count rows" >> export_manifest.txt
    fi
done

echo -e "${GREEN}✓ Export manifest created: export_manifest.txt${NC}"

# Create transfer script
echo -e "\n${BLUE}Creating transfer script...${NC}"
cat > transfer_to_server.sh <<'EOF'
#!/bin/bash

# Replace with your actual server hostname/IP
SERVER="your-server-hostname-or-ip"

echo "Transferring files to server..."
scp *.csv root@$SERVER:/tmp/
scp ../project88-production-repo/postgresql_migration_script.sql root@$SERVER:/tmp/

echo "Files transferred! You can now run the migration on the server."
echo "Next steps:"
echo "1. SSH to your server: ssh root@$SERVER"  
echo "2. Run: sudo -u postgres psql -d project88_myappdb -f /tmp/postgresql_migration_script.sql"
echo "3. Follow the import steps in MIGRATION_STEPS.md"
EOF

chmod +x transfer_to_server.sh
echo -e "${GREEN}✓ Transfer script created: transfer_to_server.sh${NC}"

# Display next steps
echo -e "\n${GREEN}========================================================================${NC}"
echo -e "${GREEN}EXPORT COMPLETED SUCCESSFULLY!${NC}"
echo -e "${GREEN}========================================================================${NC}"

echo -e "\n${YELLOW}📁 Files exported to: $EXPORT_DIR${NC}"
echo -e "\n${YELLOW}📋 Next Steps:${NC}"
echo -e "1. Review the exported files in: ${EXPORT_DIR}"
echo -e "2. Edit transfer_to_server.sh and set your server hostname"
echo -e "3. Run: ./transfer_to_server.sh to copy files to server"
echo -e "4. Follow MIGRATION_STEPS.md for the server-side migration"

echo -e "\n${BLUE}Files ready for transfer:${NC}"
ls -la *.csv | awk '{print "  " $9 " (" $5 " bytes)"}' 2>/dev/null

# Check for large files
echo -e "\n${BLUE}Checking for large files (>10MB):${NC}"
find . -name "*.csv" -size +10M -exec ls -lh {} \; | awk '{print "  ⚠️  " $9 " is large (" $5 ")"}' || echo -e "${GREEN}  ✓ No large files detected${NC}"

echo -e "\n${GREEN}Export complete! 🎉${NC}" 