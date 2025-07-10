#!/usr/bin/env python3
"""
ChronoTrack Live Backfill System for Project88Hub
Handles historical data import while avoiding duplicates from existing ChronoTrack TCP data

Key Features:
- Checks for duplicate events using check_duplicate_chronotrack_event function
- Avoids importing data that already exists from TCP hardware integration
- Follows established backfill patterns from Haku/RunSignUp
- Comprehensive logging and error handling
"""

import psycopg2
import psycopg2.extras
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse

from providers.chronotrack_live_adapter import ChronoTrackLiveAdapter

class ChronoTrackLiveBackfill:
    """Backfill system for ChronoTrack Live historical data"""
    
    def __init__(self, dry_run: bool = False, limit_events: int = None):
        self.db_config = {
            'host': 'localhost',
            'database': 'project88_myappdb', 
            'user': 'project88_myappuser',
            'password': 'puctuq-cefwyq-3boqRe',
            'port': 5432
        }
        
        self.dry_run = dry_run
        self.limit_events = limit_events
        
        # Backfill configuration
        self.config = {
            'max_concurrent_partners': 5,      # Process max 5 timing partners simultaneously
            'max_concurrent_events': 10,       # Process max 10 events per partner simultaneously
            'batch_size': 100,                 # Process participants in batches of 100
            'api_delay_seconds': 0.5,          # Delay between API calls
            'max_events_per_partner': 1000,    # Limit events per partner to avoid overload
            'start_date_cutoff_days': 365,     # Only process events from last 365 days
        }
        
        # Statistics tracking
        self.stats = {
            'timing_partners_processed': 0,
            'events_discovered': 0,
            'events_skipped_duplicate': 0,
            'events_processed': 0,
            'participants_imported': 0,
            'results_imported': 0,
            'api_calls': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        self.logger = logging.getLogger(__name__)

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def get_timing_partners_with_credentials(self) -> List[Tuple]:
        """Get timing partners with ChronoTrack Live credentials"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    tp.timing_partner_id,
                    tp.company_name,
                    ppc.principal,
                    ppc.secret,
                    ppc.additional_config
                FROM timing_partners tp
                JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
                WHERE ppc.provider_id = 1  -- ChronoTrack Live provider_id = 1
                AND ppc.principal IS NOT NULL 
                AND ppc.secret IS NOT NULL
                ORDER BY tp.timing_partner_id
            """)
            
            partners = cursor.fetchall()
            conn.close()
            
            self.logger.info(f"Found {len(partners)} timing partners with ChronoTrack Live credentials")
            return partners
            
        except Exception as e:
            self.logger.error(f"Error getting timing partners: {e}")
            return []

    def check_duplicate_event(self, event_name: str, event_date: datetime, timing_partner_id: int) -> bool:
        """
        Check if event already exists in TCP data using database function
        Returns True if duplicate exists (should skip), False if safe to import
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Use the database function we created in schema extension
            cursor.execute("""
                SELECT check_duplicate_chronotrack_event(%s, %s, %s)
            """, (event_name, event_date, timing_partner_id))
            
            is_duplicate = cursor.fetchone()[0]
            conn.close()
            
            if is_duplicate:
                self.logger.info(f"🔄 Skipping duplicate event: {event_name} (similar TCP event exists)")
                self.stats['events_skipped_duplicate'] += 1
                
            return is_duplicate
            
        except Exception as e:
            self.logger.error(f"Error checking duplicate event {event_name}: {e}")
            # If we can't check, err on the side of caution and assume it's not a duplicate
            return False

    def import_events_for_partner(self, partner_info: Tuple) -> Dict:
        """Import events for a specific timing partner"""
        timing_partner_id, company_name, principal, secret, additional_config = partner_info
        
        result = {
            'timing_partner_id': timing_partner_id,
            'company_name': company_name,
            'events_discovered': 0,
            'events_imported': 0,
            'events_skipped': 0,
            'participants_imported': 0,
            'results_imported': 0,
            'errors': 0,
            'success': True
        }
        
        try:
            self.logger.info(f"🚀 Starting backfill for {company_name} (Partner {timing_partner_id})")
            
            # Create adapter with credentials
            credentials = {
                'principal': principal,
                'secret': secret,
                'additional_config': additional_config or {}
            }
            
            adapter = ChronoTrackLiveAdapter(credentials, timing_partner_id)
            
            # Test authentication
            if not adapter.authenticate():
                self.logger.error(f"❌ Authentication failed for {company_name}")
                result['success'] = False
                result['errors'] += 1
                return result
            
            # Get events with date filtering
            cutoff_date = datetime.now() - timedelta(days=self.config['start_date_cutoff_days'])
            events = adapter.get_events()
            self.stats['api_calls'] += adapter.stats['api_calls']
            
            # Filter events by date and limit
            filtered_events = []
            for event in events:
                if event.event_date and event.event_date >= cutoff_date:
                    filtered_events.append(event)
                    
            # Apply limit if specified
            if self.limit_events and len(filtered_events) > self.limit_events:
                filtered_events = filtered_events[:self.limit_events]
                
            result['events_discovered'] = len(filtered_events)
            self.logger.info(f"📊 Found {len(filtered_events)} events for {company_name}")
            
            # Process events concurrently
            with ThreadPoolExecutor(max_workers=self.config['max_concurrent_events']) as executor:
                # Submit import jobs
                future_to_event = {
                    executor.submit(self.import_single_event, event, adapter, timing_partner_id): event 
                    for event in filtered_events
                }
                
                # Process completed jobs
                for future in as_completed(future_to_event):
                    event = future_to_event[future]
                    try:
                        event_result = future.result()
                        
                        if event_result['skipped_duplicate']:
                            result['events_skipped'] += 1
                        elif event_result['success']:
                            result['events_imported'] += 1
                            result['participants_imported'] += event_result['participants_imported']
                            result['results_imported'] += event_result['results_imported']
                        else:
                            result['errors'] += 1
                            
                    except Exception as e:
                        self.logger.error(f"❌ Event import exception for {event.event_name}: {e}")
                        result['errors'] += 1
            
            self.logger.info(f"✅ Backfill completed for {company_name}: {result['events_imported']} events imported, {result['events_skipped']} skipped")
            
        except Exception as e:
            self.logger.error(f"❌ Error processing partner {company_name}: {e}")
            result['success'] = False
            result['errors'] += 1
            
        return result

    def import_single_event(self, event, adapter: ChronoTrackLiveAdapter, timing_partner_id: int) -> Dict:
        """Import a single event with all its participants and results"""
        event_result = {
            'event_name': event.event_name,
            'success': False,
            'skipped_duplicate': False,
            'participants_imported': 0,
            'results_imported': 0,
            'error': None
        }
        
        try:
            # Check for duplicates against TCP data
            if self.check_duplicate_event(event.event_name, event.event_date, timing_partner_id):
                event_result['skipped_duplicate'] = True
                return event_result
            
            if self.dry_run:
                self.logger.info(f"🔍 DRY RUN: Would import event {event.event_name}")
                event_result['success'] = True
                return event_result
            
            # Store event in ct_events table
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert event
            cursor.execute("""
                INSERT INTO ct_events (
                    timing_partner_id, provider_event_id, event_name, event_description,
                    start_date, end_date, location, event_type, distance,
                    registration_limit, registration_fee, currency, status,
                    data_source, api_fetched_date, api_credentials_used, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                         'chronotrack_live', NOW(), %s, NOW(), NOW())
                ON CONFLICT (timing_partner_id, provider_event_id, data_source)
                DO UPDATE SET
                    event_name = EXCLUDED.event_name,
                    event_description = EXCLUDED.event_description,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    location = EXCLUDED.location,
                    updated_at = NOW()
                RETURNING event_id
            """, (
                timing_partner_id,
                event.provider_event_id,
                event.event_name,
                event.event_description,
                event.event_date,
                event.event_end_date,
                f"{event.location_city}, {event.location_state}" if event.location_city else event.location_name,
                event.event_type,
                str(event.distance) if event.distance else None,
                event.max_participants,
                event.registration_fee,
                event.currency,
                event.status,
                f"backfill_{timing_partner_id}"
            ))
            
            event_id = cursor.fetchone()[0]
            
            # Import participants
            time.sleep(self.config['api_delay_seconds'])
            participants = adapter.get_participants(event.provider_event_id)
            self.stats['api_calls'] += adapter.stats['api_calls']
            
            if participants:
                participants_imported = self.import_participants_batch(
                    participants, event_id, timing_partner_id, cursor
                )
                event_result['participants_imported'] = participants_imported
            
            # Import results (if event has finished)
            if event.event_date and event.event_date < datetime.now() - timedelta(hours=1):
                time.sleep(self.config['api_delay_seconds'])
                results = adapter.get_results(event.provider_event_id)
                self.stats['api_calls'] += adapter.stats['api_calls']
                
                if results:
                    results_imported = self.import_results_batch(
                        results, event_id, timing_partner_id, cursor
                    )
                    event_result['results_imported'] = results_imported
            
            # Record backfill in sync_history
            cursor.execute("""
                INSERT INTO sync_history (
                    timing_partner_id, provider_id, event_id, sync_type, 
                    status, participants_synced, results_synced, sync_time
                ) VALUES (%s, %s, %s, 'backfill', 'completed', %s, %s, NOW())
            """, (
                timing_partner_id, 
                1, 
                event.provider_event_id, 
                event_result['participants_imported'],
                event_result['results_imported']
            ))
            
            conn.commit()
            conn.close()
            
            event_result['success'] = True
            self.logger.info(f"✅ Imported event: {event.event_name} ({event_result['participants_imported']} participants, {event_result['results_imported']} results)")
            
        except Exception as e:
            self.logger.error(f"❌ Error importing event {event.event_name}: {e}")
            event_result['error'] = str(e)
            
        return event_result

    def import_participants_batch(self, participants: List, event_id: int, timing_partner_id: int, cursor) -> int:
        """Import participants in batches"""
        imported_count = 0
        
        for i in range(0, len(participants), self.config['batch_size']):
            batch = participants[i:i + self.config['batch_size']]
            
            for participant in batch:
                try:
                    cursor.execute("""
                        INSERT INTO ct_participants (
                            timing_partner_id, event_id, provider_participant_id,
                            first_name, last_name, email, phone, date_of_birth,
                            age, gender, city, state, country, bib_number,
                            emergency_contact, team_name, division, registration_date,
                            registration_status, payment_status, amount_paid,
                            data_source, api_fetched_date, created_at, updated_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            'chronotrack_live', NOW(), NOW(), NOW()
                        )
                        ON CONFLICT (timing_partner_id, event_id, provider_participant_id, data_source)
                        DO UPDATE SET
                            first_name = EXCLUDED.first_name,
                            last_name = EXCLUDED.last_name,
                            email = EXCLUDED.email,
                            updated_at = NOW()
                    """, (
                        timing_partner_id,
                        event_id,
                        participant.provider_participant_id,
                        participant.first_name,
                        participant.last_name,
                        participant.email,
                        participant.phone,
                        participant.date_of_birth,
                        participant.age,
                        participant.gender,
                        participant.city,
                        participant.state,
                        participant.country,
                        participant.bib_number,
                        json.dumps(participant.emergency_contact) if participant.emergency_contact else None,
                        participant.team_name,
                        participant.division,
                        participant.registration_date,
                        'active',
                        'paid' if participant.payment_amount else 'pending',
                        participant.payment_amount
                    ))
                    
                    imported_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Error importing participant {participant.first_name} {participant.last_name}: {e}")
                    continue
        
        return imported_count

    def import_results_batch(self, results: List, event_id: int, timing_partner_id: int, cursor) -> int:
        """Import results in batches"""
        imported_count = 0
        
        for result_data in results:
            try:
                cursor.execute("""
                    INSERT INTO ct_results (
                        timing_partner_id, event_id, participant_id, provider_result_id,
                        bib_number, chip_time, gun_time, overall_place, gender_place,
                        division_place, finish_time, split_times, result_status,
                        data_source, api_fetched_date, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        'chronotrack_live', NOW(), NOW()
                    )
                    ON CONFLICT (timing_partner_id, event_id, bib_number, data_source)
                    DO UPDATE SET
                        chip_time = EXCLUDED.chip_time,
                        gun_time = EXCLUDED.gun_time,
                        overall_place = EXCLUDED.overall_place,
                        finish_time = EXCLUDED.finish_time
                """, (
                    timing_partner_id,
                    event_id,
                    result_data.get('participant_id'),
                    result_data.get('provider_result_id'),
                    result_data.get('bib_number'),
                    result_data.get('chip_time'),
                    result_data.get('gun_time'),
                    result_data.get('overall_place'),
                    result_data.get('gender_place'),
                    result_data.get('division_place'),
                    result_data.get('finish_time'),
                    json.dumps(result_data.get('split_times', [])) if result_data.get('split_times') else None,
                    result_data.get('status', 'finished')
                ))
                
                imported_count += 1
                
            except Exception as e:
                self.logger.error(f"Error importing result for bib {result_data.get('bib_number', 'unknown')}: {e}")
                continue
        
        return imported_count

    def run_backfill(self) -> Dict:
        """Run the complete backfill process"""
        try:
            self.logger.info("🚀 Starting ChronoTrack Live backfill process")
            
            if self.dry_run:
                self.logger.info("🔍 DRY RUN MODE: No data will be modified")
            
            # Get timing partners
            partners = self.get_timing_partners_with_credentials()
            
            if not partners:
                self.logger.error("❌ No timing partners with ChronoTrack Live credentials found")
                return {'success': False, 'error': 'No timing partners found'}
            
            # Process partners concurrently
            max_workers = min(len(partners), self.config['max_concurrent_partners'])
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit partner jobs
                future_to_partner = {
                    executor.submit(self.import_events_for_partner, partner): partner 
                    for partner in partners
                }
                
                # Process completed jobs
                for future in as_completed(future_to_partner):
                    partner = future_to_partner[future]
                    try:
                        result = future.result()
                        
                        self.stats['timing_partners_processed'] += 1
                        self.stats['events_discovered'] += result['events_discovered']
                        self.stats['events_processed'] += result['events_imported']
                        self.stats['participants_imported'] += result['participants_imported']
                        self.stats['results_imported'] += result['results_imported']
                        self.stats['errors'] += result['errors']
                        
                        if result['success']:
                            self.logger.info(f"✅ Partner {result['company_name']} completed successfully")
                        else:
                            self.logger.error(f"❌ Partner {result['company_name']} failed")
                            
                    except Exception as e:
                        self.logger.error(f"❌ Partner processing exception: {e}")
                        self.stats['errors'] += 1
            
            # Final statistics
            runtime = datetime.now() - self.stats['start_time']
            
            self.logger.info(f"""
📊 ChronoTrack Live Backfill Complete:
   ⏱️  Runtime: {runtime}
   👥 Timing partners processed: {self.stats['timing_partners_processed']}
   🎯 Events discovered: {self.stats['events_discovered']}
   ✅ Events processed: {self.stats['events_processed']}
   🔄 Events skipped (duplicates): {self.stats['events_skipped_duplicate']}
   👤 Participants imported: {self.stats['participants_imported']}
   📊 Results imported: {self.stats['results_imported']}
   🔗 API calls made: {self.stats['api_calls']}
   ❌ Errors: {self.stats['errors']}
            """)
            
            return {
                'success': True,
                'stats': self.stats
            }
            
        except Exception as e:
            self.logger.error(f"❌ Backfill process failed: {e}")
            return {'success': False, 'error': str(e)}

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='ChronoTrack Live Backfill System')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry run mode (no data modifications)')
    parser.add_argument('--limit-events', type=int, help='Limit number of events to process per partner')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/tmp/chronotrack_live_backfill.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create and run backfill
    backfill = ChronoTrackLiveBackfill(
        dry_run=args.dry_run,
        limit_events=args.limit_events
    )
    
    try:
        result = backfill.run_backfill()
        
        if result['success']:
            logging.info("🎉 Backfill completed successfully")
        else:
            logging.error(f"❌ Backfill failed: {result.get('error', 'Unknown error')}")
            
    except KeyboardInterrupt:
        logging.info("📝 Backfill interrupted by user")
    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main() 