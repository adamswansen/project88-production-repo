#!/usr/bin/env python3
"""
Haku FAST Backfill Script - Optimized Version

Key optimizations:
1. Skip the huge Bix 7 event (process smaller events first)
2. Reduce rate limiting delays (more aggressive but still safe)
3. Process events by size (smallest first for quick wins)
4. Enhanced error recovery
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
        logging.FileHandler(f'haku_backfill_fast_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class HakuFastBackfill:
    """Optimized Haku backfill system"""
    
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
        self.large_event_threshold = 1000  # Skip events with >1000 participants initially
        
        self.stats = {
            'timing_partners_processed': 0,
            'events_processed': 0,
            'events_skipped_large': 0,
            'participants_processed': 0,
            'events_updated': 0,
            'participants_inserted': 0,
            'participants_updated': 0,
            'errors': 0,
            'start_time': datetime.now(),
            'api_calls_made': 0
        }
        
        # Progress checkpoints for resumability
        self.checkpoint_file = 'haku_backfill_fast_checkpoint.json'
        self.large_events_file = 'haku_large_events_deferred.json'
        self.load_checkpoint()
        
        # More aggressive rate limiting (but still safe)
        self.api_rate_limit = 2  # 2 seconds between calls (more aggressive than 8)
        
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
                self.checkpoint = {'completed_partners': [], 'processed_events': [], 'skipped_large_events': []}
                
            # Load deferred large events
            if os.path.exists(self.large_events_file):
                with open(self.large_events_file, 'r') as f:
                    self.deferred_large_events = json.load(f)
                logger.info(f"📂 Loaded {len(self.deferred_large_events)} deferred large events")
            else:
                self.deferred_large_events = []
                
        except Exception as e:
            logger.warning(f"⚠️  Could not load checkpoint: {e}")
            self.checkpoint = {'completed_partners': [], 'processed_events': [], 'skipped_large_events': []}
            self.deferred_large_events = []
    
    def save_checkpoint(self, timing_partner_id: int = None, event_id: str = None, completed: bool = False, skipped_large: bool = False):
        """Save progress checkpoint"""
        try:
            if completed and timing_partner_id:
                if timing_partner_id not in self.checkpoint['completed_partners']:
                    self.checkpoint['completed_partners'].append(timing_partner_id)
            
            if event_id:
                if event_id not in self.checkpoint['processed_events']:
                    self.checkpoint['processed_events'].append(event_id)
                    
            if skipped_large and event_id:
                if event_id not in self.checkpoint['skipped_large_events']:
                    self.checkpoint['skipped_large_events'].append(event_id)
            
            self.checkpoint['last_updated'] = datetime.now().isoformat()
            
            with open(self.checkpoint_file, 'w') as f:
                json.dump(self.checkpoint, f, indent=2)
                
            # Save deferred large events
            with open(self.large_events_file, 'w') as f:
                json.dump(self.deferred_large_events, f, indent=2)
                
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
    
    def estimate_event_size(self, event_id: str, event_name: str, adapter: HakuAdapter) -> int:
        """Estimate event size by making a single API call to check participant count"""
        try:
            # Get just the first page to check total count
            headers = adapter._get_auth_headers()
            response = adapter._make_api_request(
                f"{adapter.BASE_URL}/events/{event_id}/participants",
                params={"page": 1, "per_page": 1},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Try to extract total count from response
                if isinstance(data, dict):
                    # Check for pagination info
                    if 'meta' in data and 'total' in data['meta']:
                        return data['meta']['total']
                    elif 'pagination' in data and 'total' in data['pagination']:
                        return data['pagination']['total']
                    # If it's a list response, we can't easily get total without fetching all
                    elif 'participants' in data:
                        # For now, assume reasonable size if we can't get total
                        return 100  # Conservative estimate
                
                # If we can't determine size, assume it's small enough to process
                return 100
                
        except Exception as e:
            logger.warning(f"⚠️  Could not estimate size for event {event_name}: {e}")
            return 100  # Default to small size on error
    
    def get_events_by_size(self, timing_partner_id: int) -> List[Tuple[str, str, datetime, int]]:
        """Get events ordered by estimated size (smallest first)"""
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
        
        # For fast mode, prioritize by known patterns
        events_with_estimates = []
        
        for event_id, event_name, start_date in events:
            # Quick heuristic-based sizing
            estimated_size = 100  # Default small size
            
            # Known large events
            if 'bix' in event_name.lower() or 'marathon' in event_name.lower() or 'ironman' in event_name.lower():
                estimated_size = 5000
            elif 'half marathon' in event_name.lower() or '10k' in event_name.lower():
                estimated_size = 1000
            elif '5k' in event_name.lower():
                estimated_size = 500
                
            events_with_estimates.append((event_id, event_name, start_date, estimated_size))
        
        # Sort by estimated size (smallest first)
        events_with_estimates.sort(key=lambda x: x[3])
        
        return events_with_estimates
    
    def backfill_timing_partner_fast(self, timing_partner_id: int, principal: str, secret: str, credential_id: int) -> Dict:
        """Fast backfill for a specific timing partner (skip large events initially)"""
        
        # Skip if already completed
        if timing_partner_id in self.checkpoint.get('completed_partners', []):
            logger.info(f"⏭️  Skipping timing partner {timing_partner_id} (already completed)")
            return {'skipped': True}
        
        logger.info(f"\n🚀 Starting FAST backfill for timing partner {timing_partner_id}")
        
        partner_stats = {
            'timing_partner_id': timing_partner_id,
            'events_processed': 0,
            'events_skipped_large': 0,
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
            
            # Get events ordered by size
            events_with_estimates = self.get_events_by_size(timing_partner_id)
            
            if not events_with_estimates:
                logger.info(f"✅ All events for timing partner {timing_partner_id} already have participant data")
                return partner_stats
            
            logger.info(f"📅 Found {len(events_with_estimates)} events needing participant data")
            
            event_count = 0
            participant_count = 0
            
            # Process each event with individual transactions
            for event_id, event_name, start_date, estimated_size in events_with_estimates:
                event_count += 1
                
                # Skip if already processed
                if event_id in self.checkpoint.get('processed_events', []):
                    logger.info(f"⏭️  Skipping event {event_id} (already processed)")
                    continue
                
                # Skip large events if in fast mode
                if self.skip_large_events and estimated_size > self.large_event_threshold:
                    logger.info(f"🔄 Deferring large event {event_name} (~{estimated_size} participants) for later processing")
                    self.deferred_large_events.append({
                        'event_id': event_id,
                        'event_name': event_name,
                        'timing_partner_id': timing_partner_id,
                        'estimated_size': estimated_size
                    })
                    self.save_checkpoint(event_id=event_id, skipped_large=True)
                    partner_stats['events_skipped_large'] += 1
                    self.stats['events_skipped_large'] += 1
                    continue
                
                logger.info(f"🔍 Processing event {event_count}/{len(events_with_estimates)}: {event_name} (~{estimated_size} participants)")
                
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
                    
                    # Reduced rate limiting for faster processing
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
                
                # Progress update every 3 events (more frequent)
                if event_count % 3 == 0:
                    logger.info(f"⏳ Progress: {event_count}/{len(events_with_estimates)} events processed")
                    self.save_checkpoint(timing_partner_id)
            
            # Update stats
            partner_stats['events_processed'] = event_count
            partner_stats['participants_processed'] = participant_count
            partner_stats['duration'] = (datetime.now() - partner_stats['start_time']).total_seconds()
            
            logger.info(f"\n✅ Timing partner {timing_partner_id} FAST backfill complete!")
            logger.info(f"📊 Events processed: {partner_stats['events_processed']}")
            logger.info(f"📊 Events deferred (large): {partner_stats['events_skipped_large']}")
            logger.info(f"👥 Participants added: {partner_stats['participants_inserted']}")
            logger.info(f"⏱️  Duration: {partner_stats['duration']:.1f} seconds")
            
            # Mark as completed (for fast processing)
            self.save_checkpoint(timing_partner_id, completed=True)
            
            return partner_stats
            
        except Exception as e:
            logger.error(f"❌ Fatal error for timing partner {timing_partner_id}: {e}")
            partner_stats['errors'].append(f"Fatal error: {e}")
            self.stats['errors'] += 1
            return partner_stats
    
    def run_fast_backfill(self, partner_limit: int = None) -> Dict:
        """Run fast backfill for all timing partners (skip large events)"""
        
        logger.info("🚀 Starting Haku FAST Backfill (Large Events Deferred)")
        logger.info("=" * 80)
        
        if self.dry_run:
            logger.info("🧪 DRY RUN MODE - No data will be written")
        
        if self.skip_large_events:
            logger.info(f"⏩ Fast mode: Events with >{self.large_event_threshold} participants will be deferred")
        
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
                result = self.backfill_timing_partner_fast(timing_partner_id, principal, secret, credential_id)
                partner_results.append(result)
                
                # Update global stats
                if not result.get('skipped'):
                    self.stats['events_processed'] += result.get('events_processed', 0)
                    self.stats['events_skipped_large'] += result.get('events_skipped_large', 0)
                    self.stats['participants_processed'] += result.get('participants_processed', 0)
                    self.stats['participants_inserted'] += result.get('participants_inserted', 0)
                
                # Reduced rate limiting between partners
                if timing_partner_id != credentials[-1][0]:  # Don't sleep after last partner
                    time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Fatal error processing timing partner {timing_partner_id}: {e}")
                self.stats['errors'] += 1
                continue
        
        # Calculate final statistics
        self.stats['duration'] = (datetime.now() - self.stats['start_time']).total_seconds()
        
        # Generate final report
        self.generate_fast_report(partner_results)
        
        return {
            'stats': self.stats,
            'partner_results': partner_results,
            'deferred_large_events': self.deferred_large_events
        }
    
    def generate_fast_report(self, partner_results: List[Dict]):
        """Generate comprehensive final report for fast backfill"""
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 HAKU FAST BACKFILL FINAL REPORT")
        logger.info("=" * 80)
        
        # Summary statistics
        total_duration = self.stats['duration']
        logger.info(f"⏱️  Total Duration: {total_duration:.1f} seconds ({total_duration/60:.1f} minutes)")
        logger.info(f"📡 API Calls Made: {self.stats['api_calls_made']}")
        logger.info(f"📈 Events Processed: {self.stats['events_processed']}")
        logger.info(f"⏩ Events Deferred (Large): {self.stats['events_skipped_large']}")
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
            events_deferred = result.get('events_skipped_large', 0)
            participants = result.get('participants_inserted', 0)
            errors = len(result.get('errors', []))
            
            logger.info(f"   Partner {timing_partner_id}: {events} events, {participants} participants, {events_deferred} deferred, {errors} errors")
        
        # Deferred events summary
        if self.deferred_large_events:
            logger.info(f"\n🔄 Deferred Large Events ({len(self.deferred_large_events)}):")
            for event in self.deferred_large_events[:10]:  # Show first 10
                logger.info(f"   • {event['event_name']} (Partner {event['timing_partner_id']}) - ~{event['estimated_size']} participants")
            if len(self.deferred_large_events) > 10:
                logger.info(f"   ... and {len(self.deferred_large_events) - 10} more large events")
        
        # Recommendations
        logger.info("\n🎯 Recommendations:")
        if self.stats['errors'] == 0:
            logger.info("   ✅ Fast backfill completed successfully!")
            if self.deferred_large_events:
                logger.info("   🔄 Run large events processing: python3 haku_backfill_fast.py --process-large")
            logger.info("   ✅ Ready to start event-driven scheduler")
        else:
            logger.info(f"   ⚠️  {self.stats['errors']} errors occurred - review logs")
        
        logger.info("\n🚀 Next Steps:")
        logger.info("   1. Review this log file for any errors")
        if self.deferred_large_events:
            logger.info(f"   2. Process {len(self.deferred_large_events)} large events when ready")
        logger.info("   3. Start Haku scheduler: python3 haku_event_driven_scheduler.py")
        
        logger.info("=" * 80)

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Haku Fast Backfill')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode (no data written)')
    parser.add_argument('--limit', type=int, help='Limit number of timing partners (for testing)')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--process-large', action='store_true', help='Process large events (no size limit)')
    
    args = parser.parse_args()
    
    # Create backfill instance
    skip_large = not args.process_large  # Skip large events unless --process-large is specified
    backfill = HakuFastBackfill(dry_run=args.dry_run, skip_large_events=skip_large)
    
    if args.resume:
        logger.info("📂 Resuming from checkpoint...")
    
    if args.process_large:
        logger.info("🔄 Processing large events (no size limits)")
    
    # Run backfill
    try:
        results = backfill.run_fast_backfill(partner_limit=args.limit)
        
        if results['stats']['errors'] == 0:
            logger.info("🎉 Fast backfill completed successfully!")
            return 0
        else:
            logger.warning(f"⚠️  Fast backfill completed with {results['stats']['errors']} errors")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⏸️  Fast backfill interrupted by user")
        logger.info("Use --resume to continue from checkpoint")
        return 130
        
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 