# 🔄 SQLite to PostgreSQL Migration Plan

## 📊 **Current State Analysis**

### **SQLite Database** (`race_results.db` - Desktop)
- RunSignUp tables (events, participants, races, counts)
- ChronoTrack tables (events, races, participants, results)
- Provider management (timing_partners, users, credentials)
- Sync infrastructure (sync_queue, sync_history)

### **PostgreSQL Database** (`project88_myappdb` - Server)
- Race display application data
- Raw timing data integration
- Some overlapping tables (likely timing_partners, users)

## 🎯 **Migration Approach**

### **Step 1: Analyze Schema Overlap**
First, let's see what's already in PostgreSQL vs SQLite to avoid conflicts.

```bash
# Check existing PostgreSQL tables
ssh root@your-server
sudo -u postgres psql -d project88_myappdb -c "\dt"
```

### **Step 2: Export SQLite Data**
```bash
# On your desktop - export data from SQLite
sqlite3 /Users/adamswansen/Desktop/race_results.db << 'EOF'
.mode csv
.headers on
.output timing_partners_export.csv
SELECT * FROM timing_partners;
.output runsignup_events_export.csv  
SELECT * FROM runsignup_events;
.output runsignup_participants_export.csv
SELECT * FROM runsignup_participants;
.output ct_events_export.csv
SELECT * FROM ct_events;
.output ct_participants_export.csv  
SELECT * FROM ct_participants;
.output ct_results_export.csv
SELECT * FROM ct_results;
.output sync_history_export.csv
SELECT * FROM sync_history;
-- Export other tables as needed
.quit
EOF
```

### **Step 3: Create PostgreSQL Schema**
Convert our SQLite enhancement script to PostgreSQL syntax.

### **Step 4: Import Data**
```bash
# Copy CSV files to server
scp *_export.csv root@your-server:/tmp/

# Import into PostgreSQL
sudo -u postgres psql -d project88_myappdb << 'EOF'
\copy timing_partners FROM '/tmp/timing_partners_export.csv' CSV HEADER;
\copy runsignup_events FROM '/tmp/runsignup_events_export.csv' CSV HEADER;
-- etc.
EOF
```

## 🔧 **PostgreSQL-Optimized Schema**

Key differences from SQLite:
- Use `SERIAL` instead of `INTEGER PRIMARY KEY AUTOINCREMENT`
- Use `TIMESTAMP` instead of `TEXT` for dates
- Use `JSONB` instead of `TEXT` for JSON data
- Add proper foreign key constraints
- Add PostgreSQL-specific indexes

## 📋 **Migration Checklist**

- [ ] Backup current PostgreSQL database
- [ ] Export all SQLite data to CSV
- [ ] Create PostgreSQL schema enhancements
- [ ] Import data with conflict resolution
- [ ] Test unified views with real data
- [ ] Update application connection strings
- [ ] Verify all timing partners' data integrity

## ⚠️ **Potential Conflicts**

1. **Duplicate timing_partners**: SQLite and PostgreSQL may have different partner IDs
2. **Date formats**: SQLite uses TEXT, PostgreSQL uses proper TIMESTAMP
3. **Auto-increment IDs**: Need to reset sequences after import
4. **Encoding issues**: Ensure UTF-8 compatibility

## 🎯 **Success Criteria**

- All provider data accessible via unified views
- Sync infrastructure ready for new providers
- Application can query across all providers
- Performance optimized for concurrent access 