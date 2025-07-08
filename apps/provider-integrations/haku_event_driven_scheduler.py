#!/usr/bin/env python3
"""
Haku Event-Driven Sync Scheduler

This scheduler implements sophisticated event-driven sync logic for Haku:
- Twice daily events discovery (if event doesn't exist, get all participants)
- Event-proximity based sync frequencies:
  * Outside 24 hours: Incremental sync every 4 hours
  * Within 24 hours: Sync every 15 minutes  
  * Within 4 hours: Sync every minute
  * Stop: 1 hour past scheduled start time
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

from providers.haku_adapter import HakuAdapter

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'haku_event_driven_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class HakuEventDrivenScheduler:
    """
    Event-driven sync scheduler for Haku with priority-based processing
    """
    
    def __init__(self):
        # PostgreSQL connection using environment variables
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'project88_myappdb'),
            'user': os.getenv('DB_USER', 'project88_myappuser'),
            'password': os.getenv('DB_PASSWORD', 'puctuq-cefwyq-3boqRe'),
            'port': int(os.getenv('DB_PORT', '5432'))
        }
        
        # Sync configuration with priority-based processing
        self.sync_config = {
            'events_discovery_hours': [6, 18],  # 6 AM and 6 PM
            'outside_24h_frequency_minutes': 240,  # Every 4 hours
            'within_24h_frequency_minutes': 15,    # Every 15 minutes
            'within_4h_frequency_minutes': 1,     # Every minute
            'stop_after_start_hours': 1,          # Stop 1 hour after event start
            'rate_limit_delay': 2,                # Seconds between API calls (conservative)
            
            # Priority-based processing limits
            'max_high_priority_per_cycle': 50,    # Process up to 50 high-priority events per cycle
            'max_medium_priority_per_cycle': 20,  # Process up to 20 medium-priority events per cycle  
            'max_low_priority_per_cycle': 10,     # Process up to 10 low-priority events per cycle
            'cycle_sleep_seconds': 15,            # Sleep between cycles (longer for Haku)
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
        self.lock_file = '/tmp/haku_event_driven_scheduler.lock'
        
    def get_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(**self.db_config)
    
    def prevent_concurrent_execution(self) -> bool:
        """Prevent multiple scheduler instances"""
        try:
            if os.path.exists(self.lock_file):
                with open(self.lock_file, 'r') as f:
                    pid = int(f.read().strip())
                try:
                    os.kill(pid, 0)  # Check if process exists
                    logger.error(f"❌ Haku scheduler already running (PID: {pid})")
                    return False
                except OSError:
                    logger.info(f"🧹 Removing stale lock file (PID: {pid})")
                    os.remove(self.lock_file)
            
            with open(self.lock_file, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create lock file: {e}")
            return False
    
    def release_lock(self):
        """Release the lock file"""
        try:
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except Exception as e:
            logger.error(f"❌ Failed to remove lock file: {e}")
    
    def get_timing_partners(self) -> List[Tuple[int, str, str, str, str]]:
        """Get timing partners with Haku provider credentials"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                tp.timing_partner_id, 
                tp.company_name, 
                ppc.principal, 
                ppc.secret,
                ppc.additional_config->>'organization_name' as organization_name
            FROM timing_partners tp
            JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
            WHERE ppc.provider_id = (SELECT provider_id FROM providers WHERE name = 'Haku')
            ORDER BY tp.timing_partner_id
        """)
        
        partners = cursor.fetchall()
        conn.close()
        return partners
    
    def discover_events_and_races(self):
        """Discover new events from all timing partners"""
        logger.info("🔍 Starting Haku events discovery")
        timing_partners = self.get_timing_partners()
        
        if not timing_partners:
            logger.warning("⚠️  No timing partners with Haku credentials found")
            return
        
        new_events_found = 0
        
        for timing_partner_id, company_name, client_id, client_secret, organization_name in timing_partners:
            try:
                logger.info(f"📡 Discovering events for {company_name} ({organization_name})")
                
                # Create adapter with credentials
                credentials = {
                    'principal': client_id,
                    'secret': client_secret,
                    'additional_config': {'organization_name': organization_name}
                }
                
                adapter = HakuAdapter(credentials, timing_partner_id)
                
                # Get all events
                events = adapter.get_events()
                
                conn = self.get_connection()
                cursor = conn.cursor()
                
                for event in events:
                    # Check if event already exists
                    cursor.execute("""
                        SELECT COUNT(*) FROM haku_events 
                        WHERE event_id = %s AND timing_partner_id = %s
                    """, (event.provider_event_id, timing_partner_id))
                    
                    exists = cursor.fetchone()[0] > 0
                    
                    if not exists:
                        # Insert new event
                        cursor.execute("""
                            INSERT INTO haku_events (
                                event_id, event_name, event_description, start_date, end_date,
                                location, event_type, distance, registration_limit,
                                registration_fee, currency, status, fetched_date,
                                credentials_used, timing_partner_id, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s, NOW())
                        """, (
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
                            client_id[:10] + "...",
                            timing_partner_id
                        ))
                        
                        new_events_found += 1
                        logger.info(f"✅ New event: {event.event_name} ({event.provider_event_id})")
                        
                        # Queue full participant sync for new events
                        cursor.execute("""
                            INSERT INTO sync_queue (
                                timing_partner_id, provider_id, event_id, 
                                operation_type, sync_direction, status, 
                                created_at, scheduled_time
                            ) VALUES (%s, %s, %s, 'participants', 'pull', 'queued', NOW(), NOW())
                        """, (timing_partner_id, 5, event.provider_event_id))  # 5 = Haku provider ID
                
                conn.commit()
                conn.close()
                
                logger.info(f"📊 {company_name}: {len(events)} events processed")
                time.sleep(self.sync_config['rate_limit_delay'])
                
            except Exception as e:
                logger.error(f"❌ Error discovering events for partner {timing_partner_id}: {e}")
                self.stats['errors'] += 1
                continue
        
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
                he.event_id,
                he.start_date,
                he.timing_partner_id,
                he.event_name,
                tp.company_name,
                ppc.principal,
                ppc.secret,
                ppc.additional_config->>'organization_name' as organization_name,
                COALESCE(MAX(sh.sync_time), he.created_at) as last_sync_time
            FROM haku_events he
            JOIN timing_partners tp ON he.timing_partner_id = tp.timing_partner_id
            JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
            LEFT JOIN sync_history sh ON he.event_id = sh.event_id 
                AND sh.timing_partner_id = he.timing_partner_id
                AND sh.status = 'completed'
            WHERE ppc.provider_id = (SELECT provider_id FROM providers WHERE name = 'Haku')
            AND he.start_date IS NOT NULL
            AND he.start_date > %s  -- Only future events or very recent past
            GROUP BY he.event_id, he.start_date, he.timing_partner_id, he.event_name, 
                     tp.company_name, ppc.principal, ppc.secret, organization_name, he.created_at
            ORDER BY he.start_date ASC
        """, (now - timedelta(hours=self.sync_config['stop_after_start_hours']),))
        
        events = cursor.fetchall()
        conn.close()
        
        # Organize events by priority
        priority_events = {
            'high': [],
            'medium': [],
            'low': []
        }
        
        for event in events:
            event_dict = dict(event)
            event_start_time = event_dict['start_date']
            last_sync_time = event_dict['last_sync_time']
            
            # Calculate time since last sync
            time_since_sync = (now - last_sync_time).total_seconds() / 60  # minutes
            
            # Calculate required sync frequency
            required_frequency = self.calculate_sync_frequency(event_start_time, now)
            
            if required_frequency == 0:
                continue  # Skip events that don't need syncing
            
            # Determine if sync is needed
            if time_since_sync >= required_frequency:
                event_dict['time_since_sync'] = time_since_sync
                event_dict['required_frequency'] = required_frequency
                
                # Categorize by priority
                time_until_start = event_start_time - now
                
                if time_until_start <= timedelta(hours=4):
                    priority_events['high'].append(event_dict)
                elif time_until_start <= timedelta(hours=24):
                    priority_events['medium'].append(event_dict)
                else:
                    priority_events['low'].append(event_dict)
        
        # Sort each priority group by time since last sync (most overdue first)
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
        """Process events by priority with configurable limits"""
        
        # Process high priority events (within 4 hours)
        high_priority = events_by_priority['high'][:self.sync_config['max_high_priority_per_cycle']]
        self.stats['priority_stats']['high']['skipped'] += len(events_by_priority['high']) - len(high_priority)
        
        for event in high_priority:
            success = self.sync_event_participants(event)
            if success:
                self.stats['priority_stats']['high']['processed'] += 1
            time.sleep(self.sync_config['rate_limit_delay'])
        
        # Process medium priority events (within 24 hours)
        medium_priority = events_by_priority['medium'][:self.sync_config['max_medium_priority_per_cycle']]
        self.stats['priority_stats']['medium']['skipped'] += len(events_by_priority['medium']) - len(medium_priority)
        
        for event in medium_priority:
            success = self.sync_event_participants(event)
            if success:
                self.stats['priority_stats']['medium']['processed'] += 1
            time.sleep(self.sync_config['rate_limit_delay'])
        
        # Process low priority events (outside 24 hours)
        low_priority = events_by_priority['low'][:self.sync_config['max_low_priority_per_cycle']]
        self.stats['priority_stats']['low']['skipped'] += len(events_by_priority['low']) - len(low_priority)
        
        for event in low_priority:
            success = self.sync_event_participants(event)
            if success:
                self.stats['priority_stats']['low']['processed'] += 1
            time.sleep(self.sync_config['rate_limit_delay'])
    
    def sync_event_participants(self, event: Dict) -> bool:
        """Sync participants for a specific event"""
        try:
            event_id = event['event_id']
            timing_partner_id = event['timing_partner_id']
            event_name = event['event_name']
            client_id = event['principal']
            client_secret = event['secret']
            organization_name = event['organization_name']
            
            logger.info(f"🔄 Syncing participants for {event_name} ({event_id})")
            
            # Create adapter
            credentials = {
                'principal': client_id,
                'secret': client_secret,
                'additional_config': {'organization_name': organization_name}
            }
            
            adapter = HakuAdapter(credentials, timing_partner_id)
            
            # Get participants
            participants = adapter.get_participants(event_id)
            
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Store participants
            participants_synced = 0
            
            for participant in participants:
                cursor.execute("""
                    INSERT INTO haku_participants (
                        event_id, participant_id, bib_number, first_name, last_name,
                        email, phone, date_of_birth, gender, nationality, emergency_contact,
                        team_affiliation, category, registration_date, payment_status,
                        amount_paid, fetched_date, credentials_used, timing_partner_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
                    ON CONFLICT (participant_id) DO UPDATE SET
                        bib_number = EXCLUDED.bib_number,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        email = EXCLUDED.email,
                        phone = EXCLUDED.phone,
                        date_of_birth = EXCLUDED.date_of_birth,
                        gender = EXCLUDED.gender,
                        nationality = EXCLUDED.nationality,
                        emergency_contact = EXCLUDED.emergency_contact,
                        team_affiliation = EXCLUDED.team_affiliation,
                        category = EXCLUDED.category,
                        registration_date = EXCLUDED.registration_date,
                        payment_status = EXCLUDED.payment_status,
                        amount_paid = EXCLUDED.amount_paid,
                        fetched_date = NOW()
                """, (
                    participant.event_id,
                    participant.provider_participant_id,
                    participant.bib_number,
                    participant.first_name,
                    participant.last_name,
                    participant.email,
                    participant.phone,
                    participant.date_of_birth,
                    participant.gender,
                    participant.country,
                    json.dumps(participant.emergency_contact) if participant.emergency_contact else None,
                    participant.team_name,
                    participant.division,
                    participant.registration_date,
                    participant.payment_status,
                    participant.amount_paid,
                    client_id[:10] + "...",
                    timing_partner_id
                ))
                
                participants_synced += 1
            
            # Record sync history
            cursor.execute("""
                INSERT INTO sync_history (
                    timing_partner_id, provider_id, event_id, sync_type, 
                    status, participants_synced, sync_time
                ) VALUES (%s, %s, %s, 'participants', 'completed', %s, NOW())
            """, (timing_partner_id, 5, event_id, participants_synced))  # 5 = Haku provider ID
            
            conn.commit()
            conn.close()
            
            self.stats['events_synced'] += 1
            self.stats['participants_synced'] += participants_synced
            
            logger.info(f"✅ Synced {participants_synced} participants for {event_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to sync event {event.get('event_id', 'unknown')}: {e}")
            self.stats['errors'] += 1
            return False
    
    def run_event_driven_sync(self):
        """Main event-driven sync loop"""
        logger.info("🚀 Starting Haku Event-Driven Sync Loop")
        
        # Track last discovery time
        last_discovery_time = datetime.min
        discovery_interval = timedelta(hours=12)  # Twice daily
        
        while self.running:
            try:
                current_time = datetime.now()
                current_hour = current_time.hour
                
                # Check if it's time for events discovery (6 AM or 6 PM)
                should_discover = False
                if current_hour in self.sync_config['events_discovery_hours']:
                    if current_time - last_discovery_time >= discovery_interval:
                        should_discover = True
                        last_discovery_time = current_time
                
                if should_discover:
                    logger.info(f"🔍 Time for Haku events discovery ({current_hour}:00)")
                    self.discover_events_and_races()
                
                # Get events that need syncing
                events_to_sync = self.get_events_for_sync_by_priority()
                self.stats['active_events'] = sum(len(events) for events in events_to_sync.values())
                
                if any(events_to_sync.values()):
                    total_events = sum(len(events) for events in events_to_sync.values())
                    logger.info(f"📊 {total_events} Haku events need syncing (H:{len(events_to_sync['high'])} M:{len(events_to_sync['medium'])} L:{len(events_to_sync['low'])})")
                    
                    # Process events by priority with limits
                    self.process_priority_events(events_to_sync)
                else:
                    logger.info("😴 No Haku events need syncing at this time")
                
                self.stats['cycles_completed'] += 1
                
                # Sleep for configured time between cycles
                time.sleep(self.sync_config['cycle_sleep_seconds'])
                
            except Exception as e:
                logger.error(f"❌ Error in Haku sync loop: {e}")
                self.stats['errors'] += 1
                time.sleep(60)  # Wait longer on error
    
    def start_scheduler(self):
        """Start the event-driven scheduler"""
        if self.running:
            logger.warning("⚠️  Haku scheduler is already running")
            return
        
        # Prevent concurrent execution
        if not self.prevent_concurrent_execution():
            return False
        
        logger.info("🚀 Starting Haku Event-Driven Sync Scheduler")
        logger.info("=" * 80)
        logger.info(f"📅 Events discovery: {self.sync_config['events_discovery_hours']} (hours)")
        logger.info(f"⏰ Sync frequencies:")
        logger.info(f"   • Outside 24h: {self.sync_config['outside_24h_frequency_minutes']} min")
        logger.info(f"   • Within 24h: {self.sync_config['within_24h_frequency_minutes']} min")
        logger.info(f"   • Within 4h: {self.sync_config['within_4h_frequency_minutes']} min")
        logger.info(f"   • Stop after: {self.sync_config['stop_after_start_hours']} hours past start")
        logger.info("=" * 80)
        
        self.running = True
        self.sync_thread = threading.Thread(target=self.run_event_driven_sync, daemon=True)
        self.sync_thread.start()
        
        logger.info("✅ Haku event-driven scheduler started successfully")
        return True
    
    def stop_scheduler(self):
        """Stop the event-driven scheduler"""
        logger.info("🛑 Stopping Haku Event-Driven Sync Scheduler")
        self.running = False
        
        if self.sync_thread:
            self.sync_thread.join(timeout=30)
        
        self.release_lock()
        logger.info("✅ Haku scheduler stopped")
    
    def get_status(self) -> Dict:
        """Get current scheduler status"""
        return {
            'running': self.running,
            'stats': self.stats,
            'config': self.sync_config,
            'active_events': self.get_events_for_sync_by_priority() if self.running else {}
        }

# Signal handler for graceful shutdown
class SignalHandler:
    def __init__(self):
        self.scheduler = None
    
    def __call__(self, signum, frame):
        logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
        if self.scheduler:
            self.scheduler.stop_scheduler()
        sys.exit(0)

signal_handler = SignalHandler()

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Haku Event-Driven Sync Scheduler')
    parser.add_argument('--discover-only', action='store_true', 
                       help='Run events discovery only (no continuous sync)')
    parser.add_argument('--test-frequencies', action='store_true',
                       help='Test sync frequency calculations')
    parser.add_argument('--status', action='store_true',
                       help='Show current sync status')
    
    args = parser.parse_args()
    
    # Create scheduler instance
    scheduler = HakuEventDrivenScheduler()
    
    # Set up signal handlers
    signal_handler.scheduler = scheduler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.discover_only:
        logger.info("🔍 Running Haku events discovery only")
        scheduler.discover_events_and_races()
        return 0
    
    if args.test_frequencies:
        logger.info("🧪 Testing sync frequency calculations")
        now = datetime.now()
        test_times = [
            ("2 days ahead", now + timedelta(days=2)),
            ("12 hours ahead", now + timedelta(hours=12)),
            ("2 hours ahead", now + timedelta(hours=2)),
            ("30 minutes ahead", now + timedelta(minutes=30)),
            ("10 minutes ago", now - timedelta(minutes=10)),
            ("2 hours ago", now - timedelta(hours=2))
        ]
        
        for label, test_time in test_times:
            freq = scheduler.calculate_sync_frequency(test_time, now)
            print(f"{label:20} -> {freq:3d} minutes (or stop if 0)")
        return 0
    
    if args.status:
        status = scheduler.get_status()
        print(json.dumps(status, indent=2, default=str))
        return 0
    
    logger.info("🚀 Starting Haku Event-Driven Sync Scheduler...")
    logger.info("=" * 60)
    
    # Start the scheduler
    success = scheduler.start_scheduler()
    
    if success:
        try:
            # Keep the main thread alive
            while scheduler.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Keyboard interrupt received")
        finally:
            scheduler.stop_scheduler()
    
    logger.info("✅ Haku scheduler shutdown complete")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 