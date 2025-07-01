# 🚀 SQLite to PostgreSQL Migration Guide

## 📋 **Pre-Migration Checklist**

### **1. Backup Everything**
```bash
# On your desktop - backup SQLite database
cp /Users/adamswansen/Desktop/race_results.db /Users/adamswansen/Desktop/race_results_backup_$(date +%Y%m%d).db

# On server - backup PostgreSQL database
ssh root@your-server
sudo -u postgres pg_dump project88_myappdb > /tmp/project88_myappdb_backup_$(date +%Y%m%d).sql
```

### **2. Check Current PostgreSQL Setup**
```bash
ssh root@your-server

# Check PostgreSQL is running
sudo systemctl status postgresql

# Check existing tables in project88_myappdb
sudo -u postgres psql -d project88_myappdb -c "\dt"

# Check existing data
sudo -u postgres psql -d project88_myappdb -c "SELECT COUNT(*) FROM timing_partners;"
```

## 🔄 **Migration Steps**

### **Step 1: Export Data from SQLite**
```bash
# On your desktop - export all data to CSV files
cd /Users/adamswansen/Desktop/

sqlite3 race_results.db << 'EOF'
.mode csv
.headers on

.output timing_partners.csv
SELECT * FROM timing_partners;

.output providers.csv  
SELECT * FROM providers;

.output runsignup_events.csv
SELECT * FROM runsignup_events;

.output runsignup_participants.csv
SELECT * FROM runsignup_participants;

.output ct_events.csv
SELECT * FROM ct_events;

.output ct_participants.csv
SELECT * FROM ct_participants;

.output ct_results.csv
SELECT * FROM ct_results;

.output sync_history.csv
SELECT * FROM sync_history;

.output partner_provider_credentials.csv
SELECT * FROM partner_provider_credentials;

.quit
EOF

# Verify CSV files were created
ls -la *.csv
```

### **Step 2: Transfer Files to Server**
```bash
# Copy CSV files and migration script to server
scp *.csv root@your-server:/tmp/
scp project88-production-repo/postgresql_migration_script.sql root@your-server:/tmp/
```

### **Step 3: Run PostgreSQL Migration**
```bash
ssh root@your-server

# Execute the migration script
sudo -u postgres psql -d project88_myappdb -f /tmp/postgresql_migration_script.sql

# Check for any errors
echo "Migration completed. Check output above for any errors."
```

### **Step 4: Import Data**
```bash
# Still on the server - import the CSV data

sudo -u postgres psql -d project88_myappdb << 'EOF'

-- Import timing partners (handle conflicts)
\copy timing_partners(timing_partner_id, company_name, access_password) FROM '/tmp/timing_partners.csv' CSV HEADER;

-- Import RunSignUp events
\copy runsignup_events FROM '/tmp/runsignup_events.csv' CSV HEADER;

-- Import RunSignUp participants  
\copy runsignup_participants FROM '/tmp/runsignup_participants.csv' CSV HEADER;

-- Import ChronoTrack events
\copy ct_events FROM '/tmp/ct_events.csv' CSV HEADER;

-- Import ChronoTrack participants
\copy ct_participants FROM '/tmp/ct_participants.csv' CSV HEADER;

-- Import ChronoTrack results
\copy ct_results FROM '/tmp/ct_results.csv' CSV HEADER;

-- Import sync history
\copy sync_history FROM '/tmp/sync_history.csv' CSV HEADER;

-- Import provider credentials
\copy partner_provider_credentials FROM '/tmp/partner_provider_credentials.csv' CSV HEADER;

EOF
```

### **Step 5: Fix Sequences and Constraints**
```bash
sudo -u postgres psql -d project88_myappdb << 'EOF'

-- Reset auto-increment sequences to correct values
SELECT setval('timing_partners_timing_partner_id_seq', (SELECT MAX(timing_partner_id) FROM timing_partners));
SELECT setval('providers_provider_id_seq', (SELECT MAX(provider_id) FROM providers));
SELECT setval('runsignup_participants_id_seq', (SELECT MAX(id) FROM runsignup_participants));
SELECT setval('ct_results_id_seq', (SELECT MAX(id) FROM ct_results));

EOF
```

### **Step 6: Test Migration**
```bash
sudo -u postgres psql -d project88_myappdb << 'EOF'

-- Test data integrity
SELECT 'timing_partners' as table_name, COUNT(*) as row_count FROM timing_partners
UNION ALL
SELECT 'runsignup_events' as table_name, COUNT(*) as row_count FROM runsignup_events  
UNION ALL
SELECT 'ct_events' as table_name, COUNT(*) as row_count FROM ct_events
UNION ALL
SELECT 'unified_events' as table_name, COUNT(*) as row_count FROM unified_events;

-- Test unified views
SELECT source_provider, COUNT(*) as event_count 
FROM unified_events 
GROUP BY source_provider;

-- Test sample data
SELECT * FROM unified_events LIMIT 5;

EOF
```

### **Step 7: Update Application Connections**
```bash
# Find applications that need database connection updates
# Update connection strings from SQLite file path to PostgreSQL connection

# Example connection change:
# FROM: sqlite:///path/to/race_results.db  
# TO:   postgresql://project88_myappuser:password@localhost:5432/project88_myappdb
```

## ✅ **Verification Checklist**

- [ ] All CSV files exported successfully
- [ ] Migration script ran without errors
- [ ] Data imported without conflicts
- [ ] Sequences reset correctly
- [ ] Unified views return data
- [ ] Row counts match between SQLite and PostgreSQL
- [ ] Sample queries work correctly

## 🚨 **Troubleshooting**

### **Common Issues**

**1. Foreign Key Violations**
```sql
-- Temporarily disable foreign key checks during import
SET session_replication_role = replica;
-- Run imports
SET session_replication_role = DEFAULT;
```

**2. Data Type Mismatches**
```sql
-- Check for data type issues
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'your_table_name';
```

**3. Sequence Issues**
```sql
-- Check sequence current values
SELECT sequence_name, last_value 
FROM information_schema.sequences;
```

### **If Migration Fails**

1. **Restore PostgreSQL backup**:
   ```bash
   sudo -u postgres psql -d project88_myappdb < /tmp/project88_myappdb_backup_YYYYMMDD.sql
   ```

2. **Check error logs**:
   ```bash
   sudo tail -f /var/log/postgresql/postgresql-*.log
   ```

3. **Start over with clean database**:
   ```bash
   sudo -u postgres dropdb project88_myappdb
   sudo -u postgres createdb project88_myappdb
   # Re-run migration
   ```

## 🎯 **Next Steps After Migration**

1. **Test unified views thoroughly**
2. **Update application configuration** to use PostgreSQL
3. **Set up provider API integrations**
4. **Build sync job infrastructure**
5. **Create monitoring dashboard**

## 📞 **Need Help?**

If you encounter issues during migration:
1. **Save the error messages** exactly as they appear
2. **Check which step failed** (export, transfer, schema, import, sequences)
3. **Verify data integrity** with the test queries above

The migration should be straightforward, but PostgreSQL is stricter about data types and constraints than SQLite, so some manual fixes may be needed. 