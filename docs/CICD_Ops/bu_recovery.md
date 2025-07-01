# Backup & Disaster Recovery

## 📊 Overview

Project88's backup and disaster recovery strategy ensures business continuity for our production race timing SaaS platform serving 13+ timing partners with 10.6M+ records.

## 🔐 Backup Strategy

### Database Backups

| Item | Method | Frequency | Retention | Storage |
|------|--------|-----------|-----------|---------|
| **PostgreSQL Base Backup** | `pg_dump` pipe to `lz4` | Nightly 03:00 ET | 14 days | S3: `s3://p88-backup/prod/YYYY-MM-DD.sql.lz4` |
| **WAL Archive** | `wal-g` continuous push | Real-time | 7 days | S3: `s3://p88-backup/wal/` |
| **Raw Timing Data** | PostgreSQL dump | Nightly 04:00 ET | 30 days | S3: `s3://p88-backup/timing/` |
| **Application Code** | Git commits | Per change | Forever | GitLab + S3 mirror |
| **Configuration Files** | Ansible vault | Per change | Forever | Git repository |

### Backup Implementation

```bash
# Nightly database backup script
#!/bin/bash
# /opt/scripts/backup-prod.sh

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/tmp/backups"
S3_BUCKET="s3://p88-backup"

# Production database backup
pg_dump -h localhost -U project88_myappuser project88_myappdb | \
  lz4 -9 > ${BACKUP_DIR}/prod-${DATE}.sql.lz4

# Raw timing database backup  
pg_dump -h localhost -U race_timing_user raw_tag_data | \
  lz4 -9 > ${BACKUP_DIR}/timing-${DATE}.sql.lz4

# Upload to S3
aws s3 cp ${BACKUP_DIR}/prod-${DATE}.sql.lz4 ${S3_BUCKET}/prod/
aws s3 cp ${BACKUP_DIR}/timing-${DATE}.sql.lz4 ${S3_BUCKET}/timing/

# Cleanup old local backups
find ${BACKUP_DIR} -name "*.lz4" -mtime +7 -delete