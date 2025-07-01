#!/usr/bin/env python3
"""
Production RunSignUp Sync Script
Syncs races, events, and participants from all RunSignUp credentials
"""

import sys
import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Tuple

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
    
    def __init__(self, db_path: str = "../../race_results.db"):
        self.db_path = db_path
        self.total_races = 0
        self.total_events = 0
        self.total_participants = 0
        self.failed_syncs = []
        
    def get_runsignup_credentials(self) -> List[Tuple[int, str, str, int]]:
        """Get all RunSignUp credentials from database"""
        conn = sqlite3.connect(self.db_path)
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sync_history (
                event_id, sync_time, num_of_synced_records, status, reason, 
                entries_success, entries_failed
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            datetime.now().isoformat(),
            records_synced,
            status,
            reason,
            records_synced if status == 'success' else 0,
            0 if status == 'success' else 1
        ))
        
        conn.commit()
        conn.close()
    
    def sync_timing_partner(self, timing_partner_id: int, principal: str, secret: str, credential_id: int) -> Dict:
        """Sync all data for a specific timing partner"""
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
            
            # Get races
            response = adapter._make_runsignup_request("/races", {"results_per_page": 1000})
            if 'races' not in response:
                error_msg = f"No races found for timing partner {timing_partner_id}"
                logger.warning(error_msg)
                return results
            
            races = response['races']
            logger.info(f"Found {len(races)} races for timing partner {timing_partner_id}")
            
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            
            try:
                for race_entry in races:
                    race_data = race_entry['race']
                    race_id = race_data['race_id']
                    
                    try:
                        # Store race
                        adapter.store_race(race_data, conn)
                        results['races'] += 1
                        logger.debug(f"Stored race {race_id}: {race_data.get('name')}")
                        
                        # Get detailed race info with events
                        race_details = adapter._make_runsignup_request(f"/race/{race_id}", {"include_event_days": "T"})
                        
                        if 'race' in race_details:
                            race_info = race_details['race']
                            events = race_info.get('events', [])
                            
                            for event_data in events:
                                event_id = event_data['event_id']
                                
                                try:
                                    # Store event
                                    adapter.store_event(event_data, race_id, conn)
                                    results['events'] += 1
                                    logger.debug(f"Stored event {event_id}: {event_data.get('name')}")
                                    
                                    # Get participants for this event
                                    participants_response = adapter._make_runsignup_request(
                                        "/race/participants", 
                                        {
                                            "event_id": event_id,
                                            "results_per_page": 1000,
                                            "include_individual_info": "T"
                                        }
                                    )
                                    
                                    if 'participants' in participants_response:
                                        participants = participants_response['participants']
                                        participant_count = len(participants)
                                        
                                        for participant_data in participants:
                                            try:
                                                adapter.store_participant(participant_data, race_id, event_id, conn)
                                                results['participants'] += 1
                                            except Exception as e:
                                                error_msg = f"Error storing participant: {e}"
                                                logger.error(error_msg)
                                                results['errors'].append(error_msg)
                                        
                                        # Log sync for this event
                                        self.log_sync_history(event_id, participant_count, 'success')
                                        logger.info(f"✅ Synced {participant_count} participants for event {event_id}")
                                    else:
                                        logger.info(f"No participants found for event {event_id}")
                                        self.log_sync_history(event_id, 0, 'success', 'No participants found')
                                
                                except Exception as e:
                                    error_msg = f"Error processing event {event_id}: {e}"
                                    logger.error(error_msg)
                                    results['errors'].append(error_msg)
                                    self.log_sync_history(event_id, 0, 'failed', str(e))
                    
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
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        # Test mode - sync only first timing partner
        logger.info("🧪 Running in TEST MODE - syncing only first timing partner")
        sync = RunSignUpProductionSync()
        credentials = sync.get_runsignup_credentials()
        if credentials:
            timing_partner_id, principal, secret, credential_id = credentials[0]
            sync.sync_timing_partner(timing_partner_id, principal, secret, credential_id)
    else:
        # Full production sync
        sync = RunSignUpProductionSync()
        sync.run_full_sync()

if __name__ == "__main__":
    main() 