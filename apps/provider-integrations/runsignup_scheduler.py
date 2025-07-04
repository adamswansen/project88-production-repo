#!/usr/bin/env python3
"""
RunSignUp Automated Sync Scheduler

This script handles automated incremental syncs for all RunSignUp timing partners:
- Daily incremental syncs for recent data
- Smart sync intervals based on event dates
- Automatic error recovery and retry logic
- Comprehensive monitoring and alerting
- Safe concurrent execution prevention
"""

import sys
import os
import psycopg2
import psycopg2.extras
import json
import logging
import time
import fcntl
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import schedule
import signal

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.runsignup_adapter import RunSignUpAdapter
from notifications import notify_incremental_success, notify_error, get_notification_status

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'runsignup_sync_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RunSignUpScheduler:
    """Automated RunSignUp sync scheduler"""
    
    def __init__(self):
        # PostgreSQL connection using environment variables
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'project88_myappdb'),
            'user': os.getenv('DB_USER', 'project88_myappuser'),
            'password': os.getenv('DB_PASSWORD', 'puctuq-cefwyq-3boqRe'),
            'port': int(os.getenv('DB_PORT', '5432'))
        }
        
        # Sync configuration
        self.sync_config = {
            'daily_sync_hour': int(os.getenv('SYNC_HOUR', '2')),  # 2 AM default
            'incremental_lookback_hours': int(os.getenv('LOOKBACK_HOURS', '72')),  # 3 days
            'future_events_lookback_days': int(os.getenv('FUTURE_LOOKBACK_DAYS', '7')),  # 1 week
            'retry_attempts': int(os.getenv('RETRY_ATTEMPTS', '3')),
            'retry_delay_minutes': int(os.getenv('RETRY_DELAY', '5')),
            'rate_limit_delay': int(os.getenv('RATE_LIMIT_DELAY', '2')),  # seconds between partners
            'concurrent_prevention_file': '/tmp/runsignup_sync.lock'
        }
        
        self.stats = {
            'sync_start_time': datetime.now(),
            'timing_partners_processed': 0,
            'events_synced': 0,
            'participants_synced': 0,
            'errors': 0,
            'retries': 0
        }
        
    def get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(**self.db_config)
    
    def prevent_concurrent_execution(self):
        """Prevent multiple instances from running simultaneously"""
        try:
            self.lock_file = open(self.sync_config['concurrent_prevention_file'], 'w')
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_file.write(f"{os.getpid()}\n{datetime.now()}\n")
            self.lock_file.flush()
            logger.info("🔒 Acquired sync lock")
            return True
        except IOError:
            logger.warning("⚠️  Another sync process is already running")
            return False
    
    def release_lock(self):
        """Release the concurrent execution lock"""
        try:
            if hasattr(self, 'lock_file'):
                fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
                self.lock_file.close()
                os.remove(self.sync_config['concurrent_prevention_file'])
                logger.info("🔓 Released sync lock")
        except:
            pass
    
    def get_active_timing_partners(self) -> List[Tuple[int, str, str]]:
        """Get timing partners with RunSignUp credentials that need syncing"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get partners with recent or upcoming events
        query = """
            SELECT DISTINCT 
                ppc.timing_partner_id, 
                ppc.principal, 
                ppc.secret,
                tp.company_name
            FROM partner_provider_credentials ppc
            JOIN timing_partners tp ON ppc.timing_partner_id = tp.timing_partner_id
            LEFT JOIN runsignup_events re ON ppc.timing_partner_id = re.timing_partner_id
            WHERE ppc.provider_id = 2 
            AND (
                re.start_time > NOW() - INTERVAL '%s days'
                OR re.start_time IS NULL  -- Include new partners
            )
            ORDER BY ppc.timing_partner_id
        """
        
        cursor.execute(query, (self.sync_config['future_events_lookback_days'],))
        partners = cursor.fetchall()
        conn.close()
        
        logger.info(f"🎯 Found {len(partners)} active timing partners for sync")
        return partners
    
    def get_last_sync_time(self, timing_partner_id: int) -> Optional[datetime]:
        """Get the last successful sync time for a timing partner"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check sync_history table first
        cursor.execute("""
            SELECT MAX(sync_time) FROM sync_history 
            WHERE timing_partner_id = %s 
            AND provider_id = 2 
            AND status = 'completed'
        """, (timing_partner_id,))
        
        result = cursor.fetchone()
        last_sync = result[0] if result and result[0] else None
        
        # Fallback to participants table fetched_date
        if not last_sync:
            cursor.execute("""
                SELECT MAX(fetched_date) FROM runsignup_participants 
                WHERE timing_partner_id = %s
            """, (timing_partner_id,))
            
            result = cursor.fetchone()
            last_sync = result[0] if result and result[0] else None
        
        conn.close()
        return last_sync
    
    def record_sync_attempt(self, timing_partner_id: int, status: str, reason: str = None, 
                           events_processed: int = 0, participants_processed: int = 0):
        """Record sync attempt in sync_history table"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sync_history (
                    timing_partner_id, provider_id, sync_time, status, reason,
                    num_of_synced_records, entries_success, entries_failed, duration_seconds
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                timing_partner_id,
                2,  # Provider ID for RunSignUp
                datetime.now(),
                status,
                reason,
                events_processed + participants_processed,
                events_processed + participants_processed if status == 'completed' else 0,
                1 if status == 'failed' else 0,
                0  # duration_seconds - we'll calculate this later if needed
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record sync history: {e}")
    
    def sync_timing_partner(self, timing_partner_id: int, principal: str, secret: str, 
                           company_name: str) -> Dict:
        """Perform incremental sync for a specific timing partner"""
        
        logger.info(f"\n🔄 Syncing timing partner {timing_partner_id} ({company_name})")
        
        partner_stats = {
            'timing_partner_id': timing_partner_id,
            'company_name': company_name,
            'events_synced': 0,
            'participants_synced': 0,
            'errors': [],
            'status': 'started',
            'start_time': datetime.now()
        }
        
        try:
            # Get last sync time
            last_sync = self.get_last_sync_time(timing_partner_id)
            
            # Calculate incremental sync start time
            if last_sync:
                # Sync from last sync minus buffer for safety
                sync_since = last_sync - timedelta(hours=self.sync_config['incremental_lookback_hours'])
                logger.info(f"📅 Incremental sync since: {sync_since} (last sync: {last_sync})")
            else:
                # First sync - get recent data only
                sync_since = datetime.now() - timedelta(days=self.sync_config['future_events_lookback_days'])
                logger.info(f"📅 Initial sync since: {sync_since} (first time sync)")
            
            # Create adapter
            credentials_dict = {'principal': principal, 'secret': secret}
            adapter = RunSignUpAdapter(credentials_dict, timing_partner_id)
            
            # Test authentication
            if not adapter.authenticate():
                raise Exception(f"Authentication failed")
            
            logger.info(f"✅ Authentication successful")
            
            # Get events with incremental filter
            logger.info("📥 Fetching updated events...")
            provider_events = adapter.get_events(last_modified_since=sync_since)
            
            if not provider_events:
                logger.info("ℹ️  No updated events found")
                partner_stats['status'] = 'completed_no_updates'
                self.record_sync_attempt(timing_partner_id, 'completed', 'No updates found')
                return partner_stats
            
            logger.info(f"📅 Found {len(provider_events)} updated events")
            
            # Get database connection
            conn = self.get_connection()
            
            # Process events
            events_processed = 0
            participants_processed = 0
            
            for event in provider_events:
                try:
                    # Extract race_id and event_id from event's raw_data
                    race_data = event.raw_data.get('race', {})
                    event_data = event.raw_data.get('event', {})
                    race_id = race_data.get('race_id')
                    event_id = event_data.get('event_id')
                    
                    if not race_id or not event_id:
                        logger.warning(f"Missing race_id or event_id for event {event.provider_event_id}, skipping")
                        continue
                    
                    # Store/update event
                    stored_event_id = adapter.store_event(event.to_dict(), race_id, conn)
                    if stored_event_id:
                        events_processed += 1
                    
                    # Get participants with incremental filter
                    participants = adapter.get_participants(
                        race_id, 
                        str(event_id), 
                        last_modified_since=sync_since
                    )
                    
                    if participants:
                        logger.info(f"👥 Found {len(participants)} updated participants for event {event.event_id}")
                        
                        # Store participants
                        for participant in participants:
                            try:
                                adapter.store_participant(participant.to_dict(), race_id, str(event_id), conn)
                                participants_processed += 1
                            except Exception as e:
                                logger.error(f"❌ Error storing participant: {e}")
                                partner_stats['errors'].append(f"Participant error: {e}")
                                self.stats['errors'] += 1
                    
                except Exception as e:
                    logger.error(f"❌ Error processing event {event.event_id}: {e}")
                    partner_stats['errors'].append(f"Event {event.event_id} error: {e}")
                    self.stats['errors'] += 1
                    continue
            
            # Commit changes
            conn.commit()
            conn.close()
            
            # Update stats
            partner_stats['events_synced'] = events_processed
            partner_stats['participants_synced'] = participants_processed
            partner_stats['status'] = 'completed'
            partner_stats['duration'] = (datetime.now() - partner_stats['start_time']).total_seconds()
            
            logger.info(f"✅ Sync complete - Events: {events_processed}, Participants: {participants_processed}")
            
            # Record successful sync
            self.record_sync_attempt(
                timing_partner_id, 
                'completed', 
                f"Events: {events_processed}, Participants: {participants_processed}",
                events_processed,
                participants_processed
            )
            
            return partner_stats
            
        except Exception as e:
            logger.error(f"❌ Error syncing timing partner {timing_partner_id}: {e}")
            partner_stats['errors'].append(f"Fatal error: {e}")
            partner_stats['status'] = 'failed'
            self.stats['errors'] += 1
            
            # Record failed sync
            self.record_sync_attempt(timing_partner_id, 'failed', str(e))
            
            return partner_stats
    
    def run_scheduled_sync(self) -> Dict:
        """Run the scheduled incremental sync for all timing partners"""
        
        logger.info("🚀 Starting RunSignUp Scheduled Sync")
        logger.info("=" * 80)
        
        # Prevent concurrent execution
        if not self.prevent_concurrent_execution():
            return {'error': 'Another sync process is running'}
        
        try:
            # Get active timing partners
            partners = self.get_active_timing_partners()
            
            if not partners:
                logger.info("ℹ️  No active timing partners found")
                return {'stats': self.stats, 'partner_results': []}
            
            # Process each timing partner
            partner_results = []
            
            for timing_partner_id, principal, secret, company_name in partners:
                self.stats['timing_partners_processed'] += 1
                
                # Retry logic
                retry_count = 0
                result = None
                
                while retry_count <= self.sync_config['retry_attempts']:
                    try:
                        result = self.sync_timing_partner(timing_partner_id, principal, secret, company_name)
                        
                        if result['status'] in ['completed', 'completed_no_updates']:
                            break  # Success
                        
                    except Exception as e:
                        logger.error(f"❌ Retry {retry_count + 1}/{self.sync_config['retry_attempts']} failed for partner {timing_partner_id}: {e}")
                        retry_count += 1
                        self.stats['retries'] += 1
                        
                        if retry_count <= self.sync_config['retry_attempts']:
                            time.sleep(self.sync_config['retry_delay_minutes'] * 60)
                
                if result:
                    partner_results.append(result)
                    
                    # Update global stats
                    self.stats['events_synced'] += result.get('events_synced', 0)
                    self.stats['participants_synced'] += result.get('participants_synced', 0)
                
                # Rate limiting between partners
                time.sleep(self.sync_config['rate_limit_delay'])
            
            # Calculate final statistics
            self.stats['duration'] = (datetime.now() - self.stats['sync_start_time']).total_seconds()
            
            # Generate summary report
            self.generate_sync_report(partner_results)
            
            # Send notifications
            try:
                total_events_synced = self.stats.get('events_synced', 0)
                total_participants_synced = self.stats.get('participants_synced', 0)
                
                if self.stats.get('errors', 0) == 0 and (total_events_synced > 0 or total_participants_synced > 0):
                    # Send incremental success notification (first time only)
                    notify_incremental_success(total_events_synced, total_participants_synced)
                    logger.info("📱 Incremental sync success notification sent")
                elif self.stats.get('errors', 0) > 0:
                    # Send error notification
                    notify_error("Incremental Sync Errors", 
                               f"Incremental sync completed with {self.stats['errors']} errors",
                               f"Events: {total_events_synced}, Participants: {total_participants_synced}")
                    logger.info("📱 Error notification sent")
                    
            except Exception as notification_error:
                logger.error(f"Failed to send notification: {notification_error}")
            
            return {
                'stats': self.stats,
                'partner_results': partner_results
            }
            
        finally:
            self.release_lock()
    
    def generate_sync_report(self, partner_results: List[Dict]):
        """Generate sync summary report"""
        
        logger.info("\n" + "=" * 80)
        logger.info("🎉 RUNSIGNUP SCHEDULED SYNC COMPLETE!")
        logger.info("=" * 80)
        
        logger.info(f"⏱️  Duration: {self.stats['duration']:.1f} seconds")
        logger.info(f"🏢 Timing Partners: {self.stats['timing_partners_processed']}")
        logger.info(f"📅 Events Synced: {self.stats['events_synced']}")
        logger.info(f"👥 Participants Synced: {self.stats['participants_synced']}")
        
        if self.stats['errors'] > 0:
            logger.warning(f"⚠️  Errors: {self.stats['errors']}")
        
        if self.stats['retries'] > 0:
            logger.info(f"🔄 Retries: {self.stats['retries']}")
        
        # Count statuses
        status_counts = {}
        for result in partner_results:
            status = result.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info(f"\n📊 Status Summary:")
        for status, count in status_counts.items():
            logger.info(f"   • {status}: {count}")
        
        # Save summary report
        report_file = f"sync_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'sync_time': str(datetime.now()),
                'stats': self.stats,
                'partner_results': partner_results,
                'config': self.sync_config
            }, f, indent=2, default=str)
        
        logger.info(f"📄 Detailed report saved: {report_file}")

def create_cron_job():
    """Helper function to create cron job for scheduled syncs"""
    cron_command = f"0 2 * * * cd {os.getcwd()} && /usr/bin/python3 runsignup_scheduler.py >> /var/log/runsignup_sync.log 2>&1"
    
    print("📅 To set up automated daily syncs at 2 AM, add this cron job:")
    print("")
    print("Run: crontab -e")
    print("Add this line:")
    print(cron_command)
    print("")
    print("Or run this command:")
    print(f"echo '{cron_command}' | crontab -")

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RunSignUp Automated Sync Scheduler')
    parser.add_argument('--setup-cron', action='store_true', help='Show cron setup instructions')
    parser.add_argument('--test', action='store_true', help='Test sync for first timing partner only')
    
    args = parser.parse_args()
    
    if args.setup_cron:
        create_cron_job()
        return 0
    
    # Create scheduler instance
    scheduler = RunSignUpScheduler()
    
    # Override config for testing
    if args.test:
        logger.info("🧪 TEST MODE - Processing first timing partner only")
        # Limit to first partner for testing
        original_method = scheduler.get_active_timing_partners
        def test_get_partners():
            partners = original_method()
            return partners[:1] if partners else []
        scheduler.get_active_timing_partners = test_get_partners
    
    # Run sync
    try:
        results = scheduler.run_scheduled_sync()
        
        if 'error' in results:
            logger.error(f"❌ Sync failed: {results['error']}")
            return 1
        
        if results['stats']['errors'] == 0:
            logger.info("🎉 Sync completed successfully!")
            return 0
        else:
            logger.warning(f"⚠️  Sync completed with {results['stats']['errors']} errors")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⏸️  Sync interrupted by user")
        return 130
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 