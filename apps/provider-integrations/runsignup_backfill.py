#!/usr/bin/env python3
"""
RunSignUp Complete Backfill Script

This script safely backfills ALL RunSignUp data for all timing partners:
- Respects existing data (no duplicates)
- Progressive backfill with checkpoints
- Detailed logging and progress tracking
- Safe to run multiple times
- Production-ready error handling
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

from providers.runsignup_adapter import RunSignUpAdapter
from notifications import notify_backfill_success, notify_error, get_notification_status

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'runsignup_backfill_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RunSignUpBackfill:
    """Comprehensive RunSignUp backfill system"""
    
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
            'races_processed': 0,
            'events_processed': 0,
            'participants_processed': 0,
            'races_inserted': 0,
            'events_inserted': 0,
            'participants_inserted': 0,
            'races_updated': 0,
            'events_updated': 0,
            'participants_updated': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        # Progress checkpoints for resumability
        self.checkpoint_file = 'backfill_checkpoint.json'
        self.load_checkpoint()
        
    def get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(**self.db_config)
    
    def load_checkpoint(self):
        """Load backfill progress from checkpoint file"""
        try:
            if os.path.exists(self.checkpoint_file):
                with open(self.checkpoint_file, 'r') as f:
                    self.checkpoint = json.load(f)
                logger.info(f"📊 Loaded checkpoint: {self.checkpoint}")
            else:
                self.checkpoint = {'completed_partners': [], 'last_partner_id': None, 'start_time': str(datetime.now())}
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}")
            self.checkpoint = {'completed_partners': [], 'last_partner_id': None, 'start_time': str(datetime.now())}
    
    def save_checkpoint(self, partner_id: int = None, completed: bool = False):
        """Save backfill progress to checkpoint file"""
        try:
            if completed and partner_id:
                if partner_id not in self.checkpoint['completed_partners']:
                    self.checkpoint['completed_partners'].append(partner_id)
            
            if partner_id:
                self.checkpoint['last_partner_id'] = partner_id
                
            self.checkpoint['last_update'] = str(datetime.now())
            
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Could not save checkpoint: {e}")
    
    def get_runsignup_credentials(self, timing_partner_id: int = None) -> List[Tuple[int, str, str, int]]:
        """Get RunSignUp credentials for backfill, optionally filtered by timing partner ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if timing_partner_id:
            query = """
                SELECT timing_partner_id, principal, secret, partner_provider_credential_id
                FROM partner_provider_credentials 
                WHERE provider_id = 2 AND timing_partner_id = %s
                ORDER BY timing_partner_id
            """
            cursor.execute(query, (timing_partner_id,))
            logger.info(f"🎯 Looking for timing partner {timing_partner_id} credentials")
        else:
            query = """
                SELECT timing_partner_id, principal, secret, partner_provider_credential_id
                FROM partner_provider_credentials 
                WHERE provider_id = 2 
                ORDER BY timing_partner_id
            """
            cursor.execute(query)
        
        credentials = cursor.fetchall()
        conn.close()
        
        if timing_partner_id:
            if credentials:
                logger.info(f"✅ Found credentials for timing partner {timing_partner_id}")
            else:
                logger.error(f"❌ No credentials found for timing partner {timing_partner_id}")
        else:
            logger.info(f"🔑 Found {len(credentials)} RunSignUp credential sets")
        
        return credentials
    
    def fix_sequences(self) -> bool:
        """Fix PostgreSQL sequences for all RunSignUp tables"""
        logger.info("🔧 FIXING POSTGRESQL SEQUENCES")
        logger.info("=" * 50)
        
        tables_to_fix = [
            'runsignup_participants',
            'runsignup_events', 
            'runsignup_races'
        ]
        
        success_count = 0
        
        for table_name in tables_to_fix:
            try:
                logger.info(f"🔧 Fixing sequence for {table_name}...")
                
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Get the maximum existing ID
                cursor.execute(f"SELECT MAX(id) FROM {table_name};")
                max_id = cursor.fetchone()[0] or 0
                logger.info(f"📊 Max existing ID in {table_name}: {max_id}")
                
                # Get the sequence name
                cursor.execute(f"SELECT pg_get_serial_sequence('{table_name}', 'id');")
                result = cursor.fetchone()
                
                if not result or not result[0]:
                    logger.warning(f"⚠️  No sequence found for {table_name}.id")
                    conn.close()
                    continue
                
                sequence_name = result[0]
                logger.info(f"📋 Sequence name: {sequence_name}")
                
                # Get current sequence value
                cursor.execute(f"SELECT last_value FROM {sequence_name};")
                current_val = cursor.fetchone()[0]
                logger.info(f"📈 Current sequence value: {current_val}")
                
                # Fix sequence if needed
                if current_val <= max_id:
                    new_val = max_id + 1
                    logger.warning(f"🚨 PROBLEM: Sequence ({current_val}) <= Max ID ({max_id})")
                    logger.info(f"🔧 Setting sequence to {new_val}...")
                    
                    cursor.execute(f"SELECT setval('{sequence_name}', %s);", (new_val,))
                    
                    # Verify the fix
                    cursor.execute(f"SELECT last_value FROM {sequence_name};")
                    updated_val = cursor.fetchone()[0]
                    logger.info(f"✅ Sequence updated to: {updated_val}")
                    success_count += 1
                else:
                    logger.info(f"✅ Sequence OK: {current_val} > {max_id}")
                    success_count += 1
                
                conn.commit()
                conn.close()
                
            except Exception as e:
                logger.error(f"❌ Failed to fix sequence for {table_name}: {e}")
                if 'conn' in locals():
                    try:
                        conn.rollback()
                        conn.close()
                    except:
                        pass
                continue
            
            logger.info("")  # Empty line for readability
        
        logger.info("=" * 50)
        logger.info(f"🎯 SEQUENCE FIX RESULTS: {success_count}/{len(tables_to_fix)} sequences fixed")
        
        if success_count == len(tables_to_fix):
            logger.info("🎉 All sequences fixed! Proceeding with backfill...")
            return True
        else:
            logger.warning("⚠️  Some sequences could not be fixed. Proceeding anyway...")
            return False
    
    def get_existing_data_counts(self, timing_partner_id: int) -> Dict[str, int]:
        """Get counts of existing data for a timing partner"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        counts = {}
        
        # Count existing races
        cursor.execute("""
            SELECT COUNT(*) FROM runsignup_races WHERE timing_partner_id = %s
        """, (timing_partner_id,))
        counts['races'] = cursor.fetchone()[0]
        
        # Count existing events
        cursor.execute("""
            SELECT COUNT(*) FROM runsignup_events WHERE timing_partner_id = %s
        """, (timing_partner_id,))
        counts['events'] = cursor.fetchone()[0]
        
        # Count existing participants
        cursor.execute("""
            SELECT COUNT(*) FROM runsignup_participants WHERE timing_partner_id = %s
        """, (timing_partner_id,))
        counts['participants'] = cursor.fetchone()[0]
        
        conn.close()
        return counts
    
    def backfill_timing_partner(self, timing_partner_id: int, principal: str, secret: str, credential_id: int) -> Dict:
        """Backfill all data for a specific timing partner"""
        
        # Skip if already completed
        if timing_partner_id in self.checkpoint.get('completed_partners', []):
            logger.info(f"⏭️  Skipping timing partner {timing_partner_id} (already completed)")
            return {'skipped': True}
        
        logger.info(f"\n🔄 Starting backfill for timing partner {timing_partner_id}")
        
        # Get baseline counts
        baseline_counts = self.get_existing_data_counts(timing_partner_id)
        logger.info(f"📊 Baseline - Races: {baseline_counts['races']}, Events: {baseline_counts['events']}, Participants: {baseline_counts['participants']}")
        
        partner_stats = {
            'timing_partner_id': timing_partner_id,
            'races_processed': 0,
            'events_processed': 0,
            'participants_processed': 0,
            'races_inserted': 0,
            'events_inserted': 0,
            'participants_inserted': 0,
            'errors': [],
            'start_time': datetime.now()
        }
        
        try:
            # Create adapter
            credentials_dict = {'principal': principal, 'secret': secret}
            adapter = RunSignUpAdapter(credentials_dict, timing_partner_id)
            
            # Test authentication
            if not adapter.authenticate():
                raise Exception(f"Authentication failed for timing partner {timing_partner_id}")
            
            logger.info(f"✅ Authentication successful for timing partner {timing_partner_id}")
            
            # Get ALL events (not just future ones)
            logger.info("📥 Fetching all events...")
            provider_events = adapter.get_events()  # No date filter = all events
            
            if not provider_events:
                logger.warning(f"No events found for timing partner {timing_partner_id}")
                return partner_stats
            
            logger.info(f"📅 Found {len(provider_events)} total events for timing partner {timing_partner_id}")
            
            # Get database connection for bulk operations
            conn = self.get_connection()
            
            # Group events by race for efficient processing
            races_data = {}
            for event in provider_events:
                # Extract race_id from event's raw_data
                race_data = event.raw_data.get('race', {})
                race_id = race_data.get('race_id')
                if not race_id:
                    logger.warning(f"No race_id found for event {event.provider_event_id}, skipping")
                    continue
                    
                if race_id not in races_data:
                    races_data[race_id] = {
                        'race_info': race_data,
                        'events': []
                    }
                races_data[race_id]['events'].append(event)
            
            logger.info(f"📊 Processing {len(races_data)} races with {len(provider_events)} events")
            
            race_count = 0
            event_count = 0
            participant_count = 0
            
            # Process each race
            for race_id, race_data in races_data.items():
                race_count += 1
                
                if race_count % 10 == 0:
                    logger.info(f"⏳ Progress: {race_count}/{len(races_data)} races processed")
                    self.save_checkpoint(timing_partner_id)
                
                try:
                    # Store race data (adapter handles duplicates)
                    if race_data['race_info']:
                        if not self.dry_run:
                            stored_race_id = adapter.store_race(race_data['race_info'], conn)
                            if stored_race_id:
                                partner_stats['races_inserted'] += 1
                    
                    # Process events for this race
                    for event in race_data['events']:
                        event_count += 1
                        
                        try:
                            # Extract event_id from event's raw_data
                            event_data = event.raw_data.get('event', {})
                            event_id = event_data.get('event_id')
                            
                            if not event_id:
                                logger.warning(f"No event_id found for event {event.provider_event_id}, skipping")
                                continue
                            
                            # Store event data (adapter handles duplicates)
                            if not self.dry_run:
                                stored_event_id = adapter.store_event(event_data, race_id, conn)
                                if stored_event_id:
                                    partner_stats['events_inserted'] += 1
                            
                            # Get participants for this event
                            logger.debug(f"🔍 Fetching participants for event {event_id}")
                            participants = adapter.get_participants(race_id, str(event_id))
                            
                            if participants:
                                logger.info(f"👥 Found {len(participants)} participants for event {event_id}")
                                
                                # Store participants (adapter handles duplicates)
                                for participant in participants:
                                    participant_count += 1
                                    
                                    try:
                                        if not self.dry_run:
                                            adapter.store_participant(participant.to_dict(), race_id, event_id, conn)
                                            partner_stats['participants_inserted'] += 1
                                            
                                    except Exception as e:
                                        logger.error(f"❌ Error storing participant: {e}")
                                        partner_stats['errors'].append(f"Participant error: {e}")
                                        self.stats['errors'] += 1
                            
                        except Exception as e:
                            logger.error(f"❌ Error processing event {event_id}: {e}")
                            partner_stats['errors'].append(f"Event {event_id} error: {e}")
                            self.stats['errors'] += 1
                            continue
                
                except Exception as e:
                    logger.error(f"❌ Error processing race {race_id}: {e}")
                    partner_stats['errors'].append(f"Race {race_id} error: {e}")
                    self.stats['errors'] += 1
                    continue
            
            # Commit all changes
            if not self.dry_run:
                conn.commit()
            conn.close()
            
            # Update stats
            partner_stats['races_processed'] = race_count
            partner_stats['events_processed'] = event_count
            partner_stats['participants_processed'] = participant_count
            partner_stats['duration'] = (datetime.now() - partner_stats['start_time']).total_seconds()
            
            # Get final counts
            final_counts = self.get_existing_data_counts(timing_partner_id)
            
            logger.info(f"\n✅ Timing partner {timing_partner_id} backfill complete!")
            logger.info(f"📊 Final counts - Races: {final_counts['races']}, Events: {final_counts['events']}, Participants: {final_counts['participants']}")
            logger.info(f"📈 Added - Races: +{final_counts['races'] - baseline_counts['races']}, Events: +{final_counts['events'] - baseline_counts['events']}, Participants: +{final_counts['participants'] - baseline_counts['participants']}")
            logger.info(f"⏱️  Duration: {partner_stats['duration']:.1f} seconds")
            
            # Mark as completed
            self.save_checkpoint(timing_partner_id, completed=True)
            
            return partner_stats
            
        except Exception as e:
            logger.error(f"❌ Fatal error for timing partner {timing_partner_id}: {e}")
            partner_stats['errors'].append(f"Fatal error: {e}")
            self.stats['errors'] += 1
            return partner_stats
    
    def run_complete_backfill(self, partner_limit: int = None, timing_partner_id: int = None) -> Dict:
        """Run complete backfill for all timing partners or specific timing partner"""
        
        if timing_partner_id:
            logger.info(f"🎯 Starting RunSignUp Backfill for Timing Partner {timing_partner_id}")
        else:
            logger.info("🚀 Starting RunSignUp Complete Backfill")
        logger.info("=" * 80)
        
        if self.dry_run:
            logger.info("🧪 DRY RUN MODE - No data will be written")
        
        # Get credentials
        credentials = self.get_runsignup_credentials(timing_partner_id)
        
        if not credentials:
            if timing_partner_id:
                logger.error(f"❌ No credentials found for timing partner {timing_partner_id}")
            else:
                logger.error("❌ No RunSignUp credentials found")
            return {'stats': self.stats, 'partner_results': []}
        
        if partner_limit and not timing_partner_id:
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
                    self.stats['races_processed'] += result.get('races_processed', 0)
                    self.stats['events_processed'] += result.get('events_processed', 0)
                    self.stats['participants_processed'] += result.get('participants_processed', 0)
                    self.stats['races_inserted'] += result.get('races_inserted', 0)
                    self.stats['events_inserted'] += result.get('events_inserted', 0)
                    self.stats['participants_inserted'] += result.get('participants_inserted', 0)
                
                # Rate limiting to be nice to RunSignUp API
                time.sleep(2)
                
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
        logger.info("🎉 RUNSIGNUP BACKFILL COMPLETE!")
        logger.info("=" * 80)
        
        logger.info(f"⏱️  Total Duration: {self.stats['duration']:.1f} seconds ({self.stats['duration']/60:.1f} minutes)")
        logger.info(f"🏢 Timing Partners: {self.stats['timing_partners_processed']}")
        logger.info(f"🏁 Races Processed: {self.stats['races_processed']}")
        logger.info(f"📅 Events Processed: {self.stats['events_processed']}")
        logger.info(f"👥 Participants Processed: {self.stats['participants_processed']}")
        
        logger.info("\n📈 Data Inserted:")
        logger.info(f"   • Races: {self.stats['races_inserted']}")
        logger.info(f"   • Events: {self.stats['events_inserted']}")
        logger.info(f"   • Participants: {self.stats['participants_inserted']}")
        
        if self.stats['errors'] > 0:
            logger.warning(f"\n⚠️  Errors: {self.stats['errors']}")
        
        # Save detailed report
        report_file = f"backfill_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'stats': self.stats,
                'partner_results': partner_results,
                'checkpoint': self.checkpoint
            }, f, indent=2, default=str)
        
        logger.info(f"📄 Detailed report saved: {report_file}")
        
        # Clean up checkpoint on successful completion
        if self.stats['errors'] == 0:
            try:
                os.remove(self.checkpoint_file)
                logger.info("🧹 Checkpoint file cleaned up")
            except:
                pass

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RunSignUp Complete Backfill')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no data written)')
    parser.add_argument('--limit', type=int, help='Limit number of timing partners (for testing)')
    parser.add_argument('--timing-partner-id', type=int, help='Target specific timing partner ID (useful for new partners)')
    parser.add_argument('--fix-sequences', action='store_true', help='Fix PostgreSQL sequences before running backfill')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    
    args = parser.parse_args()
    
    # Create backfill instance
    backfill = RunSignUpBackfill(dry_run=args.dry_run)
    
    if args.fix_sequences:
        logger.info("🔧 Fixing PostgreSQL sequences before backfill...")
        backfill.fix_sequences()
        logger.info("")  # Empty line for readability
    
    if args.resume:
        logger.info("📂 Resuming from checkpoint...")
    
    # Run backfill
    try:
        results = backfill.run_complete_backfill(partner_limit=args.limit, timing_partner_id=args.timing_partner_id)
        
        if results['stats']['errors'] == 0:
            logger.info("🎉 Backfill completed successfully!")
            
            # Send success notification with actual counts
            total_events = results['stats'].get('events_processed', 0)
            total_races = results['stats'].get('races_processed', 0)
            total_participants = results['stats'].get('participants_processed', 0)
            
            try:
                notify_backfill_success(total_events, total_races, total_participants)
                logger.info("📱 Success notification sent")
            except Exception as notification_error:
                logger.error(f"Failed to send success notification: {notification_error}")
            
            return 0
        else:
            logger.warning(f"⚠️  Backfill completed with {results['stats']['errors']} errors")
            
            try:
                notify_error("Backfill Completed With Errors", 
                           f"Backfill finished but encountered {results['stats']['errors']} errors", 
                           f"Total processed - Events: {results['stats'].get('events_processed', 0)}, Participants: {results['stats'].get('participants_processed', 0)}")
                logger.info("📱 Error notification sent")
            except Exception as notification_error:
                logger.error(f"Failed to send error notification: {notification_error}")
            
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⏸️  Backfill interrupted by user")
        logger.info("Use --resume to continue from checkpoint")
        
        try:
            notify_error("Backfill Interrupted", "Backfill was manually interrupted by user", "Process stopped gracefully, use --resume to continue")
            logger.info("📱 Interruption notification sent")
        except Exception as notification_error:
            logger.error(f"Failed to send interruption notification: {notification_error}")
        
        return 130
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        
        try:
            notify_error("Backfill Fatal Error", str(e), "Critical system error during backfill process")
            logger.info("📱 Fatal error notification sent")
        except Exception as notification_error:
            logger.error(f"Failed to send fatal error notification: {notification_error}")
        
        return 1

if __name__ == "__main__":
    exit(main()) 