#!/usr/bin/env python3
"""
Project88Hub Development Database Refresh Script
Maintains last 500 events with all related data while preserving referential integrity
"""

import os
import sys
import psycopg2
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import subprocess
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/project88/db_refresh.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DatabaseRefreshManager:
    """Manages development database refresh with industry-standard backup practices"""
    
    def __init__(self):
        self.prod_conn = None
        self.dev_conn = None
        self.s3_client = None
        self.backup_bucket = os.getenv('S3_BACKUP_BUCKET', 'project88.bu')
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        
        # Industry standard backup retention (3-2-1 strategy)
        self.retention_policy = {
            'daily': 14,      # 14 daily backups
            'weekly': 8,      # 8 weekly backups (2 months)
            'monthly': 12     # 12 monthly backups (1 year)
        }
        
        # Database connection parameters
        self.prod_db_config = {
            'host': os.getenv('PROD_DB_HOST', 'localhost'),
            'port': os.getenv('PROD_DB_PORT', '5432'),
            'database': os.getenv('PROD_DB_NAME', 'project88_myappdb'),
            'user': os.getenv('PROD_DB_USER', 'project88_myappuser'),
            'password': os.getenv('PROD_DB_PASSWORD')
        }
        
        self.dev_db_config = {
            'host': os.getenv('DEV_DB_HOST', 'localhost'),
            'port': os.getenv('DEV_DB_PORT', '5432'),
            'database': os.getenv('DEV_DB_NAME', 'project88_dev_myappdb'),
            'user': os.getenv('DEV_DB_USER', 'project88_dev_user'),
            'password': os.getenv('DEV_DB_PASSWORD')
        }
        
        # Tables to keep full (structural/configuration data)
        self.full_tables = [
            'timing_partners',
            'users', 
            'providers'
        ]
        
        # Provider event tables with their participant/result relationships
        self.provider_tables = {
            'runsignup': {
                'events': 'runsignup_events',
                'participants': 'runsignup_participants',
                'results': None,
                'event_id_col': 'event_id',
                'date_col': 'start_time'
            },
            'chronotrack': {
                'events': 'ct_events',
                'participants': 'ct_participants', 
                'results': 'ct_results',
                'event_id_col': 'event_id',
                'date_col': 'event_start_time'
            },
            'raceroster': {
                'events': 'raceroster_events',
                'participants': 'raceroster_participants',
                'results': None,
                'event_id_col': 'event_id',
                'date_col': 'start_date'
            },
            'copernico': {
                'events': 'copernico_events',
                'participants': 'copernico_participants',
                'results': 'copernico_results',
                'event_id_col': 'event_id',
                'date_col': 'event_date'
            },
            'haku': {
                'events': 'haku_events',
                'participants': 'haku_participants',
                'results': None,
                'event_id_col': 'event_id',
                'date_col': 'start_date'
            }
        }
        
        # Sync/operational tables (keep last 500 records by date)
        self.operational_tables = {
            'sync_queue': {'date_col': 'created_at', 'limit': 500},
            'sync_history': {'date_col': 'created_at', 'limit': 500}
        }

    def connect_databases(self):
        """Establish connections to production and development databases"""
        try:
            logger.info("Connecting to production database...")
            self.prod_conn = psycopg2.connect(**self.prod_db_config)
            
            logger.info("Connecting to development database...")
            self.dev_conn = psycopg2.connect(**self.dev_db_config)
            
            # Set autocommit for DDL operations
            self.prod_conn.autocommit = True
            self.dev_conn.autocommit = True
            
            logger.info("Database connections established successfully")
            
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def setup_s3_client(self):
        """Initialize S3 client for backup operations"""
        try:
            self.s3_client = boto3.client(
                's3',
                region_name=self.aws_region,
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
            )
            logger.info("S3 client initialized successfully")
            
        except Exception as e:
            logger.error(f"S3 client initialization failed: {e}")
            raise

    def create_production_backup(self) -> str:
        """Create full production database backup before refresh"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"prod_backup_{timestamp}.sql.gz"
        backup_path = f"/tmp/{backup_filename}"
        
        try:
            logger.info("Creating production database backup...")
            
            # Create compressed PostgreSQL dump
            dump_cmd = [
                'pg_dump',
                f"--host={self.prod_db_config['host']}",
                f"--port={self.prod_db_config['port']}",
                f"--username={self.prod_db_config['user']}",
                f"--dbname={self.prod_db_config['database']}",
                '--verbose',
                '--clean',
                '--if-exists',
                '--create'
            ]
            
            # Set PGPASSWORD environment variable
            env = os.environ.copy()
            env['PGPASSWORD'] = self.prod_db_config['password']
            
            # Pipe through gzip for compression
            with open(backup_path, 'wb') as f:
                dump_process = subprocess.Popen(
                    dump_cmd, 
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )
                
                gzip_process = subprocess.Popen(
                    ['gzip', '-c'],
                    stdin=dump_process.stdout,
                    stdout=f,
                    stderr=subprocess.PIPE
                )
                
                dump_process.stdout.close()
                _, gzip_stderr = gzip_process.communicate()
                _, dump_stderr = dump_process.communicate()
                
                if dump_process.returncode != 0:
                    raise Exception(f"pg_dump failed: {dump_stderr.decode()}")
                    
                if gzip_process.returncode != 0:
                    raise Exception(f"gzip failed: {gzip_stderr.decode()}")
            
            logger.info(f"Production backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Production backup failed: {e}")
            raise

    def upload_backup_to_s3(self, backup_path: str):
        """Upload backup to S3 with proper versioning and lifecycle"""
        try:
            timestamp = datetime.now()
            s3_key = f"database-backups/production/{timestamp.strftime('%Y/%m/%d')}/{os.path.basename(backup_path)}"
            
            logger.info(f"Uploading backup to S3: s3://{self.backup_bucket}/{s3_key}")
            
            # Upload with metadata
            self.s3_client.upload_file(
                backup_path,
                self.backup_bucket,
                s3_key,
                ExtraArgs={
                    'Metadata': {
                        'backup-type': 'production-full',
                        'database': 'project88_myappdb',
                        'created-at': timestamp.isoformat(),
                        'retention-policy': 'daily-14-weekly-8-monthly-12'
                    },
                    'StorageClass': 'STANDARD'  # Hot storage for recent backups
                }
            )
            
            # Schedule lifecycle transition after 30 days
            self.setup_s3_lifecycle_policy()
            
            logger.info("Backup uploaded to S3 successfully")
            
        except ClientError as e:
            logger.error(f"S3 upload failed: {e}")
            raise

    def setup_s3_lifecycle_policy(self):
        """Configure S3 lifecycle policy for cost optimization"""
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'Project88-DB-Backup-Lifecycle',
                    'Status': 'Enabled',
                    'Filter': {'Prefix': 'database-backups/'},
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'  # Infrequent access after 30 days
                        },
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER'  # Archive after 90 days
                        },
                        {
                            'Days': 365,
                            'StorageClass': 'DEEP_ARCHIVE'  # Deep archive after 1 year
                        }
                    ],
                    'Expiration': {
                        'Days': 2555  # Delete after 7 years (industry compliance)
                    }
                }
            ]
        }
        
        try:
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.backup_bucket,
                LifecycleConfiguration=lifecycle_config
            )
            logger.info("S3 lifecycle policy configured")
            
        except ClientError as e:
            logger.warning(f"S3 lifecycle policy setup failed: {e}")

    def get_recent_events_by_provider(self, provider: str, limit: int = 500) -> List[str]:
        """Get the most recent event IDs for a specific provider"""
        provider_config = self.provider_tables[provider]
        events_table = provider_config['events']
        event_id_col = provider_config['event_id_col']
        date_col = provider_config['date_col']
        
        query = f"""
        SELECT {event_id_col}
        FROM {events_table}
        WHERE {date_col} IS NOT NULL
        ORDER BY {date_col} DESC
        LIMIT %s
        """
        
        try:
            with self.prod_conn.cursor() as cursor:
                cursor.execute(query, (limit,))
                results = cursor.fetchall()
                return [str(row[0]) for row in results]
                
        except psycopg2.Error as e:
            logger.error(f"Failed to get recent events for {provider}: {e}")
            return []

    def truncate_development_database(self):
        """Safely truncate development database preserving structure"""
        try:
            logger.info("Truncating development database...")
            
            with self.dev_conn.cursor() as cursor:
                # Disable foreign key checks temporarily
                cursor.execute("SET session_replication_role = replica;")
                
                # Get all user tables
                cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename NOT LIKE 'pg_%'
                    AND tablename NOT LIKE 'sql_%'
                """)
                
                tables = [row[0] for row in cursor.fetchall()]
                
                # Truncate all tables except views
                for table in tables:
                    cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                    logger.debug(f"Truncated table: {table}")
                
                # Re-enable foreign key checks
                cursor.execute("SET session_replication_role = DEFAULT;")
                
            self.dev_conn.commit()
            logger.info("Development database truncated successfully")
            
        except psycopg2.Error as e:
            logger.error(f"Failed to truncate development database: {e}")
            self.dev_conn.rollback()
            raise

    def copy_full_tables(self):
        """Copy structural tables completely to development"""
        try:
            logger.info("Copying full tables to development...")
            
            for table in self.full_tables:
                logger.info(f"Copying table: {table}")
                
                # Get column names
                with self.prod_conn.cursor() as prod_cursor:
                    prod_cursor.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = %s 
                        ORDER BY ordinal_position
                    """, (table,))
                    
                    columns = [row[0] for row in prod_cursor.fetchall()]
                    column_list = ', '.join(columns)
                    
                    # Copy data
                    prod_cursor.execute(f"SELECT {column_list} FROM {table}")
                    
                    with self.dev_conn.cursor() as dev_cursor:
                        # Use copy_from for efficient bulk insert
                        copy_sql = f"COPY {table} ({column_list}) FROM STDIN"
                        dev_cursor.copy_expert(copy_sql, prod_cursor)
                
            self.dev_conn.commit()
            logger.info("Full tables copied successfully")
            
        except psycopg2.Error as e:
            logger.error(f"Failed to copy full tables: {e}")
            self.dev_conn.rollback()
            raise

    def copy_trimmed_provider_data(self):
        """Copy last 500 events with all related data for each provider"""
        try:
            logger.info("Copying trimmed provider data...")
            
            for provider, config in self.provider_tables.items():
                logger.info(f"Processing provider: {provider}")
                
                # Get recent event IDs
                recent_events = self.get_recent_events_by_provider(provider, 500)
                
                if not recent_events:
                    logger.warning(f"No events found for provider: {provider}")
                    continue
                
                logger.info(f"Found {len(recent_events)} recent events for {provider}")
                
                # Copy events
                self.copy_provider_table(
                    config['events'], 
                    config['event_id_col'], 
                    recent_events
                )
                
                # Copy participants
                if config['participants']:
                    self.copy_provider_table(
                        config['participants'],
                        config['event_id_col'],
                        recent_events
                    )
                
                # Copy results if exists
                if config['results']:
                    self.copy_provider_table(
                        config['results'],
                        config['event_id_col'],
                        recent_events
                    )
            
            self.dev_conn.commit()
            logger.info("Provider data copied successfully")
            
        except Exception as e:
            logger.error(f"Failed to copy provider data: {e}")
            self.dev_conn.rollback()
            raise

    def copy_provider_table(self, table_name: str, event_id_col: str, event_ids: List[str]):
        """Copy specific provider table data for given event IDs"""
        try:
            if not event_ids:
                return
                
            logger.debug(f"Copying table: {table_name}")
            
            # Create placeholders for IN clause
            placeholders = ','.join(['%s'] * len(event_ids))
            
            with self.prod_conn.cursor() as prod_cursor:
                # Get column names
                prod_cursor.execute(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = %s 
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = [row[0] for row in prod_cursor.fetchall()]
                column_list = ', '.join(columns)
                
                # Copy data for specific events
                query = f"""
                    SELECT {column_list} 
                    FROM {table_name} 
                    WHERE {event_id_col} IN ({placeholders})
                """
                
                prod_cursor.execute(query, event_ids)
                
                with self.dev_conn.cursor() as dev_cursor:
                    # Batch insert
                    rows = prod_cursor.fetchall()
                    if rows:
                        insert_query = f"""
                            INSERT INTO {table_name} ({column_list}) 
                            VALUES ({','.join(['%s'] * len(columns))})
                        """
                        dev_cursor.executemany(insert_query, rows)
                        
                        logger.debug(f"Copied {len(rows)} rows to {table_name}")
            
        except psycopg2.Error as e:
            logger.error(f"Failed to copy table {table_name}: {e}")
            raise

    def copy_operational_tables(self):
        """Copy operational tables with last 500 records"""
        try:
            logger.info("Copying operational tables...")
            
            for table, config in self.operational_tables.items():
                logger.info(f"Copying table: {table}")
                
                date_col = config['date_col']
                limit = config['limit']
                
                with self.prod_conn.cursor() as prod_cursor:
                    # Get column names
                    prod_cursor.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = %s 
                        ORDER BY ordinal_position
                    """, (table,))
                    
                    columns = [row[0] for row in prod_cursor.fetchall()]
                    column_list = ', '.join(columns)
                    
                    # Get recent records
                    query = f"""
                        SELECT {column_list} 
                        FROM {table} 
                        ORDER BY {date_col} DESC 
                        LIMIT %s
                    """
                    
                    prod_cursor.execute(query, (limit,))
                    
                    with self.dev_conn.cursor() as dev_cursor:
                        rows = prod_cursor.fetchall()
                        if rows:
                            insert_query = f"""
                                INSERT INTO {table} ({column_list}) 
                                VALUES ({','.join(['%s'] * len(columns))})
                            """
                            dev_cursor.executemany(insert_query, rows)
                            
                            logger.info(f"Copied {len(rows)} rows to {table}")
            
            self.dev_conn.commit()
            logger.info("Operational tables copied successfully")
            
        except psycopg2.Error as e:
            logger.error(f"Failed to copy operational tables: {e}")
            self.dev_conn.rollback()
            raise

    def update_sequences(self):
        """Update PostgreSQL sequences to match data"""
        try:
            logger.info("Updating database sequences...")
            
            with self.dev_conn.cursor() as cursor:
                # Get all sequences
                cursor.execute("""
                    SELECT schemaname, sequencename 
                    FROM pg_sequences 
                    WHERE schemaname = 'public'
                """)
                
                sequences = cursor.fetchall()
                
                for schema, sequence in sequences:
                    # Find the table and column using this sequence
                    cursor.execute(f"""
                        SELECT pg_get_serial_sequence('{schema}.{sequence.replace('_seq', '')}', 'id')
                    """)
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        table_name = sequence.replace('_seq', '')
                        
                        # Update sequence to max(id) + 1
                        cursor.execute(f"""
                            SELECT setval('{sequence}', 
                                COALESCE((SELECT MAX(id) FROM {table_name}), 1), 
                                COALESCE((SELECT MAX(id) FROM {table_name}), 1) > 0
                            )
                        """)
                        
                        logger.debug(f"Updated sequence: {sequence}")
            
            self.dev_conn.commit()
            logger.info("Database sequences updated successfully")
            
        except psycopg2.Error as e:
            logger.error(f"Failed to update sequences: {e}")
            self.dev_conn.rollback()
            raise

    def generate_refresh_report(self) -> Dict:
        """Generate a report of the refresh operation"""
        try:
            report = {
                'timestamp': datetime.now().isoformat(),
                'status': 'success',
                'tables': {}
            }
            
            with self.dev_conn.cursor() as cursor:
                # Count records in each table
                cursor.execute("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public'
                """)
                
                tables = [row[0] for row in cursor.fetchall()]
                
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    report['tables'][table] = count
            
            logger.info(f"Development database refresh completed successfully")
            logger.info(f"Total tables refreshed: {len(report['tables'])}")
            logger.info(f"Total records: {sum(report['tables'].values())}")
            
            return report
            
        except psycopg2.Error as e:
            logger.error(f"Failed to generate refresh report: {e}")
            return {'status': 'error', 'error': str(e)}

    def cleanup_old_backups(self):
        """Clean up old backups according to retention policy"""
        try:
            logger.info("Cleaning up old backups...")
            
            # List all backup objects
            response = self.s3_client.list_objects_v2(
                Bucket=self.backup_bucket,
                Prefix='database-backups/production/'
            )
            
            if 'Contents' not in response:
                return
            
            # Group backups by age
            now = datetime.now()
            objects_to_delete = []
            
            for obj in response['Contents']:
                obj_date = obj['LastModified'].replace(tzinfo=None)
                age_days = (now - obj_date).days
                
                # Apply retention policy
                should_delete = False
                
                if age_days > self.retention_policy['daily'] and age_days <= 60:
                    # Keep weekly backups
                    if obj_date.weekday() != 0:  # Not Monday
                        should_delete = True
                elif age_days > 60 and age_days <= 365:
                    # Keep monthly backups
                    if obj_date.day != 1:  # Not first of month
                        should_delete = True
                elif age_days > 365:
                    # Delete everything older than 1 year
                    should_delete = True
                
                if should_delete:
                    objects_to_delete.append({'Key': obj['Key']})
            
            # Delete old backups
            if objects_to_delete:
                self.s3_client.delete_objects(
                    Bucket=self.backup_bucket,
                    Delete={'Objects': objects_to_delete}
                )
                logger.info(f"Deleted {len(objects_to_delete)} old backup files")
            
        except ClientError as e:
            logger.error(f"Backup cleanup failed: {e}")

    def run_refresh(self, skip_backup: bool = False):
        """Execute complete database refresh process"""
        try:
            logger.info("Starting development database refresh...")
            start_time = datetime.now()
            
            # Step 1: Connect to databases
            self.connect_databases()
            
            # Step 2: Setup S3 client
            if not skip_backup:
                self.setup_s3_client()
            
            # Step 3: Create production backup
            if not skip_backup:
                backup_path = self.create_production_backup()
                self.upload_backup_to_s3(backup_path)
                
                # Clean up local backup file
                os.remove(backup_path)
                
                # Clean up old backups
                self.cleanup_old_backups()
            
            # Step 4: Truncate development database
            self.truncate_development_database()
            
            # Step 5: Copy full tables
            self.copy_full_tables()
            
            # Step 6: Copy trimmed provider data
            self.copy_trimmed_provider_data()
            
            # Step 7: Copy operational tables
            self.copy_operational_tables()
            
            # Step 8: Update sequences
            self.update_sequences()
            
            # Step 9: Generate report
            report = self.generate_refresh_report()
            
            duration = datetime.now() - start_time
            logger.info(f"Database refresh completed in {duration}")
            
            return report
            
        except Exception as e:
            logger.error(f"Database refresh failed: {e}")
            raise
        finally:
            # Close database connections
            if self.prod_conn:
                self.prod_conn.close()
            if self.dev_conn:
                self.dev_conn.close()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Project88Hub Development Database Refresh')
    parser.add_argument('--skip-backup', action='store_true', 
                       help='Skip backup creation (for testing)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    try:
        refresh_manager = DatabaseRefreshManager()
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            logger.info("Would refresh development database with last 500 events")
            logger.info("Would create production backup and upload to S3")
            logger.info("Would maintain referential integrity across all providers")
            return
        
        report = refresh_manager.run_refresh(skip_backup=args.skip_backup)
        
        if report['status'] == 'success':
            logger.info("✅ Development database refresh completed successfully")
            sys.exit(0)
        else:
            logger.error("❌ Development database refresh failed")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()