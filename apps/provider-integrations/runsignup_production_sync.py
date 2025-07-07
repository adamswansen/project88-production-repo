#!/usr/bin/env python3
"""
Production RunSignUp Sync Script
Syncs races, events, and participants from all RunSignUp credentials
"""

import sys
import os
import psycopg2
import psycopg2.extras
import json
import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import argparse

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.runsignup_adapter import RunSignUpAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('runsignup_sync.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RunSignUpProductionSync:
    """Production RunSignUp sync orchestrator"""
    
    def __init__(self, db_config: Dict = None):
        if db_config is None:
            # PostgreSQL connection using environment variables with fallback defaults
            self.db_config = {
                'host': os.getenv('DB_HOST', 'localhost'),
                'database': os.getenv('DB_NAME', 'project88_myappdb'),
                'user': os.getenv('DB_USER', 'project88_myappuser'),
                'password': os.getenv('DB_PASSWORD', 'puctuq-cefwyq-3boqRe'),
                'port': int(os.getenv('DB_PORT', '5432'))
            }
        else:
            self.db_config = db_config
            
        self.total_races = 0
        self.total_events = 0
        self.total_participants = 0
        self.failed_syncs = []
        self.force_full_sync = False
        self.incremental_days = 7
        
    def get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(**self.db_config)
        
    def get_runsignup_credentials(self) -> List[Tuple[int, str, str, int]]:
        """Get all RunSignUp credentials from database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timing_partner_id, principal, secret, partner_provider_credential_id
            FROM partner_provider_credentials 
            WHERE provider_id = 2 
            ORDER BY timing_partner_id
        """)
        
        credentials = cursor.fetchall()
        conn.close()
        
        logger.info(f"Found {len(credentials)} RunSignUp credential sets")
        return credentials
    
    def log_sync_history(self, event_id: int, records_synced: int, status: str, reason: str = None):
        """Log sync operation to sync_history table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sync_history (
                event_id, sync_time, num_of_synced_records, status, reason, 
                entries_success, entries_failed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            event_id,
            datetime.now(),
            records_synced,
            status,
            reason,
            records_synced if status == 'success' else 0,
            0 if status == 'success' else 1
        ))
        
        conn.commit()
        conn.close()
    
    def sync_timing_partner(self, timing_partner_id: int, principal: str, secret: str, credential_id: int) -> Dict:
        """Sync all data for a specific timing partner using incremental sync when possible"""
        logger.info(f"Starting sync for timing partner {timing_partner_id} ({principal})")
        
        results = {
            'timing_partner_id': timing_partner_id,
            'races': 0,
            'events': 0,
            'participants': 0,
            'errors': []
        }
        
        try:
            # Create adapter
            credentials = {'principal': principal, 'secret': secret}
            adapter = RunSignUpAdapter(credentials, timing_partner_id)
            
            # Test authentication
            if not adapter.authenticate():
                error_msg = f"Authentication failed for timing partner {timing_partner_id}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
                return results
            
            logger.info(f"✅ Authentication successful for timing partner {timing_partner_id}")
            
            # Get events using paginated method (this also gives us the races)
            provider_events = adapter.get_events()
            if not provider_events:
                error_msg = f"No events found for timing partner {timing_partner_id}"
                logger.warning(error_msg)
                return results
            
            # Filter for future events only (no point syncing past events)
            future_events = [e for e in provider_events if e.event_date and e.event_date > datetime.now()]
            logger.info(f"📅 Found {len(provider_events)} total events, filtering to {len(future_events)} future events")
            
            if not future_events:
                logger.info(f"No future events found for timing partner {timing_partner_id}")
                return results
            
            # Group events by race_id to process races efficiently
            races_with_events = {}
            for event in future_events:
                race_data = event.raw_data.get('race', {})
                race_id = race_data.get('race_id')
                if race_id:
                    if race_id not in races_with_events:
                        races_with_events[race_id] = {
                            'race': race_data,
                            'events': []
                        }
                    races_with_events[race_id]['events'].append(event.raw_data.get('event', {}))
            
            logger.info(f"Found {len(races_with_events)} races with {len(future_events)} future events for timing partner {timing_partner_id}")
            
            # Connect to database
            conn = self.get_connection()
            
            try:
                for race_id, race_with_events in races_with_events.items():
                    race_data = race_with_events['race']
                    events = race_with_events['events']
                    
                    try:
                        # Store race
                        adapter.store_race(race_data, conn)
                        results['races'] += 1
                        logger.debug(f"Stored race {race_id}: {race_data.get('name')}")
                        
                        # Process pre-fetched events (no additional API call needed)
                        for event_data in events:
                            event_id = event_data['event_id']
                            
                            try:
                                # Store event
                                adapter.store_event(event_data, race_id, conn)
                                results['events'] += 1
                                logger.debug(f"Stored event {event_id}: {event_data.get('name')}")
                                
                                # Get last sync time for this event to enable incremental sync
                                last_sync_time = self._get_last_sync_time(event_id, conn)
                                
                                # Get participants using incremental sync
                                try:
                                    if self.force_full_sync or not last_sync_time:
                                        logger.info(f"🔄 Using full sync for event {event_id} {'(forced)' if self.force_full_sync else '(first sync)'}")
                                        provider_participants = adapter.get_participants(race_id, str(event_id))
                                        sync_type = "full"
                                    else:
                                        # Use incremental sync with safety check
                                        days_since_last_sync = (datetime.now() - last_sync_time).days
                                        if days_since_last_sync > self.incremental_days:
                                            logger.info(f"🔄 Using full sync for event {event_id} (last sync {days_since_last_sync} days ago, threshold: {self.incremental_days} days)")
                                            provider_participants = adapter.get_participants(race_id, str(event_id))
                                            sync_type = "full"
                                        else:
                                            logger.info(f"🔄 Using incremental sync for event {event_id} (last sync: {last_sync_time})")
                                            provider_participants = adapter.get_participants(race_id, str(event_id), last_sync_time)
                                            sync_type = "incremental"
                                    
                                    participant_count = len(provider_participants)
                                    
                                    if provider_participants:
                                        for provider_participant in provider_participants:
                                            try:
                                                # Extract raw data for direct storage
                                                participant_data = provider_participant.raw_data
                                                adapter.store_participant(participant_data, race_id, event_id, conn)
                                                results['participants'] += 1
                                            except Exception as e:
                                                error_msg = f"Error storing participant: {e}"
                                                logger.error(error_msg)
                                                results['errors'].append(error_msg)
                                        
                                        logger.info(f"✅ Synced {participant_count} participants for event {event_id} ({sync_type} sync)")
                                    else:
                                        logger.debug(f"No participants found for event {event_id} ({sync_type} sync)")
                                    
                                    # Update last sync time for this event
                                    self._update_last_sync_time(event_id, conn)
                                
                                except Exception as e:
                                    error_msg = f"Error getting participants for event {event_id}: {e}"
                                    logger.error(error_msg)
                                    results['errors'].append(error_msg)
                            
                            except Exception as e:
                                error_msg = f"Error storing event {event_id}: {e}"
                                logger.error(error_msg)
                                results['errors'].append(error_msg)
                        
                        # Get and log participant counts summary for the race
                        try:
                            participant_counts = adapter.get_participant_counts(race_id)
                            if participant_counts:
                                logger.debug(f"Participant counts for race {race_id}: {participant_counts}")
                        except Exception as e:
                            logger.debug(f"Could not get participant counts for race {race_id}: {e}")
                    
                    except Exception as e:
                        error_msg = f"Error processing race {race_id}: {e}"
                        logger.error(error_msg)
                        results['errors'].append(error_msg)
                
                # Commit all changes
                conn.commit()
                logger.info(f"✅ Committed all changes for timing partner {timing_partner_id}")
                
            finally:
                conn.close()
        
        except Exception as e:
            error_msg = f"Critical error syncing timing partner {timing_partner_id}: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        # Update totals
        self.total_races += results['races']
        self.total_events += results['events']
        self.total_participants += results['participants']
        
        logger.info(f"✅ Completed sync for timing partner {timing_partner_id}: "
                   f"{results['races']} races, {results['events']} events, "
                   f"{results['participants']} participants")
        
        return results
    
    def _get_last_sync_time(self, event_id: int, conn) -> Optional[datetime]:
        """Get the last sync time for an event"""
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT MAX(fetched_date) 
                FROM runsignup_participants 
                WHERE event_id = %s
            """, (event_id,))
            result = cursor.fetchone()
            return result[0] if result and result[0] else None
        except Exception as e:
            logger.debug(f"Could not get last sync time for event {event_id}: {e}")
            return None
    
    def _update_last_sync_time(self, event_id: int, conn):
        """Update the last sync time for an event"""
        cursor = conn.cursor()
        try:
            current_time = datetime.now()
            cursor.execute("""
                UPDATE runsignup_events 
                SET fetched_date = %s 
                WHERE event_id = %s
            """, (current_time, event_id))
            logger.debug(f"Updated last sync time for event {event_id}")
        except Exception as e:
            logger.debug(f"Could not update last sync time for event {event_id}: {e}")
    
    def run_full_sync(self):
        """Run complete sync for all RunSignUp credentials"""
        start_time = datetime.now()
        logger.info("🚀 Starting RunSignUp Production Sync")
        logger.info("=" * 80)
        
        # Get all credentials
        credentials = self.get_runsignup_credentials()
        
        if not credentials:
            logger.error("❌ No RunSignUp credentials found!")
            return
        
        # Sync each timing partner
        all_results = []
        for timing_partner_id, principal, secret, credential_id in credentials:
            try:
                results = self.sync_timing_partner(timing_partner_id, principal, secret, credential_id)
                all_results.append(results)
                
                if results['errors']:
                    self.failed_syncs.append({
                        'timing_partner_id': timing_partner_id,
                        'errors': results['errors']
                    })
            
            except Exception as e:
                error_msg = f"Failed to sync timing partner {timing_partner_id}: {e}"
                logger.error(error_msg)
                self.failed_syncs.append({
                    'timing_partner_id': timing_partner_id,
                    'errors': [error_msg]
                })
        
        # Final summary
        duration = (datetime.now() - start_time).total_seconds()
        logger.info("=" * 80)
        logger.info("🎉 RunSignUp Production Sync Complete!")
        logger.info(f"⏱️  Duration: {duration:.2f} seconds")
        logger.info(f"📊 Total Synced:")
        logger.info(f"   • {self.total_races} races")
        logger.info(f"   • {self.total_events} events") 
        logger.info(f"   • {self.total_participants} participants")
        
        if self.failed_syncs:
            logger.warning(f"⚠️  {len(self.failed_syncs)} timing partners had errors:")
            for failed in self.failed_syncs:
                logger.warning(f"   • Partner {failed['timing_partner_id']}: {len(failed['errors'])} errors")
        else:
            logger.info("✅ All timing partners synced successfully!")
        
        # Write summary to file
        summary = {
            'sync_time': start_time.isoformat(),
            'duration_seconds': duration,
            'total_races': self.total_races,
            'total_events': self.total_events,
            'total_participants': self.total_participants,
            'timing_partners_synced': len(credentials),
            'failed_syncs': self.failed_syncs,
            'detailed_results': all_results
        }
        
        with open('runsignup_sync_summary.json', 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info("📄 Detailed summary saved to runsignup_sync_summary.json")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='RunSignUp Production Sync')
    parser.add_argument('--test', action='store_true', help='Test mode - sync only first timing partner')
    parser.add_argument('--force-full-sync', action='store_true', help='Force full sync for all events (ignore last sync times)')
    parser.add_argument('--timing-partner', type=int, help='Sync only specific timing partner ID')
    parser.add_argument('--incremental-days', type=int, default=7, help='Days to look back for incremental sync (default: 7)')
    
    args = parser.parse_args()
    
    if args.test:
        # Test mode - sync only first timing partner
        logger.info("🧪 Running in TEST MODE - syncing only first timing partner")
        sync = RunSignUpProductionSync()
        sync.force_full_sync = args.force_full_sync
        sync.incremental_days = args.incremental_days
        credentials = sync.get_runsignup_credentials()
        if credentials:
            timing_partner_id, principal, secret, credential_id = credentials[0]
            sync.sync_timing_partner(timing_partner_id, principal, secret, credential_id)
    elif args.timing_partner:
        # Single timing partner mode
        logger.info(f"🎯 Running sync for timing partner {args.timing_partner}")
        sync = RunSignUpProductionSync()
        sync.force_full_sync = args.force_full_sync
        sync.incremental_days = args.incremental_days
        credentials = sync.get_runsignup_credentials()
        partner_found = False
        for timing_partner_id, principal, secret, credential_id in credentials:
            if timing_partner_id == args.timing_partner:
                sync.sync_timing_partner(timing_partner_id, principal, secret, credential_id)
                partner_found = True
                break
        if not partner_found:
            logger.error(f"❌ Timing partner {args.timing_partner} not found!")
    else:
        # Full production sync
        sync = RunSignUpProductionSync()
        sync.force_full_sync = args.force_full_sync
        sync.incremental_days = args.incremental_days
        
        if args.force_full_sync:
            logger.info("🔄 FULL SYNC MODE - All events will be fully synced")
        else:
            logger.info(f"⚡ INCREMENTAL SYNC MODE - Looking back {args.incremental_days} days for changes")
        
        sync.run_full_sync()

if __name__ == "__main__":
    main() 