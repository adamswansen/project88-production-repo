#!/usr/bin/env python3
"""
Haku Complete Backfill Script

This script safely backfills ALL Haku data for all timing partners:
- Respects existing data (no duplicates)
- Progressive backfill with checkpoints
- Detailed logging and progress tracking
- Safe to run multiple times
- Production-ready error handling
- Respects Haku API rate limits (500 calls/hour)
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

# Optional imports for notifications
try:
    from notifications import notify_backfill_success, notify_error, get_notification_status
except ImportError:
    # Fallback if notifications module is not available
    def notify_backfill_success(*args, **kwargs):
        pass
    def notify_error(*args, **kwargs):
        pass
    def get_notification_status(*args, **kwargs):
        return True

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'haku_backfill_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class HakuBackfill:
    """Comprehensive Haku backfill system"""
    
    def __init__(self, dry_run: bool = False):
        # PostgreSQL connection using environment variables with fallback defaults
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'project88_myappdb'),
            'user': os.getenv('DB_USER', 'project88_myappuser'),
            'password': os.getenv('DB_PASSWORD', 'puctuq-cefwyq-3boqRe'),
            'port': int(os.getenv('DB_PORT', '5432'))
        }
        
        self.dry_run = dry_run
        self.stats = {
            'timing_partners_processed': 0,
            'events_processed': 0,
            'participants_processed': 0,
            'events_updated': 0,
            'participants_inserted': 0,
            'participants_updated': 0,
            'errors': 0,
            'start_time': datetime.now(),
            'api_calls_made': 0
        }
        
        # Progress checkpoints for resumability
        self.checkpoint_file = 'haku_backfill_checkpoint.json'
        self.load_checkpoint()
        
        # Rate limiting for Haku API (500 calls/hour = 1 call per 7.2 seconds)
        self.api_rate_limit = 8  # Conservative 8 seconds between calls
        
    def get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(**self.db_config)
    
    def load_checkpoint(self):
        """Load progress checkpoint"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r') as f:
                    self.checkpoint = json.load(f)
                logger.info(f"📂 Loaded checkpoint from {self.checkpoint_file}")
            else:
                self.checkpoint = {'completed_partners': [], 'processed_events': []}
        except Exception as e:
            logger.warning(f"⚠️  Could not load checkpoint: {e}")
            self.checkpoint = {'completed_partners': [], 'processed_events': []}
    
    def save_checkpoint(self, timing_partner_id: int = None, event_id: str = None, completed: bool = False):
        """Save progress checkpoint"""
        try:
            if completed and timing_partner_id:
                if timing_partner_id not in self.checkpoint['completed_partners']:
                    self.checkpoint['completed_partners'].append(timing_partner_id)
            
            if event_id:
                if event_id not in self.checkpoint['processed_events']:
                    self.checkpoint['processed_events'].append(event_id)
            
            self.checkpoint['last_updated'] = datetime.now().isoformat()
            
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint, f, indent=2)
                
        except Exception as e:
            logger.warning(f"⚠️  Could not save checkpoint: {e}")
    
    def get_haku_credentials(self) -> List[Tuple[int, str, str, int]]:
        """Get all Haku credentials for backfill"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT ppc.timing_partner_id, ppc.principal, ppc.secret, ppc.partner_provider_credential_id
            FROM partner_provider_credentials ppc
            WHERE ppc.provider_id = (SELECT provider_id FROM providers WHERE name = 'Haku')
            ORDER BY ppc.timing_partner_id
        """
        
        cursor.execute(query)
        credentials = cursor.fetchall()
        conn.close()
        
        logger.info(f"🔑 Found {len(credentials)} Haku credential sets")
        return credentials
    
    def get_existing_data_counts(self, timing_partner_id: int) -> Dict[str, int]:
        """Get counts of existing data for a timing partner"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        counts = {}
        
        # Count existing events
        cursor.execute("""
            SELECT COUNT(*) FROM haku_events WHERE timing_partner_id = %s
        """, (timing_partner_id,))
        counts['events'] = cursor.fetchone()[0]
        
        # Count existing participants
        cursor.execute("""
            SELECT COUNT(*) FROM haku_participants WHERE timing_partner_id = %s
        """, (timing_partner_id,))
        counts['participants'] = cursor.fetchone()[0]
        
        conn.close()
        return counts
    
    def get_events_needing_participants(self, timing_partner_id: int) -> List[Tuple[str, str, datetime]]:
        """Get events that need participant data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT DISTINCT he.event_id, he.event_name, he.start_date
            FROM haku_events he
            LEFT JOIN haku_participants hp ON he.event_id = hp.event_id AND he.timing_partner_id = hp.timing_partner_id
            WHERE he.timing_partner_id = %s
            AND hp.event_id IS NULL
            ORDER BY he.start_date DESC
        """
        
        cursor.execute(query, (timing_partner_id,))
        events = cursor.fetchall()
        conn.close()
        
        return events
    
    def backfill_timing_partner(self, timing_partner_id: int, principal: str, secret: str, credential_id: int) -> Dict:
        """Backfill all data for a specific timing partner"""
        
        # Skip if already completed
        if timing_partner_id in self.checkpoint.get('completed_partners', []):
            logger.info(f"⏭️  Skipping timing partner {timing_partner_id} (already completed)")
            return {'skipped': True}
        
        logger.info(f"\n🔄 Starting backfill for timing partner {timing_partner_id}")
        
        # Get baseline counts
        baseline_counts = self.get_existing_data_counts(timing_partner_id)
        logger.info(f"📊 Baseline - Events: {baseline_counts['events']}, Participants: {baseline_counts['participants']}")
        
        partner_stats = {
            'timing_partner_id': timing_partner_id,
            'events_processed': 0,
            'participants_processed': 0,
            'participants_inserted': 0,
            'errors': [],
            'start_time': datetime.now()
        }
        
        try:
            # Create adapter
            credentials_dict = {'principal': principal, 'secret': secret}
            adapter = HakuAdapter(credentials_dict, timing_partner_id)
            
            # Test authentication
            if not adapter.authenticate():
                raise Exception(f"Authentication failed for timing partner {timing_partner_id}")
            
            logger.info(f"✅ Authentication successful for timing partner {timing_partner_id}")
            
            # Get events that need participant data
            events_needing_participants = self.get_events_needing_participants(timing_partner_id)
            
            if not events_needing_participants:
                logger.info(f"✅ All events for timing partner {timing_partner_id} already have participant data")
                return partner_stats
            
            logger.info(f"📅 Found {len(events_needing_participants)} events needing participant data")
            
            event_count = 0
            participant_count = 0
            
            # Process each event with individual transactions
            for event_id, event_name, start_date in events_needing_participants:
                event_count += 1
                
                # Skip if already processed in checkpoint
                if event_id in self.checkpoint.get('processed_events', []):
                    logger.info(f"⏭️  Skipping event {event_id} (already processed)")
                    continue
                
                logger.info(f"🔍 Processing event {event_count}/{len(events_needing_participants)}: {event_name}")
                
                # Get database connection for this event
                conn = self.get_connection()
                event_participant_count = 0
                
                try:
                    # Get participants for this event
                    participants = adapter.get_participants(event_id)
                    self.stats['api_calls_made'] += 1
                    
                    if participants:
                        logger.info(f"👥 Found {len(participants)} participants for event {event_name}")
                        
                        # Store participants for this event
                        cursor = conn.cursor()
                        for participant in participants:
                            participant_count += 1
                            event_participant_count += 1
                            
                            try:
                                if not self.dry_run:
                                    # Insert participant data
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
                                        participant.participant_id,
                                        participant.bib_number,
                                        participant.first_name,
                                        participant.last_name,
                                        participant.email,
                                        participant.gender,
                                        participant.registration_date,
                                        principal[:10] + "...",
                                        timing_partner_id
                                    ))
                                    
                                    partner_stats['participants_inserted'] += 1
                                    
                            except Exception as e:
                                logger.error(f"❌ Error storing participant: {e}")
                                partner_stats['errors'].append(f"Participant error: {e}")
                                self.stats['errors'] += 1
                        
                        # Commit this event's participants
                        if not self.dry_run:
                            conn.commit()
                            logger.info(f"✅ Committed {event_participant_count} participants for event {event_name}")
                        
                    else:
                        logger.info(f"📭 No participants found for event {event_name}")
                    
                    # Save checkpoint for this event
                    self.save_checkpoint(event_id=event_id)
                    
                    # Rate limiting - respect Haku API limits
                    logger.debug(f"⏳ Rate limiting - sleeping {self.api_rate_limit} seconds")
                    time.sleep(self.api_rate_limit)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing event {event_name}: {e}")
                    partner_stats['errors'].append(f"Event {event_name} error: {e}")
                    self.stats['errors'] += 1
                    # Rollback this event's transaction on error
                    if not self.dry_run:
                        conn.rollback()
                        logger.warning(f"🔄 Rolled back transaction for event {event_name}")
                finally:
                    # Always close the connection for this event
                    conn.close()
                
                # Progress update every 5 events
                if event_count % 5 == 0:
                    logger.info(f"⏳ Progress: {event_count}/{len(events_needing_participants)} events processed")
                    self.save_checkpoint(timing_partner_id)
            
            # Update stats
            partner_stats['events_processed'] = event_count
            partner_stats['participants_processed'] = participant_count
            partner_stats['duration'] = (datetime.now() - partner_stats['start_time']).total_seconds()
            
            # Get final counts
            final_counts = self.get_existing_data_counts(timing_partner_id)
            
            logger.info(f"\n✅ Timing partner {timing_partner_id} backfill complete!")
            logger.info(f"📊 Final counts - Events: {final_counts['events']}, Participants: {final_counts['participants']}")
            logger.info(f"📈 Added - Participants: +{final_counts['participants'] - baseline_counts['participants']}")
            logger.info(f"⏱️  Duration: {partner_stats['duration']:.1f} seconds")
            
            # Mark as completed
            self.save_checkpoint(timing_partner_id, completed=True)
            
            return partner_stats
            
        except Exception as e:
            logger.error(f"❌ Fatal error for timing partner {timing_partner_id}: {e}")
            partner_stats['errors'].append(f"Fatal error: {e}")
            self.stats['errors'] += 1
            return partner_stats
    
    def run_complete_backfill(self, partner_limit: int = None) -> Dict:
        """Run complete backfill for all timing partners"""
        
        logger.info("🚀 Starting Haku Complete Backfill")
        logger.info("=" * 80)
        
        if self.dry_run:
            logger.info("🧪 DRY RUN MODE - No data will be written")
        
        # Get credentials
        credentials = self.get_haku_credentials()
        
        if partner_limit:
            credentials = credentials[:partner_limit]
            logger.info(f"🔬 Limited to first {partner_limit} timing partners for testing")
        
        # Process each timing partner
        partner_results = []
        
        for timing_partner_id, principal, secret, credential_id in credentials:
            self.stats['timing_partners_processed'] += 1
            
            try:
                result = self.backfill_timing_partner(timing_partner_id, principal, secret, credential_id)
                partner_results.append(result)
                
                # Update global stats
                if not result.get('skipped'):
                    self.stats['events_processed'] += result.get('events_processed', 0)
                    self.stats['participants_processed'] += result.get('participants_processed', 0)
                    self.stats['participants_inserted'] += result.get('participants_inserted', 0)
                
                # Additional rate limiting between partners
                if timing_partner_id != credentials[-1][0]:  # Don't sleep after last partner
                    time.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Fatal error processing timing partner {timing_partner_id}: {e}")
                self.stats['errors'] += 1
                continue
        
        # Calculate final statistics
        self.stats['duration'] = (datetime.now() - self.stats['start_time']).total_seconds()
        
        # Generate final report
        self.generate_final_report(partner_results)
        
        return {
            'stats': self.stats,
            'partner_results': partner_results
        }
    
    def generate_final_report(self, partner_results: List[Dict]):
        """Generate comprehensive final report"""
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 HAKU BACKFILL FINAL REPORT")
        logger.info("=" * 80)
        
        # Summary statistics
        total_duration = self.stats['duration']
        logger.info(f"⏱️  Total Duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        logger.info(f"📡 API Calls Made: {self.stats['api_calls_made']}")
        logger.info(f"📈 Events Processed: {self.stats['events_processed']}")
        logger.info(f"👥 Participants Processed: {self.stats['participants_processed']}")
        logger.info(f"✅ Participants Inserted: {self.stats['participants_inserted']}")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        
        # Partner breakdown
        logger.info("\n📍 Partner Breakdown:")
        for result in partner_results:
            if result.get('skipped'):
                continue
            
            timing_partner_id = result['timing_partner_id']
            events = result.get('events_processed', 0)
            participants = result.get('participants_inserted', 0)
            errors = len(result.get('errors', []))
            
            logger.info(f"   Partner {timing_partner_id}: {events} events, {participants} participants, {errors} errors")
        
        # Rate limiting analysis
        if self.stats['api_calls_made'] > 0:
            calls_per_hour = (self.stats['api_calls_made'] / total_duration) * 3600
            logger.info(f"\n🚦 Rate Limiting: {calls_per_hour:.1f} calls/hour (limit: 500)")
        
        # Recommendations
        logger.info("\n🎯 Recommendations:")
        if self.stats['errors'] == 0:
            logger.info("   ✅ Backfill completed successfully!")
            logger.info("   ✅ Ready to start event-driven scheduler")
        else:
            logger.info(f"   ⚠️  {self.stats['errors']} errors occurred - review logs")
            logger.info("   🔄 Consider re-running backfill to retry failed items")
        
        logger.info("\n🚀 Next Steps:")
        logger.info("   1. Review this log file for any errors")
        logger.info("   2. Start Haku scheduler: python3 haku_event_driven_scheduler.py")
        logger.info("   3. Monitor ongoing sync operations")
        
        logger.info("=" * 80)

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Haku Complete Backfill')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no data written)')
    parser.add_argument('--limit', type=int, help='Limit number of timing partners (for testing)')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    
    args = parser.parse_args()
    
    # Create backfill instance
    backfill = HakuBackfill(dry_run=args.dry_run)
    
    if args.resume:
        logger.info("📂 Resuming from checkpoint...")
    
    # Run backfill
    try:
        results = backfill.run_complete_backfill(partner_limit=args.limit)
        
        if results['stats']['errors'] == 0:
            logger.info("🎉 Backfill completed successfully!")
            return 0
        else:
            logger.warning(f"⚠️  Backfill completed with {results['stats']['errors']} errors")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⏸️  Backfill interrupted by user")
        logger.info("Use --resume to continue from checkpoint")
        return 130
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 