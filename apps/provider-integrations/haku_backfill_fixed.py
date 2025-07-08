#!/usr/bin/env python3
"""
Haku Fast Backfill - FIXED VERSION with Better Error Handling

Enhanced version that handles database errors properly by:
1. Rolling back transactions immediately on error
2. Creating new connections after failed transactions
3. Better error logging and recovery
4. Preventing transaction abort lock-ups
"""

import sys
import os
import psycopg2
import psycopg2.extras
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.haku_adapter import HakuAdapter

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'haku_backfill_fixed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class HakuFixedBackfill:
    """
    Fixed version of Haku backfill with proper error handling and transaction management
    """
    
    def __init__(self, dry_run: bool = False, skip_large_events: bool = True):
        # PostgreSQL connection using environment variables with fallback defaults
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'project88_myappdb'),
            'user': os.getenv('DB_USER', 'project88_myappuser'),
            'password': os.getenv('DB_PASSWORD', 'puctuq-cefwyq-3boqRe'),
            'port': int(os.getenv('DB_PORT', '5432'))
        }
        
        self.dry_run = dry_run
        self.skip_large_events = skip_large_events
        self.large_event_threshold = 100  # Events with >100 participants are "large"
        self.api_rate_limit = 1.5  # Reduced from 3 to 1.5 seconds due to larger page sizes
        
        # Statistics tracking
        self.stats = {
            'start_time': datetime.now(),
            'timing_partners_processed': 0,
            'events_processed': 0,
            'events_skipped_large': 0,
            'participants_processed': 0,
            'participants_inserted': 0,
            'database_errors': 0,
            'api_errors': 0,
            'total_errors': 0,
            'api_calls_made': 0
        }
        
        # Deferred large events
        self.deferred_large_events = []
        
        # Load existing checkpoint
        self.checkpoint = self.load_checkpoint()
    
    def get_connection(self):
        """Get fresh PostgreSQL database connection"""
        return psycopg2.connect(**self.db_config)
    
    def safe_database_operation(self, operation_func, *args, **kwargs):
        """
        Safely execute a database operation with proper error handling
        Returns (success: bool, result: any, error: str)
        """
        conn = None
        try:
            conn = self.get_connection()
            conn.autocommit = False  # Use transactions
            result = operation_func(conn, *args, **kwargs)
            conn.commit()
            return True, result, None
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Database operation failed: {error_msg}")
            if conn:
                try:
                    conn.rollback()
                    logger.info("🔄 Transaction rolled back successfully")
                except Exception as rollback_error:
                    logger.error(f"❌ Rollback failed: {rollback_error}")
            self.stats['database_errors'] += 1
            self.stats['total_errors'] += 1
            return False, None, error_msg
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
    
    def store_participants_batch(self, conn, participants: List, event_id: str, timing_partner_id: int, principal: str):
        """Store a batch of participants in a single transaction"""
        cursor = conn.cursor()
        inserted_count = 0
        
        for participant in participants:
            try:
                # Insert participant data with proper error handling
                cursor.execute("""
                    INSERT INTO haku_participants (
                        event_id, participant_id, bib_number, first_name, last_name,
                        email, gender, registration_date, fetched_date,
                        credentials_used, timing_partner_id, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, NOW())
                    ON CONFLICT (event_id, participant_id, timing_partner_id) DO UPDATE SET
                        bib_number = EXCLUDED.bib_number,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        email = EXCLUDED.email,
                        gender = EXCLUDED.gender,
                        registration_date = EXCLUDED.registration_date,
                        fetched_date = NOW()
                """, (
                    event_id,
                    participant.provider_participant_id,
                    participant.bib_number,
                    participant.first_name,
                    participant.last_name,
                    participant.email,
                    participant.gender,
                    participant.registration_date,
                    principal[:10] + "...",
                    timing_partner_id
                ))
                
                inserted_count += 1
                
            except Exception as e:
                # Log individual participant error but continue with batch
                logger.warning(f"⚠️  Failed to insert participant {participant.provider_participant_id}: {e}")
                # Don't break the entire batch for one bad participant
                continue
        
        return inserted_count
    
    def get_haku_credentials(self) -> List[Tuple[int, str, str, int]]:
        """Get Haku timing partner credentials"""
        def get_credentials_op(conn):
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    tp.timing_partner_id, 
                    ppc.principal, 
                    ppc.secret,
                    ppc.partner_provider_credential_id
                FROM timing_partners tp
                JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
                WHERE ppc.provider_id = (SELECT provider_id FROM providers WHERE name = 'Haku')
                ORDER BY tp.timing_partner_id
            """)
            return cursor.fetchall()
        
        success, credentials, error = self.safe_database_operation(get_credentials_op)
        if success:
            logger.info(f"📡 Found {len(credentials)} Haku timing partners")
            return credentials
        else:
            logger.error(f"❌ Failed to get Haku credentials: {error}")
            return []
    
    def get_events_for_partner(self, timing_partner_id: int, principal: str, secret: str) -> List[Tuple[str, str, datetime]]:
        """Get events for a timing partner from Haku API"""
        try:
            # Create adapter with credentials
            credentials = {
                'principal': principal,
                'secret': secret,
                'additional_config': {'organization_name': 'Unknown'}  # Will be updated from API
            }
            
            adapter = HakuAdapter(credentials, timing_partner_id)
            events = adapter.get_events()
            self.stats['api_calls_made'] += 1
            
            # Convert to our format
            event_list = []
            for event in events:
                event_list.append((
                    event.provider_event_id,
                    event.event_name,
                    event.event_date
                ))
            
            return event_list
            
        except Exception as e:
            logger.error(f"❌ Failed to get events for partner {timing_partner_id}: {e}")
            self.stats['api_errors'] += 1
            self.stats['total_errors'] += 1
            return []
    
    def process_single_event(self, event_id: str, event_name: str, timing_partner_id: int, principal: str, secret: str) -> Dict:
        """Process a single event with proper error handling"""
        event_stats = {
            'event_id': event_id,
            'event_name': event_name,
            'participants_processed': 0,
            'participants_inserted': 0,
            'success': False,
            'error': None
        }
        
        try:
            # Create adapter
            credentials = {
                'principal': principal,
                'secret': secret,
                'additional_config': {'organization_name': 'Unknown'}
            }
            
            adapter = HakuAdapter(credentials, timing_partner_id)
            
            # Get participants for this event
            logger.info(f"👥 Fetching participants for event: {event_name}")
            participants = adapter.get_participants(event_id)
            self.stats['api_calls_made'] += 1
            
            if not participants:
                logger.info(f"📭 No participants found for event {event_name}")
                event_stats['success'] = True
                return event_stats
            
            logger.info(f"👥 Found {len(participants)} participants for event {event_name}")
            event_stats['participants_processed'] = len(participants)
            
            # Check if this is a large event and we're skipping them
            if self.skip_large_events and len(participants) > self.large_event_threshold:
                logger.info(f"⏩ Deferring large event {event_name} ({len(participants)} participants)")
                self.deferred_large_events.append({
                    'event_id': event_id,
                    'event_name': event_name,
                    'timing_partner_id': timing_partner_id,
                    'estimated_size': len(participants)
                })
                self.stats['events_skipped_large'] += 1
                event_stats['success'] = True
                return event_stats
            
            if not self.dry_run:
                # Store participants using safe database operation
                success, inserted_count, error = self.safe_database_operation(
                    self.store_participants_batch,
                    participants, event_id, timing_partner_id, principal
                )
                
                if success:
                    event_stats['participants_inserted'] = inserted_count
                    event_stats['success'] = True
                    logger.info(f"✅ Successfully stored {inserted_count} participants for event {event_name}")
                    self.stats['participants_inserted'] += inserted_count
                else:
                    event_stats['error'] = error
                    logger.error(f"❌ Failed to store participants for event {event_name}: {error}")
            else:
                # Dry run mode
                event_stats['participants_inserted'] = len(participants)
                event_stats['success'] = True
                logger.info(f"🧪 DRY RUN: Would store {len(participants)} participants for event {event_name}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Error processing event {event_name}: {error_msg}")
            event_stats['error'] = error_msg
            self.stats['api_errors'] += 1
            self.stats['total_errors'] += 1
        
        return event_stats
    
    def process_timing_partner(self, timing_partner_id: int, principal: str, secret: str) -> Dict:
        """Process all events for a timing partner"""
        partner_stats = {
            'timing_partner_id': timing_partner_id,
            'start_time': datetime.now(),
            'events_processed': 0,
            'events_skipped': 0,
            'participants_inserted': 0,
            'errors': [],
            'success': False
        }
        
        try:
            logger.info(f"\n🚀 Processing timing partner {timing_partner_id}")
            
            # Get events for this partner
            events = self.get_events_for_partner(timing_partner_id, principal, secret)
            
            if not events:
                logger.warning(f"📭 No events found for timing partner {timing_partner_id}")
                partner_stats['success'] = True
                return partner_stats
            
            logger.info(f"📅 Found {len(events)} events for timing partner {timing_partner_id}")
            
            # Process each event
            for event_id, event_name, event_date in events:
                logger.info(f"🎯 Processing event: {event_name} ({event_id})")
                
                event_result = self.process_single_event(
                    event_id, event_name, timing_partner_id, principal, secret
                )
                
                if event_result['success']:
                    partner_stats['events_processed'] += 1
                    partner_stats['participants_inserted'] += event_result['participants_inserted']
                    self.stats['events_processed'] += 1
                    self.stats['participants_processed'] += event_result['participants_processed']
                else:
                    partner_stats['events_skipped'] += 1
                    if event_result['error']:
                        partner_stats['errors'].append(f"Event {event_name}: {event_result['error']}")
                
                # Rate limiting between events
                logger.debug(f"⏳ Rate limiting - sleeping {self.api_rate_limit} seconds")
                time.sleep(self.api_rate_limit)
            
            partner_stats['success'] = True
            partner_stats['duration'] = (datetime.now() - partner_stats['start_time']).total_seconds()
            
            logger.info(f"✅ Completed timing partner {timing_partner_id}")
            logger.info(f"📊 Events: {partner_stats['events_processed']}, Participants: {partner_stats['participants_inserted']}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Fatal error processing timing partner {timing_partner_id}: {error_msg}")
            partner_stats['errors'].append(f"Fatal error: {error_msg}")
            self.stats['total_errors'] += 1
        
        return partner_stats
    
    def load_checkpoint(self):
        """Load checkpoint file if it exists"""
        try:
            with open('haku_backfill_checkpoint.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'completed_partners': [],
                'processed_events': [],
                'last_updated': None
            }
        except Exception as e:
            logger.warning(f"⚠️  Failed to load checkpoint: {e}")
            return {
                'completed_partners': [],
                'processed_events': [],
                'last_updated': None
            }
    
    def save_checkpoint(self, timing_partner_id: int = None, completed: bool = False):
        """Save checkpoint to resume processing"""
        try:
            if timing_partner_id and completed:
                if timing_partner_id not in self.checkpoint['completed_partners']:
                    self.checkpoint['completed_partners'].append(timing_partner_id)
            
            self.checkpoint['last_updated'] = datetime.now().isoformat()
            
            with open('haku_backfill_checkpoint.json', 'w') as f:
                json.dump(self.checkpoint, f, indent=2)
                
        except Exception as e:
            logger.warning(f"⚠️  Failed to save checkpoint: {e}")
    
    def find_smallest_event(self) -> Tuple[str, str, int, str, str]:
        """Find the smallest event across all timing partners for testing"""
        logger.info("🔍 Finding smallest event for testing...")
        
        credentials = self.get_haku_credentials()
        if not credentials:
            return None
        
        smallest_event = None
        smallest_size = float('inf')
        
        for timing_partner_id, principal, secret, credential_id in credentials:
            try:
                logger.info(f"🔍 Checking events for partner {timing_partner_id}")
                events = self.get_events_for_partner(timing_partner_id, principal, secret)
                
                for event_id, event_name, event_date in events[:3]:  # Only check first 3 events per partner
                    try:
                        # Create adapter
                        credentials_dict = {
                            'principal': principal,
                            'secret': secret,
                            'additional_config': {'organization_name': 'Unknown'}
                        }
                        
                        adapter = HakuAdapter(credentials_dict, timing_partner_id)
                        participants = adapter.get_participants(event_id)
                        self.stats['api_calls_made'] += 1
                        
                        participant_count = len(participants) if participants else 0
                        logger.info(f"   Event {event_name}: {participant_count} participants")
                        
                        if participant_count > 0 and participant_count < smallest_size:
                            smallest_size = participant_count
                            smallest_event = (event_id, event_name, timing_partner_id, principal, secret)
                        
                        time.sleep(self.api_rate_limit)  # Rate limiting
                        
                    except Exception as e:
                        logger.warning(f"⚠️  Error checking event {event_name}: {e}")
                        continue
                
            except Exception as e:
                logger.warning(f"⚠️  Error checking partner {timing_partner_id}: {e}")
                continue
        
        if smallest_event:
            event_id, event_name, timing_partner_id, principal, secret = smallest_event
            logger.info(f"🎯 Smallest event found: {event_name} (Partner {timing_partner_id}) with {smallest_size} participants")
            return smallest_event
        else:
            logger.error("❌ No suitable test event found")
            return None
    
    def test_single_event(self) -> bool:
        """Test processing with the smallest available event"""
        logger.info("🧪 Running single event test...")
        
        smallest_event = self.find_smallest_event()
        if not smallest_event:
            return False
        
        event_id, event_name, timing_partner_id, principal, secret = smallest_event
        
        logger.info(f"🎯 Testing with event: {event_name} (Partner {timing_partner_id})")
        
        result = self.process_single_event(event_id, event_name, timing_partner_id, principal, secret)
        
        if result['success']:
            logger.info(f"✅ Test successful! Inserted {result['participants_inserted']} participants")
            return True
        else:
            logger.error(f"❌ Test failed: {result['error']}")
            return False
    
    def run_full_backfill(self, partner_limit: int = None) -> Dict:
        """Run full backfill for all timing partners"""
        logger.info("🚀 Starting Haku Fixed Backfill")
        logger.info("=" * 80)
        
        if self.dry_run:
            logger.info("🧪 DRY RUN MODE - No data will be written")
        
        if self.skip_large_events:
            logger.info(f"⏩ Fast mode: Events with >{self.large_event_threshold} participants will be deferred")
        
        # Get credentials
        credentials = self.get_haku_credentials()
        
        if partner_limit:
            credentials = credentials[:partner_limit]
            logger.info(f"🔬 Limited to first {partner_limit} timing partners")
        
        # Filter out already completed partners
        remaining_credentials = [
            (tp_id, principal, secret, cred_id) for tp_id, principal, secret, cred_id in credentials
            if tp_id not in self.checkpoint['completed_partners']
        ]
        
        if len(remaining_credentials) < len(credentials):
            skipped = len(credentials) - len(remaining_credentials)
            logger.info(f"📂 Resuming: Skipping {skipped} already completed partners")
        
        # Process each timing partner
        partner_results = []
        
        for timing_partner_id, principal, secret, credential_id in remaining_credentials:
            self.stats['timing_partners_processed'] += 1
            
            result = self.process_timing_partner(timing_partner_id, principal, secret)
            partner_results.append(result)
            
            if result['success']:
                self.save_checkpoint(timing_partner_id, completed=True)
            
            # Rate limiting between partners
            if timing_partner_id != remaining_credentials[-1][0]:
                time.sleep(5)  # Longer pause between partners
        
        # Calculate final statistics
        self.stats['duration'] = (datetime.now() - self.stats['start_time']).total_seconds()
        
        # Generate final report
        self.generate_report(partner_results)
        
        return {
            'stats': self.stats,
            'partner_results': partner_results,
            'deferred_large_events': self.deferred_large_events
        }
    
    def generate_report(self, partner_results: List[Dict]):
        """Generate comprehensive final report"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 HAKU FIXED BACKFILL FINAL REPORT")
        logger.info("=" * 80)
        
        # Summary statistics
        total_duration = self.stats['duration']
        logger.info(f"⏱️  Total Duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        logger.info(f"📡 API Calls Made: {self.stats['api_calls_made']}")
        logger.info(f"📈 Events Processed: {self.stats['events_processed']}")
        logger.info(f"⏩ Events Deferred (Large): {self.stats['events_skipped_large']}")
        logger.info(f"👥 Participants Processed: {self.stats['participants_processed']}")
        logger.info(f"✅ Participants Inserted: {self.stats['participants_inserted']}")
        logger.info(f"🗄️  Database Errors: {self.stats['database_errors']}")
        logger.info(f"📡 API Errors: {self.stats['api_errors']}")
        logger.info(f"❌ Total Errors: {self.stats['total_errors']}")
        
        # Success rate
        if self.stats['participants_processed'] > 0:
            success_rate = (self.stats['participants_inserted'] / self.stats['participants_processed']) * 100
            logger.info(f"🎯 Success Rate: {success_rate:.1f}%")
        
        # Partner breakdown
        logger.info("\n📍 Partner Breakdown:")
        for result in partner_results:
            timing_partner_id = result['timing_partner_id']
            events = result.get('events_processed', 0)
            participants = result.get('participants_inserted', 0)
            errors = len(result.get('errors', []))
            status = "✅" if result.get('success') else "❌"
            
            logger.info(f"   {status} Partner {timing_partner_id}: {events} events, {participants} participants, {errors} errors")
        
        # Recommendations
        logger.info("\n🎯 Recommendations:")
        if self.stats['total_errors'] == 0:
            logger.info("   ✅ Backfill completed successfully with no errors!")
        elif self.stats['database_errors'] == 0:
            logger.info("   ✅ No database errors - API issues only")
        else:
            logger.info(f"   ⚠️  {self.stats['database_errors']} database errors occurred")
        
        if self.deferred_large_events:
            logger.info(f"   🔄 {len(self.deferred_large_events)} large events deferred")
            logger.info("   💡 Run with --process-large to handle deferred events")
        
        logger.info("\n🚀 Next Steps:")
        logger.info("   1. Verify data in database")
        logger.info("   2. Start event-driven scheduler if successful")
        if self.deferred_large_events:
            logger.info("   3. Process large events when ready")
        
        logger.info("=" * 80)

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Haku Fixed Backfill with Better Error Handling')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no data written)')
    parser.add_argument('--limit', type=int, help='Limit number of timing partners (for testing)')
    parser.add_argument('--test-single', action='store_true', help='Test with smallest available event')
    parser.add_argument('--process-large', action='store_true', help='Process large events (no size limit)')
    
    args = parser.parse_args()
    
    # Create backfill instance
    skip_large = not args.process_large
    backfill = HakuFixedBackfill(dry_run=args.dry_run, skip_large_events=skip_large)
    
    if args.test_single:
        logger.info("🧪 Running single event test mode")
        success = backfill.test_single_event()
        if success:
            logger.info("✅ Test passed! Database schema and connectivity working properly")
        else:
            logger.error("❌ Test failed! Check logs for issues")
    else:
        logger.info("🚀 Running full backfill")
        result = backfill.run_full_backfill(partner_limit=args.limit)
        
        if result['stats']['total_errors'] == 0:
            logger.info("🎉 Backfill completed successfully!")
        else:
            logger.warning(f"⚠️  Backfill completed with {result['stats']['total_errors']} errors")

if __name__ == "__main__":
    main() 