#!/usr/bin/env python3
"""
RunSignUp Event-Driven Sync Scheduler

This scheduler implements sophisticated event-driven sync logic:
- Twice daily events/races discovery (if event doesn't exist, get all participants)
- Event-proximity based sync frequencies:
  * Outside 24 hours: Incremental sync every hour
  * Within 24 hours: Sync every 5 minutes  
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

from providers.runsignup_adapter import RunSignUpAdapter

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'runsignup_event_driven_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class EventDrivenSyncScheduler:
    """
    Event-driven sync scheduler for RunSignUp with priority-based processing
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
            'outside_24h_frequency_minutes': 60,  # Every hour
            'within_24h_frequency_minutes': 5,    # Every 5 minutes
            'within_4h_frequency_minutes': 1,     # Every minute
            'stop_after_start_hours': 1,          # Stop 1 hour after event start
            'rate_limit_delay': 1,                # Seconds between API calls
            
            # NEW: Priority-based processing limits
            'max_high_priority_per_cycle': 50,    # Process up to 50 high-priority events per cycle
            'max_medium_priority_per_cycle': 20,  # Process up to 20 medium-priority events per cycle  
            'max_low_priority_per_cycle': 10,     # Process up to 10 low-priority events per cycle
            'cycle_sleep_seconds': 10,            # Sleep between cycles (reduced from 30s)
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
        self.lock_file = '/tmp/runsignup_event_driven_scheduler.lock'
        
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
                    logger.error(f"❌ Scheduler already running (PID: {pid})")
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
    
    def get_timing_partners(self) -> List[Tuple[int, str, str, str]]:
        """Get timing partners with RunSignUp provider credentials"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT tp.timing_partner_id, tp.company_name, ppc.principal, ppc.secret
            FROM timing_partners tp
            JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
            WHERE ppc.provider_id = 2  -- RunSignUp provider
            ORDER BY tp.timing_partner_id
        """)
        
        partners = cursor.fetchall()
        conn.close()
        return partners
    
    def discover_events_and_races(self):
        """Discover new events and races from all timing partners"""
        logger.info("🔍 Starting events and races discovery")
        timing_partners = self.get_timing_partners()
        
        new_events_found = 0
        
        for timing_partner_id, company_name, principal, secret in timing_partners:
            try:
                logger.info(f"🏃 Discovering events for {company_name} (TP: {timing_partner_id})")
                
                # Create adapter
                credentials_dict = {'principal': principal, 'secret': secret}
                adapter = RunSignUpAdapter(credentials_dict, timing_partner_id)
                
                # Test authentication
                if not adapter.authenticate():
                    logger.error(f"❌ Authentication failed for {company_name}")
                    self.stats['errors'] += 1
                    continue
                
                # Get connection for database operations
                conn = self.get_connection()
                
                # Get events
                events = adapter.get_events()
                logger.info(f"📅 Found {len(events)} events for {company_name}")
                
                for event in events:
                    try:
                        if adapter.is_new_event(event.provider_event_id, conn):
                            # New event - store it and get all participants
                            logger.info(f"🆕 New event found: {event.name} (ID: {event.provider_event_id})")
                            adapter.store_event(event.to_dict(), conn)
                            new_events_found += 1
                            
                            # Get all races for this event
                            races = adapter.get_races(event.provider_event_id)
                            for race in races:
                                adapter.store_race(race.to_dict(), event.provider_event_id, conn)
                            
                            # Get all participants for new event (full sync)
                            for race in races:
                                participants = adapter.get_participants(race.race_id, event.provider_event_id)
                                for participant in participants:
                                    adapter.store_participant(participant.raw_data, race.race_id, event.provider_event_id, conn)
                            
                            # Record sync history for new event
                            self.record_event_sync(timing_partner_id, event.provider_event_id, 'full_sync', len(participants))
                        else:
                            # Existing event - will be handled by event-driven sync
                            pass
                            
                    except Exception as e:
                        logger.error(f"❌ Error processing event {event.provider_event_id}: {e}")
                        self.stats['errors'] += 1
                        continue
                
                conn.commit()
                conn.close()
                
                # Rate limiting between partners
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
                re.event_id,
                re.start_time,
                re.timing_partner_id,
                re.name as event_name,
                tp.company_name,
                ppc.principal,
                ppc.secret,
                COALESCE(MAX(sh.sync_time), re.created_at) as last_sync_time
            FROM runsignup_events re
            JOIN timing_partners tp ON re.timing_partner_id = tp.timing_partner_id
            JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
            LEFT JOIN sync_history sh ON re.event_id::text = sh.event_id 
                AND sh.timing_partner_id = re.timing_partner_id
                AND sh.status = 'completed'
            WHERE ppc.provider_id = 2
            AND re.start_time IS NOT NULL
            AND re.start_time > %s  -- Only future events or very recent past
            GROUP BY re.event_id, re.start_time, re.timing_partner_id, re.name, 
                     tp.company_name, ppc.principal, ppc.secret, re.created_at
            ORDER BY re.start_time ASC
        """, (now - timedelta(hours=self.sync_config['stop_after_start_hours']),))
        
        # Organize events by priority
        priority_events = {
            'high': [],     # Within 4 hours (1-min frequency)
            'medium': [],   # Within 24 hours (5-min frequency)  
            'low': []       # Outside 24 hours (60-min frequency)
        }
        
        for row in cursor.fetchall():
            event_id, start_time, timing_partner_id, event_name, company_name, principal, secret, last_sync_time = row
            
            # Calculate sync frequency and priority
            frequency_minutes = self.calculate_sync_frequency(start_time, now)
            
            if frequency_minutes > 0:  # 0 means stop syncing
                # Check if it's time to sync
                time_since_sync = now - last_sync_time
                
                if time_since_sync >= timedelta(minutes=frequency_minutes):
                    event_info = {
                        'event_id': event_id,
                        'event_name': event_name,
                        'start_time': start_time,
                        'timing_partner_id': timing_partner_id,
                        'company_name': company_name,
                        'principal': principal,
                        'secret': secret,
                        'last_sync_time': last_sync_time,
                        'frequency_minutes': frequency_minutes,
                        'time_until_start': start_time - now,
                        'time_since_sync': time_since_sync
                    }
                    
                    # Assign priority based on frequency
                    if frequency_minutes == 1:
                        priority_events['high'].append(event_info)
                    elif frequency_minutes == 5:
                        priority_events['medium'].append(event_info)
                    else:  # 60 minutes
                        priority_events['low'].append(event_info)
        
        conn.close()
        
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
        
        # Within 24 hours: Every 5 minutes
        elif time_until_start <= timedelta(hours=24):
            return self.sync_config['within_24h_frequency_minutes']
        
        # Outside 24 hours: Every hour
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
            
            if events_to_process:
                logger.info(f"{emoji} Processing {len(events_to_process)} {priority_name}-priority events (skipping {events_skipped})")
                
                for event_info in events_to_process:
                    if not self.running:
                        break
                        
                    sync_result = self.sync_event_participants(event_info)
                    self.stats['participants_synced'] += sync_result['participants_synced']
                    
                    if sync_result['status'] == 'failed':
                        self.stats['errors'] += 1
                    else:
                        self.stats['events_synced'] += 1
                    
                    # Update priority stats
                    self.stats['priority_stats'][priority_name]['processed'] += 1
                    
                    # Small delay between events to prevent overwhelming
                    time.sleep(0.5)
            
            # Update skipped stats
            if events_skipped > 0:
                self.stats['priority_stats'][priority_name]['skipped'] += events_skipped
                logger.info(f"⏭️  Skipped {events_skipped} {priority_name}-priority events (will retry next cycle)")

    def sync_event_participants(self, event_info: Dict) -> Dict:
        """Sync participants for a specific event using incremental sync"""
        event_id = event_info['event_id']
        timing_partner_id = event_info['timing_partner_id']
        
        logger.info(f"🔄 Syncing event {event_info['event_name']} (ID: {event_id})")
        logger.info(f"   ⏰ Start time: {event_info['start_time']}")
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
            adapter = RunSignUpAdapter(credentials_dict, timing_partner_id)
            
            # Test authentication
            if not adapter.authenticate():
                raise Exception("Authentication failed")
            
            # Get race_id for this event
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT race_id FROM runsignup_events 
                WHERE event_id = %s AND timing_partner_id = %s
            """, (event_id, timing_partner_id))
            
            race_result = cursor.fetchone()
            if not race_result:
                raise Exception(f"Race ID not found for event {event_id}")
            
            race_id = race_result[0]
            
            # Incremental sync - only get participants modified since last sync
            last_sync_time = event_info['last_sync_time']
            participants = adapter.get_participants(
                race_id, 
                str(event_id),
                last_modified_since=last_sync_time
            )
            
            logger.info(f"👥 Found {len(participants)} modified participants since {last_sync_time}")
            
            # Store updated participants
            for participant in participants:
                try:
                    adapter.store_participant(participant.raw_data, race_id, event_id, conn)
                    sync_result['participants_synced'] += 1
                except Exception as e:
                    logger.error(f"❌ Error storing participant: {e}")
                    sync_result['errors'].append(f"Participant error: {e}")
            
            conn.commit()
            conn.close()
            
            sync_result['status'] = 'completed'
            
            # Record sync history
            self.record_event_sync(timing_partner_id, event_id, 'incremental_sync', 
                                 sync_result['participants_synced'])
            
            logger.info(f"✅ Event sync complete - {sync_result['participants_synced']} participants updated")
            
            return sync_result
            
        except Exception as e:
            logger.error(f"❌ Error syncing event {event_id}: {e}")
            sync_result['status'] = 'failed'
            sync_result['errors'].append(f"Fatal error: {e}")
            return sync_result
    
    def record_event_sync(self, timing_partner_id: int, event_id: str, sync_type: str, 
                         participants_count: int):
        """Record sync operation in sync_history table"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO sync_history (
                    timing_partner_id, provider_id, event_id, operation_type, 
                    sync_time, status, num_of_synced_records, entries_success
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                timing_partner_id,
                2,  # Provider ID for RunSignUp
                str(event_id),  # Ensure event_id is stored as text
                sync_type,
                datetime.now(),
                'completed',
                participants_count,
                participants_count
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record sync history: {e}")
    
    def run_event_driven_sync(self):
        """Main event-driven sync loop"""
        logger.info("🚀 Starting Event-Driven Sync Loop")
        
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
                    logger.info(f"🔍 Time for events discovery ({current_hour}:00)")
                    self.discover_events_and_races()
                
                # Get events that need syncing
                events_to_sync = self.get_events_for_sync_by_priority()
                self.stats['active_events'] = sum(len(events) for events in events_to_sync.values())
                
                if any(events_to_sync.values()):
                    total_events = sum(len(events) for events in events_to_sync.values())
                    logger.info(f"📊 {total_events} events need syncing (H:{len(events_to_sync['high'])} M:{len(events_to_sync['medium'])} L:{len(events_to_sync['low'])})")
                    
                    # Process events by priority with limits
                    self.process_priority_events(events_to_sync)
                else:
                    logger.info("😴 No events need syncing at this time")
                
                self.stats['cycles_completed'] += 1
                
                # Sleep for reduced time between cycles
                time.sleep(self.sync_config['cycle_sleep_seconds'])
                
            except Exception as e:
                logger.error(f"❌ Error in sync loop: {e}")
                self.stats['errors'] += 1
                time.sleep(60)  # Wait longer on error
    
    def start_scheduler(self):
        """Start the event-driven scheduler"""
        if self.running:
            logger.warning("⚠️  Scheduler is already running")
            return
        
        # Prevent concurrent execution
        if not self.prevent_concurrent_execution():
            return False
        
        logger.info("🚀 Starting Event-Driven Sync Scheduler")
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
        
        logger.info("✅ Event-driven scheduler started successfully")
        return True
    
    def stop_scheduler(self):
        """Stop the event-driven scheduler"""
        logger.info("🛑 Stopping Event-Driven Sync Scheduler")
        self.running = False
        
        if self.sync_thread:
            self.sync_thread.join(timeout=30)
        
        self.release_lock()
        logger.info("✅ Scheduler stopped")
    
    def get_status(self) -> Dict:
        """Get current scheduler status"""
        return {
            'running': self.running,
            'stats': self.stats,
            'config': self.sync_config,
            'active_events': self.get_events_for_sync_by_priority() if self.running else {}
        }

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"📡 Received signal {signum}, shutting down gracefully...")
    if hasattr(signal_handler, 'scheduler'):
        signal_handler.scheduler.stop_scheduler()
    sys.exit(0)

def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RunSignUp Event-Driven Sync Scheduler')
    parser.add_argument('--discover-only', action='store_true', 
                       help='Run events discovery only (no continuous sync)')
    parser.add_argument('--test-frequencies', action='store_true',
                       help='Test sync frequency calculations')
    parser.add_argument('--status', action='store_true',
                       help='Show current sync status')
    
    args = parser.parse_args()
    
    # Create scheduler instance
    scheduler = EventDrivenSyncScheduler()
    
    # Set up signal handlers
    signal_handler.scheduler = scheduler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    if args.discover_only:
        logger.info("🔍 Running events discovery only")
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
    
    # Start the scheduler
    try:
        if scheduler.start_scheduler():
            logger.info("🔄 Scheduler running - Press Ctrl+C to stop")
            
            # Keep main thread alive
            while scheduler.running:
                time.sleep(1)
        else:
            logger.error("❌ Failed to start scheduler")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n⏸️  Scheduler interrupted by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        return 1
    finally:
        scheduler.stop_scheduler()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
