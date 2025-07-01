#!/usr/bin/env python3
"""
Provider Sync Engine for Project88Hub
Handles intelligent sync scheduling based on event start times
"""

import psycopg2
import psycopg2.extras
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import schedule
import time
import threading
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/project88/provider_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ProviderSyncEngine')

@dataclass
class EventSyncConfig:
    """Configuration for syncing a specific event"""
    event_id: str
    provider_id: int
    provider_name: str
    timing_partner_id: int
    event_start_time: datetime
    last_sync_time: Optional[datetime]
    is_full_sync_completed: bool
    sync_frequency_minutes: int
    
    def get_sync_frequency(self) -> int:
        """Calculate sync frequency based on time until event start"""
        now = datetime.now()
        time_until_start = self.event_start_time - now
        time_since_start = now - self.event_start_time
        
        # Stop syncing 1 hour after event start
        if time_since_start > timedelta(hours=1):
            return 0  # No more syncing
        
        # Frequency based on proximity to start time
        if time_until_start > timedelta(hours=24):
            return 60  # Every hour outside 24 hours
        elif time_until_start > timedelta(hours=4):
            return 15  # Every 15 minutes within 24 hours
        else:
            return 1   # Every minute within 4 hours (or after start until +1hr)

class DatabaseManager:
    """Database connection and operations manager"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.connection = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                self.connection_string,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            self.connection.autocommit = True
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
            
    def get_active_events_for_sync(self) -> List[EventSyncConfig]:
        """Get events that need syncing based on their start times"""
        cursor = self.connection.cursor()
        
        query = """
        WITH event_sync_status AS (
            SELECT DISTINCT
                ue.source_provider,
                ue.timing_partner_id,
                ue.event_id,
                ue.event_name,
                ue.event_date,
                p.provider_id,
                p.name as provider_name,
                sh.sync_time as last_sync_time,
                CASE WHEN sh.sync_time IS NOT NULL THEN true ELSE false END as has_synced
            FROM unified_events ue
            JOIN providers p ON p.name = ue.source_provider
            JOIN partner_provider_credentials ppc ON ppc.provider_id = p.provider_id 
                AND ppc.timing_partner_id = ue.timing_partner_id
            LEFT JOIN LATERAL (
                SELECT sync_time 
                FROM sync_history sh2 
                WHERE sh2.timing_partner_id = ue.timing_partner_id 
                    AND sh2.provider_id = p.provider_id
                    AND sh2.event_id = ue.event_id
                    AND sh2.operation_type = 'participants'
                    AND sh2.status = 'success'
                ORDER BY sh2.sync_time DESC 
                LIMIT 1
            ) sh ON true
        )
        SELECT *
        FROM event_sync_status
        WHERE event_date > NOW() - INTERVAL '1 hour'  -- Events not more than 1hr past start
            AND event_date < NOW() + INTERVAL '7 days'  -- Events within next week
        ORDER BY event_date ASC
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        events = []
        for row in results:
            config = EventSyncConfig(
                event_id=row['event_id'],
                provider_id=row['provider_id'],
                provider_name=row['provider_name'],
                timing_partner_id=row['timing_partner_id'],
                event_start_time=row['event_date'],
                last_sync_time=row['last_sync_time'],
                is_full_sync_completed=row['has_synced'],
                sync_frequency_minutes=0  # Will be calculated
            )
            config.sync_frequency_minutes = config.get_sync_frequency()
            events.append(config)
            
        return events
    
    def get_provider_credentials(self, timing_partner_id: int, provider_id: int) -> Dict:
        """Get credentials for a specific provider"""
        cursor = self.connection.cursor()
        
        query = """
        SELECT ppc.*, p.name as provider_name, p.api_base_url
        FROM partner_provider_credentials ppc
        JOIN providers p ON p.provider_id = ppc.provider_id
        WHERE ppc.timing_partner_id = %s AND ppc.provider_id = %s
        """
        
        cursor.execute(query, (timing_partner_id, provider_id))
        result = cursor.fetchone()
        
        if not result:
            raise ValueError(f"No credentials found for timing_partner_id={timing_partner_id}, provider_id={provider_id}")
            
        return dict(result)
    
    def queue_sync_job(self, event_config: EventSyncConfig, operation_type: str = 'participants', 
                       priority: int = 5) -> int:
        """Queue a sync job"""
        cursor = self.connection.cursor()
        
        # Check if a similar job is already pending
        check_query = """
        SELECT sync_queue_id FROM sync_queue 
        WHERE timing_partner_id = %s 
            AND provider_id = %s 
            AND event_id = %s 
            AND operation_type = %s 
            AND status = 'pending'
        """
        cursor.execute(check_query, (
            event_config.timing_partner_id,
            event_config.provider_id, 
            event_config.event_id,
            operation_type
        ))
        
        if cursor.fetchone():
            logger.debug(f"Sync job already queued for {event_config.provider_name} event {event_config.event_id}")
            return None
        
        # Queue new job
        insert_query = """
        INSERT INTO sync_queue (
            timing_partner_id, provider_id, event_id, operation_type,
            sync_direction, priority, status, scheduled_time, payload
        ) VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW(), %s)
        RETURNING sync_queue_id
        """
        
        payload = {
            'event_name': 'Event sync',
            'is_incremental': event_config.is_full_sync_completed,
            'last_sync_time': event_config.last_sync_time.isoformat() if event_config.last_sync_time else None
        }
        
        cursor.execute(insert_query, (
            event_config.timing_partner_id,
            event_config.provider_id,
            event_config.event_id,
            operation_type,
            'pull',
            priority,
            json.dumps(payload)
        ))
        
        job_id = cursor.fetchone()['sync_queue_id']
        logger.info(f"Queued sync job {job_id} for {event_config.provider_name} event {event_config.event_id}")
        return job_id

class ProviderSyncScheduler:
    """Main scheduler for provider sync operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.active_schedules = {}  # Track scheduled jobs per event
        self.running = False
        
    def start_scheduler(self):
        """Start the sync scheduler"""
        logger.info("Starting Provider Sync Scheduler")
        self.running = True
        
        # Schedule the main sync orchestrator to run every minute
        schedule.every(1).minutes.do(self.orchestrate_syncs)
        
        # Run scheduler in background thread
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Sync scheduler started in background thread")
        
    def stop_scheduler(self):
        """Stop the sync scheduler"""
        logger.info("Stopping Provider Sync Scheduler")
        self.running = False
        schedule.clear()
        
    def orchestrate_syncs(self):
        """Main orchestration logic - runs every minute"""
        try:
            # Get all events that need syncing
            events = self.db_manager.get_active_events_for_sync()
            
            for event_config in events:
                self.schedule_event_sync(event_config)
                
        except Exception as e:
            logger.error(f"Error in sync orchestration: {e}")
    
    def schedule_event_sync(self, event_config: EventSyncConfig):
        """Schedule sync for a specific event based on its timing"""
        event_key = f"{event_config.timing_partner_id}_{event_config.provider_id}_{event_config.event_id}"
        
        # Skip if no syncing needed (past 1hr after start)
        if event_config.sync_frequency_minutes == 0:
            if event_key in self.active_schedules:
                logger.info(f"Event {event_config.event_id} past sync window, removing from schedule")
                del self.active_schedules[event_key]
            return
        
        # Check if we need to sync now
        should_sync_now = False
        
        if not event_config.is_full_sync_completed:
            # Always do full sync first
            should_sync_now = True
            logger.info(f"Scheduling full sync for {event_config.provider_name} event {event_config.event_id}")
        else:
            # Check if enough time has passed for incremental sync
            if event_config.last_sync_time:
                time_since_sync = datetime.now() - event_config.last_sync_time
                if time_since_sync >= timedelta(minutes=event_config.sync_frequency_minutes):
                    should_sync_now = True
            else:
                should_sync_now = True
        
        if should_sync_now:
            # Determine priority based on how close to event start
            now = datetime.now()
            time_until_start = event_config.event_start_time - now
            
            if time_until_start <= timedelta(hours=1):
                priority = 1  # Highest priority - very close to start
            elif time_until_start <= timedelta(hours=4):
                priority = 2  # High priority
            elif time_until_start <= timedelta(hours=24):
                priority = 3  # Medium priority
            else:
                priority = 5  # Normal priority
            
            # Queue the sync job
            self.db_manager.queue_sync_job(event_config, 'participants', priority)
            
            # Also queue events sync if this is the first sync
            if not event_config.is_full_sync_completed:
                self.db_manager.queue_sync_job(event_config, 'events', priority)
        
        # Track this event
        self.active_schedules[event_key] = {
            'last_scheduled': datetime.now(),
            'frequency': event_config.sync_frequency_minutes,
            'next_sync': datetime.now() + timedelta(minutes=event_config.sync_frequency_minutes)
        }

class ProviderSyncEngine:
    """Main engine for provider synchronization"""
    
    def __init__(self, db_connection_string: str):
        self.db_manager = DatabaseManager(db_connection_string)
        self.scheduler = ProviderSyncScheduler(self.db_manager)
        
    def start(self):
        """Start the sync engine"""
        try:
            logger.info("Starting Provider Sync Engine")
            self.db_manager.connect()
            self.scheduler.start_scheduler()
            logger.info("Provider Sync Engine started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start sync engine: {e}")
            raise
    
    def stop(self):
        """Stop the sync engine"""
        logger.info("Stopping Provider Sync Engine")
        self.scheduler.stop_scheduler()
        if self.db_manager.connection:
            self.db_manager.connection.close()
    
    def manual_sync(self, timing_partner_id: int, provider_name: str, event_id: str = None):
        """Trigger manual sync for specific timing partner/provider"""
        try:
            # Get provider ID
            cursor = self.db_manager.connection.cursor()
            cursor.execute("SELECT provider_id FROM providers WHERE name = %s", (provider_name,))
            result = cursor.fetchone()
            
            if not result:
                raise ValueError(f"Provider '{provider_name}' not found")
            
            provider_id = result['provider_id']
            
            if event_id:
                # Sync specific event
                config = EventSyncConfig(
                    event_id=event_id,
                    provider_id=provider_id,
                    provider_name=provider_name,
                    timing_partner_id=timing_partner_id,
                    event_start_time=datetime.now(),  # Will be updated from DB
                    last_sync_time=None,
                    is_full_sync_completed=False,
                    sync_frequency_minutes=1
                )
                self.db_manager.queue_sync_job(config, 'participants', priority=1)
                self.db_manager.queue_sync_job(config, 'events', priority=1)
                logger.info(f"Manual sync queued for event {event_id}")
            else:
                # Sync all events for this timing partner/provider
                events = self.db_manager.get_active_events_for_sync()
                queued_count = 0
                
                for event_config in events:
                    if (event_config.timing_partner_id == timing_partner_id and 
                        event_config.provider_id == provider_id):
                        self.db_manager.queue_sync_job(event_config, 'participants', priority=1)
                        self.db_manager.queue_sync_job(event_config, 'events', priority=1)
                        queued_count += 1
                
                logger.info(f"Manual sync queued for {queued_count} events")
                
        except Exception as e:
            logger.error(f"Manual sync failed: {e}")
            raise

def main():
    """Main entry point for running the sync engine"""
    
    # Database connection string - adjust for your environment
    DB_CONNECTION = (
        "host=localhost "
        "dbname=project88_myappdb "
        "user=project88_myappuser "
        "password=your_password"
    )
    
    try:
        # Create and start sync engine
        engine = ProviderSyncEngine(DB_CONNECTION)
        engine.start()
        
        logger.info("Provider Sync Engine running. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            
    except Exception as e:
        logger.error(f"Critical error: {e}")
        
    finally:
        engine.stop()
        logger.info("Provider Sync Engine stopped")

if __name__ == "__main__":
    main() 