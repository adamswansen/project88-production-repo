#!/usr/bin/env python3
"""
Race Roster Event-Driven Sync Scheduler

This scheduler implements sophisticated event-driven sync logic matching RunSignUp:
- Twice daily events/races discovery (6 AM and 6 PM)
- Event-proximity based sync frequencies:
  * Outside 24 hours: Incremental sync every 4 hours
  * Within 24 hours: Sync every 15 minutes  
  * Within 4 hours: Sync every minute
  * Stop: 1 hour past scheduled start time
- Priority-based processing with cycle limits
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
import threading
import signal

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.raceroster_adapter import RaceRosterAdapter

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'raceroster_event_driven_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class RaceRosterEventDrivenScheduler:
    """Event-driven Race Roster scheduler with dynamic frequency based on event proximity"""
    
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
        
        # Sync configuration with priority-based processing
        self.sync_config = {
            'events_discovery_hours': [6, 18],  # 6 AM and 6 PM
            'outside_24h_frequency_minutes': 240,  # Every 4 hours
            'within_24h_frequency_minutes': 15,    # Every 15 minutes
            'within_4h_frequency_minutes': 1,     # Every minute
            'stop_after_start_hours': 1,          # Stop 1 hour after event start
            'rate_limit_delay': 1,                # Seconds between API calls
            
            # Priority-based processing limits
            'max_high_priority_per_cycle': 50,    # Process up to 50 high-priority events per cycle
            'max_medium_priority_per_cycle': 20,  # Process up to 20 medium-priority events per cycle  
            'max_low_priority_per_cycle': 10,     # Process up to 10 low-priority events per cycle
            'cycle_sleep_seconds': 10,            # Sleep between cycles
        }
        
        self.stats = {
            'sync_start_time': datetime.now(),
            'events_discovered': 0,
            'events_synced': 0,
            'participants_synced': 0,
            'errors': 0,
            'active_events': 0,
            'cycles_completed': 0,
            'priority_stats': {
                'high': {'processed': 0, 'skipped': 0},
                'medium': {'processed': 0, 'skipped': 0}, 
                'low': {'processed': 0, 'skipped': 0}
            }
        }
        
        self.running = False
        self.sync_thread = None
        self.lock_file = '/tmp/raceroster_event_driven_scheduler.lock'
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def acquire_lock(self) -> bool:
        """Acquire file lock to prevent multiple instances"""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.lock_fd.write(str(os.getpid()))
            self.lock_fd.flush()
            return True
        except (IOError, OSError):
            return False
    
    def release_lock(self):
        """Release file lock"""
        try:
            if hasattr(self, 'lock_fd'):
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                os.unlink(self.lock_file)
        except:
            pass
    
    def should_discover_events(self) -> bool:
        """Check if it's time for event discovery (6 AM or 6 PM)"""
        current_hour = datetime.now().hour
        return current_hour in self.sync_config['events_discovery_hours']
    
    def discover_events(self):
        """Discover new events from all Race Roster timing partners"""
        logger.info("🔍 Starting Race Roster event discovery...")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get all Race Roster timing partners
        cursor.execute("""
            SELECT tp.timing_partner_id, tp.company_name, ppc.principal, ppc.secret
            FROM timing_partners tp
            JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
            WHERE ppc.provider_id = 3  -- Race Roster provider ID
        """)
        
        timing_partners = cursor.fetchall()
        new_events_found = 0
        
        for partner in timing_partners:
            timing_partner_id, company_name, principal, secret = partner
            
            logger.info(f"🏢 Discovering events for {company_name} (ID: {timing_partner_id})")
            
            try:
                # Create adapter
                credentials_dict = {
                    'principal': principal,
                    'secret': secret
                }
                adapter = RaceRosterAdapter(credentials_dict)
                
                # Get events - only upcoming events
                events = adapter.get_events()
                
                for event in events:
                    event_date = datetime.fromisoformat(event['startDate'].replace('Z', '+00:00'))
                    
                    # Only process upcoming events (not past events)
                    if event_date < datetime.now():
                        continue
                    
                                    # Check if event already exists
                cursor.execute("""
                    SELECT event_id FROM raceroster_events 
                    WHERE event_id = %s AND timing_partner_id = %s
                """, (event['eventId'], timing_partner_id))
                
                existing_event = cursor.fetchone()
                
                if not existing_event:
                    # Insert new event
                    cursor.execute("""
                        INSERT INTO raceroster_events (
                            event_id, timing_partner_id, name, 
                            start_date, created_at
                        ) VALUES (%s, %s, %s, %s, %s)
                    """, (
                        event['eventId'],
                        timing_partner_id,
                        event['name'],
                        event_date,
                        datetime.now()
                    ))
                    new_events_found += 1
                    logger.info(f"📅 New event: {event['name']} ({event_date})")
                
                conn.commit()
                time.sleep(self.sync_config['rate_limit_delay'])
                
            except Exception as e:
                logger.error(f"❌ Error discovering events for {company_name}: {e}")
                conn.rollback()
                self.stats['errors'] += 1
                continue
        
        cursor.close()
        conn.close()
        
        self.stats['events_discovered'] = new_events_found
        logger.info(f"✅ Discovery complete - {new_events_found} new events found")
    
    def get_events_for_sync_by_priority(self) -> Dict[str, List[Dict]]:
        """Get events that need syncing, organized by priority"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        
        # Get events that should be actively synced
        cursor.execute("""
            SELECT 
                re.event_id,
                re.event_id as external_event_id,
                re.start_date,
                re.timing_partner_id,
                re.name as event_name,
                tp.company_name,
                ppc.principal,
                ppc.secret,
                COALESCE(re.fetched_date, re.created_at) as last_sync_time
            FROM raceroster_events re
            JOIN timing_partners tp ON re.timing_partner_id = tp.timing_partner_id
            JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
            WHERE ppc.provider_id = 3  -- Race Roster provider ID
            AND re.start_date > %s - INTERVAL '1 hour'  -- Stop 1 hour after start
            ORDER BY re.start_date ASC
        """, (now,))
        
        events = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Organize events by priority
        priority_events = {'high': [], 'medium': [], 'low': []}
        
        for event in events:
            event_info = {
                'event_id': event[0],
                'external_event_id': event[1],
                'start_date': event[2],
                'timing_partner_id': event[3],
                'event_name': event[4],
                'company_name': event[5],
                'principal': event[6],
                'secret': event[7],
                'last_sync_time': event[8]
            }
            
            # Calculate time relationships
            time_until_start = event_info['start_date'] - now
            time_since_sync = now - event_info['last_sync_time'] if event_info['last_sync_time'] else timedelta(days=1)
            frequency_minutes = self.calculate_sync_frequency(event_info['start_date'], now)
            
            # Skip if frequency is 0 (event finished)
            if frequency_minutes == 0:
                continue
            
            # Check if sync is needed
            if time_since_sync < timedelta(minutes=frequency_minutes):
                continue  # Too soon to sync again
            
            # Add calculated fields
            event_info.update({
                'time_until_start': time_until_start,
                'time_since_sync': time_since_sync,
                'frequency_minutes': frequency_minutes
            })
            
            # Categorize by priority
            if time_until_start <= timedelta(hours=4):
                priority_events['high'].append(event_info)
            elif time_until_start <= timedelta(hours=24):
                priority_events['medium'].append(event_info)
            else:
                priority_events['low'].append(event_info)
        
        # Sort each priority group by time since last sync (oldest first)
        for priority in priority_events:
            priority_events[priority].sort(key=lambda x: x['time_since_sync'], reverse=True)
        
        return priority_events
    
    def calculate_sync_frequency(self, event_start_time: datetime, current_time: datetime) -> int:
        """Calculate sync frequency in minutes based on time until event start"""
        time_until_start = event_start_time - current_time
        time_since_start = current_time - event_start_time
        
        # Stop syncing 1 hour after event start
        if time_since_start > timedelta(hours=self.sync_config['stop_after_start_hours']):
            return 0  # Stop syncing
        
        # Within 4 hours (including post-start until +1hr): Every minute
        if time_until_start <= timedelta(hours=4):
            return self.sync_config['within_4h_frequency_minutes']
        
        # Within 24 hours: Every 15 minutes
        elif time_until_start <= timedelta(hours=24):
            return self.sync_config['within_24h_frequency_minutes']
        
        # Outside 24 hours: Every 4 hours
        else:
            return self.sync_config['outside_24h_frequency_minutes']

    def process_priority_events(self, events_by_priority: Dict[str, List[Dict]]):
        """Process events by priority with limits to prevent cycle overload"""
        
        # Priority processing order and limits
        priority_config = [
            ('high', self.sync_config['max_high_priority_per_cycle'], '🔴'),
            ('medium', self.sync_config['max_medium_priority_per_cycle'], '🟡'), 
            ('low', self.sync_config['max_low_priority_per_cycle'], '⚪')
        ]
        
        for priority_name, max_events, emoji in priority_config:
            if not self.running:
                break
                
            events = events_by_priority.get(priority_name, [])
            if not events:
                continue
                
            # Limit events to process this cycle
            events_to_process = events[:max_events]
            events_skipped = len(events) - len(events_to_process)
            
            logger.info(f"{emoji} Processing {len(events_to_process)} {priority_name}-priority events")
            
            for event_info in events_to_process:
                if not self.running:
                    break
                    
                try:
                    sync_result = self.sync_event_participants(event_info)
                    
                    if sync_result['status'] == 'success':
                        self.stats['events_synced'] += 1
                        self.stats['participants_synced'] += sync_result['participants_synced']
                        self.stats['priority_stats'][priority_name]['processed'] += 1
                    else:
                        self.stats['errors'] += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error syncing event {event_info['event_name']}: {e}")
                    self.stats['errors'] += 1
                    continue
                
                # Rate limiting
                time.sleep(self.sync_config['rate_limit_delay'])
            
            # Update skipped stats
            if events_skipped > 0:
                self.stats['priority_stats'][priority_name]['skipped'] += events_skipped
                logger.info(f"⏭️  Skipped {events_skipped} {priority_name}-priority events (will retry next cycle)")

    def sync_event_participants(self, event_info: Dict) -> Dict:
        """Sync participants for a specific event using incremental sync"""
        event_id = event_info['event_id']
        external_event_id = event_info['external_event_id']
        timing_partner_id = event_info['timing_partner_id']
        
        logger.info(f"🔄 Syncing event {event_info['event_name']} (ID: {event_id})")
        logger.info(f"   ⏰ Start time: {event_info['start_date']}")
        logger.info(f"   🕐 Time until start: {event_info['time_until_start']}")
        logger.info(f"   📊 Sync frequency: {event_info['frequency_minutes']} minutes")
        
        sync_result = {
            'event_id': event_id,
            'participants_synced': 0,
            'status': 'started',
            'errors': []
        }
        
        try:
            # Create adapter
            credentials_dict = {
                'principal': event_info['principal'],
                'secret': event_info['secret']
            }
            adapter = RaceRosterAdapter(credentials_dict)
            
            # Sync participants for this event
            participants = adapter.get_participants(external_event_id)
            
            if participants:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Store participants
                for participant in participants:
                    try:
                        # Check if participant exists
                        participant_id = participant.get('participantId')
                        cursor.execute("""
                            SELECT id FROM raceroster_participants 
                            WHERE event_id = %s AND registration_id = %s
                        """, (event_id, participant_id))
                        
                        existing = cursor.fetchone()
                        
                        if not existing:
                            cursor.execute("""
                                INSERT INTO raceroster_participants (
                                    event_id, timing_partner_id, registration_id,
                                    first_name, last_name, email, bib_number, gender,
                                    registration_date, registration_status, created_at
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """, (
                                event_id,
                                timing_partner_id,
                                participant_id,
                                participant.get('firstName'),
                                participant.get('lastName'),
                                participant.get('profile', {}).get('email'),
                                participant.get('bibNumber'),
                                'M' if participant.get('gender') == 1 else 'F' if participant.get('gender') == 2 else 'Other',
                                datetime.fromisoformat(participant['registrationDate'].replace('Z', '+00:00')) if participant.get('registrationDate') else None,
                                'active' if participant.get('isActive', True) else 'inactive',
                                datetime.now()
                            ))
                        sync_result['participants_synced'] += 1
                        
                    except Exception as e:
                        logger.warning(f"⚠️  Error storing participant {participant.get('participantId', 'Unknown')}: {e}")
                        sync_result['errors'].append(str(e))
                        continue
                
                # Update event sync time
                cursor.execute("""
                    UPDATE raceroster_events 
                    SET fetched_date = %s, current_participants = %s
                    WHERE event_id = %s
                """, (datetime.now(), sync_result['participants_synced'], event_id))
                
                conn.commit()
                cursor.close()
                conn.close()
                
                sync_result['status'] = 'success'
                logger.info(f"✅ Synced {sync_result['participants_synced']} participants")
            else:
                sync_result['status'] = 'success'
                logger.info("ℹ️  No participants found")
                
                # Still update sync time
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE raceroster_events 
                    SET fetched_date = %s
                    WHERE event_id = %s
                """, (datetime.now(), event_id))
                conn.commit()
                cursor.close()
                conn.close()
            
        except Exception as e:
            sync_result['status'] = 'error'
            sync_result['errors'].append(str(e))
            logger.error(f"❌ Error syncing participants: {e}")
        
        return sync_result
    
    def print_stats(self):
        """Print current statistics"""
        runtime = datetime.now() - self.stats['sync_start_time']
        
        logger.info("📊 === Race Roster Event-Driven Scheduler Stats ===")
        logger.info(f"⏱️  Runtime: {runtime}")
        logger.info(f"🔄 Cycles completed: {self.stats['cycles_completed']}")
        logger.info(f"📅 Events discovered: {self.stats['events_discovered']}")
        logger.info(f"✅ Events synced: {self.stats['events_synced']}")
        logger.info(f"👥 Participants synced: {self.stats['participants_synced']}")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        logger.info(f"🏃 Active events: {self.stats['active_events']}")
        
        # Priority stats
        for priority, stats in self.stats['priority_stats'].items():
            emoji = {'high': '🔴', 'medium': '🟡', 'low': '⚪'}[priority]
            logger.info(f"{emoji} {priority.title()}-priority: {stats['processed']} processed, {stats['skipped']} skipped")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    def start(self):
        """Start the event-driven scheduler"""
        if not self.acquire_lock():
            logger.error("❌ Another instance is already running")
            return False
        
        logger.info("🚀 Starting Race Roster Event-Driven Scheduler")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.running = True
        
        try:
            # Main scheduler loop
            while self.running:
                cycle_start = datetime.now()
                
                # Event discovery check (6 AM and 6 PM)
                if self.should_discover_events():
                    self.discover_events()
                
                # Get events organized by priority
                events_by_priority = self.get_events_for_sync_by_priority()
                
                # Calculate active events
                total_events = sum(len(events) for events in events_by_priority.values())
                self.stats['active_events'] = total_events
                
                if total_events > 0:
                    logger.info(f"🎯 Processing {total_events} events this cycle")
                    
                    # Process events by priority
                    self.process_priority_events(events_by_priority)
                else:
                    logger.info("😴 No events need syncing this cycle")
                
                # Update cycle stats
                self.stats['cycles_completed'] += 1
                
                # Print stats every 10 cycles
                if self.stats['cycles_completed'] % 10 == 0:
                    self.print_stats()
                
                # Sleep until next cycle
                cycle_duration = datetime.now() - cycle_start
                sleep_time = max(0, self.sync_config['cycle_sleep_seconds'] - cycle_duration.total_seconds())
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
        except Exception as e:
            logger.error(f"💥 Fatal error in scheduler: {e}")
            raise
        finally:
            self.release_lock()
            
        logger.info("🛑 Race Roster Event-Driven Scheduler stopped")
        return True
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=30)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Race Roster Event-Driven Scheduler')
    parser.add_argument('--dry-run', action='store_true', help='Run without making changes')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.dry_run:
        logger.info("🧪 Running in DRY RUN mode - no changes will be made")
    
    scheduler = RaceRosterEventDrivenScheduler()
    
    try:
        success = scheduler.start()
        return 0 if success else 1
    except KeyboardInterrupt:
        logger.info("👋 Interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 