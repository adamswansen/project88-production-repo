#!/usr/bin/env python3
"""
Sync Worker for Project88Hub Provider Integrations
Processes sync jobs from the queue and stores data in the database
"""

import psycopg2
import psycopg2.extras
import logging
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from providers.runsignup_adapter import RunSignUpAdapter
from providers.raceroster_adapter import RaceRosterAdapter
from providers.haku_adapter import HakuAdapter
from providers.letsdothis_adapter import LetsDoThisAdapter
from providers.base_adapter import BaseProviderAdapter, ProviderEvent, ProviderParticipant, SyncResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/project88/sync_worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SyncWorker')

class SyncWorker:
    """Worker that processes sync jobs from the queue"""
    
    def __init__(self, db_connection_string: str, worker_id: str = "worker-1"):
        self.db_connection_string = db_connection_string
        self.worker_id = worker_id
        self.connection = None
        self.running = False
        
        # Provider adapter mapping
        self.provider_adapters = {
            'RunSignUp': RunSignUpAdapter,
            'Race Roster': RaceRosterAdapter,
            'Haku': HakuAdapter,
            'Let\'s Do This': LetsDoThisAdapter
        }
        
    def connect_db(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                self.db_connection_string,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            self.connection.autocommit = True
            logger.info(f"Worker {self.worker_id} database connection established")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} database connection failed: {e}")
            raise
    
    def start(self):
        """Start the sync worker"""
        logger.info(f"Starting sync worker {self.worker_id}")
        self.running = True
        self.connect_db()
        
        # Start worker loop in a thread
        worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        worker_thread.start()
        
    def stop(self):
        """Stop the sync worker"""
        logger.info(f"Stopping sync worker {self.worker_id}")
        self.running = False
        if self.connection:
            self.connection.close()
    
    def _worker_loop(self):
        """Main worker loop"""
        while self.running:
            try:
                # Get pending jobs
                jobs = self._get_pending_jobs(limit=5)
                
                if not jobs:
                    time.sleep(10)  # Wait 10 seconds if no jobs
                    continue
                
                # Process each job
                for job in jobs:
                    self._process_job(job)
                
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error in main loop: {e}")
                time.sleep(30)  # Wait before retrying
    
    def _get_pending_jobs(self, limit: int = 5) -> List[Dict]:
        """Get pending sync jobs from the queue"""
        cursor = self.connection.cursor()
        
        query = """
        SELECT sq.*, p.name as provider_name, p.api_base_url
        FROM sync_queue sq
        JOIN providers p ON p.provider_id = sq.provider_id
        WHERE sq.status = 'pending'
            AND (sq.scheduled_time <= NOW() OR sq.scheduled_time IS NULL)
        ORDER BY sq.priority ASC, sq.scheduled_time ASC
        LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        return cursor.fetchall()
    
    def _process_job(self, job: Dict):
        """Process a single sync job"""
        job_id = job['sync_queue_id']
        
        try:
            logger.info(f"Worker {self.worker_id} processing job {job_id}: {job['provider_name']} {job['operation_type']}")
            
            # Update job status to running
            self._update_job_status(job_id, 'running')
            
            # Get provider credentials
            credentials = self._get_provider_credentials(job['timing_partner_id'], job['provider_id'])
            
            # Create provider adapter
            adapter = self._create_provider_adapter(job['provider_name'], credentials, job['timing_partner_id'])
            
            # Process based on operation type
            if job['operation_type'] == 'events':
                result = self._sync_events(adapter, job)
            elif job['operation_type'] == 'participants':
                result = self._sync_participants(adapter, job)
            else:
                raise ValueError(f"Unknown operation type: {job['operation_type']}")
            
            # Record success
            self._record_sync_history(job, result)
            self._update_job_status(job_id, 'completed')
            
            logger.info(f"Worker {self.worker_id} completed job {job_id}: {result.processed_records}/{result.total_records} records")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Worker {self.worker_id} failed job {job_id}: {error_msg}")
            
            # Record failure
            self._record_sync_failure(job, error_msg)
            self._handle_job_failure(job, error_msg)
    
    def _create_provider_adapter(self, provider_name: str, credentials: Dict, timing_partner_id: int) -> BaseProviderAdapter:
        """Create and configure provider adapter"""
        adapter_class = self.provider_adapters.get(provider_name)
        
        if not adapter_class:
            raise ValueError(f"No adapter found for provider: {provider_name}")
        
        # Create adapter with database storage methods
        adapter = adapter_class(credentials, timing_partner_id)
        
        # Inject database storage methods
        adapter._store_event = lambda event: self._store_event(event, provider_name, timing_partner_id, credentials)
        adapter._store_participant = lambda participant: self._store_participant(participant, provider_name, timing_partner_id, credentials)
        
        return adapter
    
    def _sync_events(self, adapter: BaseProviderAdapter, job: Dict) -> SyncResult:
        """Sync events using provider adapter"""
        payload = json.loads(job.get('payload', '{}'))
        last_modified_since = None
        
        if payload.get('is_incremental') and payload.get('last_sync_time'):
            last_modified_since = datetime.fromisoformat(payload['last_sync_time'])
        
        return adapter.sync_events(last_modified_since)
    
    def _sync_participants(self, adapter: BaseProviderAdapter, job: Dict) -> SyncResult:
        """Sync participants using provider adapter"""
        payload = json.loads(job.get('payload', '{}'))
        last_modified_since = None
        
        if payload.get('is_incremental') and payload.get('last_sync_time'):
            last_modified_since = datetime.fromisoformat(payload['last_sync_time'])
        
        return adapter.sync_participants(job['event_id'], last_modified_since)
    
    def _store_event(self, event: ProviderEvent, provider_name: str, timing_partner_id: int, credentials: Dict):
        """Store event in appropriate provider table"""
        cursor = self.connection.cursor()
        
        try:
            if provider_name == 'RunSignUp':
                self._store_runsignup_event(cursor, event, timing_partner_id, credentials)
            elif provider_name == 'Race Roster':
                self._store_raceroster_event(cursor, event, timing_partner_id, credentials)
            elif provider_name == 'Haku':
                self._store_haku_event(cursor, event, timing_partner_id, credentials)
            elif provider_name == 'Let\'s Do This':
                self._store_letsdothis_event(cursor, event, timing_partner_id, credentials)
            else:
                raise ValueError(f"Unknown provider: {provider_name}")
                
        except Exception as e:
            logger.error(f"Failed to store event {event.provider_event_id} for {provider_name}: {e}")
            raise
    
    def _store_participant(self, participant: ProviderParticipant, provider_name: str, timing_partner_id: int, credentials: Dict):
        """Store participant in appropriate provider table"""
        cursor = self.connection.cursor()
        
        try:
            if provider_name == 'RunSignUp':
                self._store_runsignup_participant(cursor, participant, timing_partner_id, credentials)
            elif provider_name == 'Race Roster':
                self._store_raceroster_participant(cursor, participant, timing_partner_id, credentials)
            elif provider_name == 'Haku':
                self._store_haku_participant(cursor, participant, timing_partner_id, credentials)
            elif provider_name == 'Let\'s Do This':
                self._store_letsdothis_participant(cursor, participant, timing_partner_id, credentials)
            else:
                raise ValueError(f"Unknown provider: {provider_name}")
                
        except Exception as e:
            logger.error(f"Failed to store participant {participant.provider_participant_id} for {provider_name}: {e}")
            raise
    
    def _store_runsignup_event(self, cursor, event: ProviderEvent, timing_partner_id: int, credentials: Dict):
        """Store RunSignUp event"""
        insert_query = """
        INSERT INTO runsignup_events (
            event_id, name, details, start_time, end_time, 
            event_type, distance, fetched_date, credentials_used, timing_partner_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        ON CONFLICT (event_id) DO UPDATE SET
            name = EXCLUDED.name,
            details = EXCLUDED.details,
            start_time = EXCLUDED.start_time,
            end_time = EXCLUDED.end_time,
            event_type = EXCLUDED.event_type,
            distance = EXCLUDED.distance,
            fetched_date = NOW()
        """
        
        cursor.execute(insert_query, (
            event.provider_event_id,
            event.event_name,
            event.event_description,
            event.event_date,
            event.event_end_date,
            event.event_type,
            event.distance,
            credentials.get('principal', ''),
            timing_partner_id
        ))
    
    def _store_raceroster_event(self, cursor, event: ProviderEvent, timing_partner_id: int, credentials: Dict):
        """Store Race Roster event"""
        insert_query = """
        INSERT INTO raceroster_events (
            event_id, name, description, start_date, end_date, 
            location_name, address, event_type, distance, 
            max_participants, registration_fee, currency, status,
            fetched_date, credentials_used, timing_partner_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        ON CONFLICT (event_id) DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            location_name = EXCLUDED.location_name,
            address = EXCLUDED.address,
            event_type = EXCLUDED.event_type,
            distance = EXCLUDED.distance,
            max_participants = EXCLUDED.max_participants,
            registration_fee = EXCLUDED.registration_fee,
            currency = EXCLUDED.currency,
            status = EXCLUDED.status,
            fetched_date = NOW()
        """
        
        address_json = json.dumps({
            'city': event.location_city,
            'state': event.location_state,
            'name': event.location_name
        }) if event.location_city or event.location_state else None
        
        cursor.execute(insert_query, (
            event.provider_event_id,
            event.event_name,
            event.event_description,
            event.event_date,
            event.event_end_date,
            event.location_name,
            address_json,
            event.event_type,
            event.distance,
            event.max_participants,
            event.registration_fee,
            event.currency,
            event.status,
            credentials.get('principal', ''),
            timing_partner_id
        ))
    
    def _store_haku_event(self, cursor, event: ProviderEvent, timing_partner_id: int, credentials: Dict):
        """Store Haku event"""
        insert_query = """
        INSERT INTO haku_events (
            event_id, event_name, event_description, start_date, end_date,
            location, event_type, distance, registration_limit,
            registration_fee, currency, status, fetched_date, 
            credentials_used, timing_partner_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        ON CONFLICT (event_id) DO UPDATE SET
            event_name = EXCLUDED.event_name,
            event_description = EXCLUDED.event_description,
            start_date = EXCLUDED.start_date,
            end_date = EXCLUDED.end_date,
            location = EXCLUDED.location,
            event_type = EXCLUDED.event_type,
            distance = EXCLUDED.distance,
            registration_limit = EXCLUDED.registration_limit,
            registration_fee = EXCLUDED.registration_fee,
            currency = EXCLUDED.currency,
            status = EXCLUDED.status,
            fetched_date = NOW()
        """
        
        location_str = f"{event.location_city}, {event.location_state}" if event.location_city and event.location_state else event.location_name
        
        cursor.execute(insert_query, (
            event.provider_event_id,
            event.event_name,
            event.event_description,
            event.event_date,
            event.event_end_date,
            location_str,
            event.event_type,
            str(event.distance) if event.distance else None,
            event.max_participants,
            event.registration_fee,
            event.currency,
            event.status,
            credentials.get('principal', ''),
            timing_partner_id
        ))
    
    def _store_letsdothis_event(self, cursor, event: ProviderEvent, timing_partner_id: int, credentials: Dict):
        """Store Let's Do This event (placeholder - need to create table)"""
        # Note: Let's Do This table would need to be created in the schema
        logger.debug(f"Would store Let's Do This event: {event.provider_event_id}")
    
    def _store_runsignup_participant(self, cursor, participant: ProviderParticipant, timing_partner_id: int, credentials: Dict):
        """Store RunSignUp participant"""
        insert_query = """
        INSERT INTO runsignup_participants (
            event_id, registration_id, first_name, last_name, email,
            phone, dob, gender, age, bib_num, address, team_name,
            registration_date, payment_status, amount_paid,
            fetched_date, credentials_used, timing_partner_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        ON CONFLICT (registration_id) DO UPDATE SET
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            email = EXCLUDED.email,
            phone = EXCLUDED.phone,
            dob = EXCLUDED.dob,
            gender = EXCLUDED.gender,
            age = EXCLUDED.age,
            bib_num = EXCLUDED.bib_num,
            address = EXCLUDED.address,
            team_name = EXCLUDED.team_name,
            registration_date = EXCLUDED.registration_date,
            payment_status = EXCLUDED.payment_status,
            amount_paid = EXCLUDED.amount_paid,
            fetched_date = NOW()
        """
        
        address_json = json.dumps({
            'city': participant.city,
            'state': participant.state,
            'country': participant.country
        }) if participant.city or participant.state else None
        
        cursor.execute(insert_query, (
            participant.event_id,
            participant.provider_participant_id,
            participant.first_name,
            participant.last_name,
            participant.email,
            participant.phone,
            participant.date_of_birth,
            participant.gender,
            participant.age,
            participant.bib_number,
            address_json,
            participant.team_name,
            participant.registration_date,
            participant.payment_status,
            participant.amount_paid,
            credentials.get('principal', ''),
            timing_partner_id
        ))
    
    def _store_raceroster_participant(self, cursor, participant: ProviderParticipant, timing_partner_id: int, credentials: Dict):
        """Store Race Roster participant"""
        insert_query = """
        INSERT INTO raceroster_participants (
            event_id, registration_id, bib_number, first_name, last_name,
            email, phone, date_of_birth, gender, address, emergency_contact,
            team_name, division, registration_date, registration_status,
            payment_status, amount_paid, fetched_date, credentials_used, timing_partner_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        ON CONFLICT (registration_id) DO UPDATE SET
            bib_number = EXCLUDED.bib_number,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            email = EXCLUDED.email,
            phone = EXCLUDED.phone,
            date_of_birth = EXCLUDED.date_of_birth,
            gender = EXCLUDED.gender,
            address = EXCLUDED.address,
            emergency_contact = EXCLUDED.emergency_contact,
            team_name = EXCLUDED.team_name,
            division = EXCLUDED.division,
            registration_date = EXCLUDED.registration_date,
            registration_status = EXCLUDED.registration_status,
            payment_status = EXCLUDED.payment_status,
            amount_paid = EXCLUDED.amount_paid,
            fetched_date = NOW()
        """
        
        address_json = json.dumps({
            'city': participant.city,
            'state': participant.state,
            'country': participant.country
        }) if participant.city or participant.state else None
        
        cursor.execute(insert_query, (
            participant.event_id,
            participant.provider_participant_id,
            participant.bib_number,
            participant.first_name,
            participant.last_name,
            participant.email,
            participant.phone,
            participant.date_of_birth,
            participant.gender,
            address_json,
            json.dumps(participant.emergency_contact) if participant.emergency_contact else None,
            participant.team_name,
            participant.division,
            participant.registration_date,
            participant.registration_status,
            participant.payment_status,
            participant.amount_paid,
            credentials.get('principal', ''),
            timing_partner_id
        ))
    
    def _store_haku_participant(self, cursor, participant: ProviderParticipant, timing_partner_id: int, credentials: Dict):
        """Store Haku participant"""
        insert_query = """
        INSERT INTO haku_participants (
            event_id, participant_id, bib_number, first_name, last_name,
            email, phone, date_of_birth, gender, emergency_contact,
            team_affiliation, category, registration_date, payment_status,
            amount_paid, fetched_date, credentials_used, timing_partner_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s)
        ON CONFLICT (participant_id) DO UPDATE SET
            bib_number = EXCLUDED.bib_number,
            first_name = EXCLUDED.first_name,
            last_name = EXCLUDED.last_name,
            email = EXCLUDED.email,
            phone = EXCLUDED.phone,
            date_of_birth = EXCLUDED.date_of_birth,
            gender = EXCLUDED.gender,
            emergency_contact = EXCLUDED.emergency_contact,
            team_affiliation = EXCLUDED.team_affiliation,
            category = EXCLUDED.category,
            registration_date = EXCLUDED.registration_date,
            payment_status = EXCLUDED.payment_status,
            amount_paid = EXCLUDED.amount_paid,
            fetched_date = NOW()
        """
        
        cursor.execute(insert_query, (
            participant.event_id,
            participant.provider_participant_id,
            participant.bib_number,
            participant.first_name,
            participant.last_name,
            participant.email,
            participant.phone,
            participant.date_of_birth,
            participant.gender,
            json.dumps(participant.emergency_contact) if participant.emergency_contact else None,
            participant.team_name,
            participant.division,
            participant.registration_date,
            participant.payment_status,
            participant.amount_paid,
            credentials.get('principal', ''),
            timing_partner_id
        ))
    
    def _store_letsdothis_participant(self, cursor, participant: ProviderParticipant, timing_partner_id: int, credentials: Dict):
        """Store Let's Do This participant (placeholder - need to create table)"""
        # Note: Let's Do This table would need to be created in the schema
        logger.debug(f"Would store Let's Do This participant: {participant.provider_participant_id}")
    
    def _get_provider_credentials(self, timing_partner_id: int, provider_id: int) -> Dict:
        """Get provider credentials"""
        cursor = self.connection.cursor()
        
        query = """
        SELECT ppc.*, p.name as provider_name
        FROM partner_provider_credentials ppc
        JOIN providers p ON p.provider_id = ppc.provider_id
        WHERE ppc.timing_partner_id = %s AND ppc.provider_id = %s
        """
        
        cursor.execute(query, (timing_partner_id, provider_id))
        result = cursor.fetchone()
        
        if not result:
            raise ValueError(f"No credentials found for timing_partner_id={timing_partner_id}, provider_id={provider_id}")
        
        return dict(result)
    
    def _update_job_status(self, job_id: int, status: str):
        """Update job status"""
        cursor = self.connection.cursor()
        
        update_fields = {"status": status}
        if status == 'running':
            update_fields["started_at"] = datetime.now()
        elif status in ['completed', 'failed']:
            update_fields["completed_at"] = datetime.now()
        
        set_clause = ", ".join([f"{k} = %s" for k in update_fields.keys()])
        query = f"UPDATE sync_queue SET {set_clause} WHERE sync_queue_id = %s"
        
        values = list(update_fields.values()) + [job_id]
        cursor.execute(query, values)
    
    def _record_sync_history(self, job: Dict, result: SyncResult):
        """Record successful sync in history"""
        cursor = self.connection.cursor()
        
        insert_query = """
        INSERT INTO sync_history (
            timing_partner_id, provider_id, event_id, operation_type,
            sync_direction, status, num_of_synced_records, entries_success,
            entries_failed, duration_seconds, data_snapshot
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        data_snapshot = {
            'total_records': result.total_records,
            'processed_records': result.processed_records,
            'errors': result.errors[:10]  # Store first 10 errors
        }
        
        cursor.execute(insert_query, (
            job['timing_partner_id'],
            job['provider_id'],
            job.get('event_id'),
            job['operation_type'],
            job.get('sync_direction', 'pull'),
            'success' if result.success else 'partial',
            result.processed_records,
            result.processed_records,
            result.error_count,
            int(result.duration_seconds),
            json.dumps(data_snapshot)
        ))
    
    def _record_sync_failure(self, job: Dict, error_message: str):
        """Record sync failure in history"""
        cursor = self.connection.cursor()
        
        insert_query = """
        INSERT INTO sync_history (
            timing_partner_id, provider_id, event_id, operation_type,
            sync_direction, status, num_of_synced_records, entries_success,
            entries_failed, error_details
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(insert_query, (
            job['timing_partner_id'],
            job['provider_id'],
            job.get('event_id'),
            job['operation_type'],
            job.get('sync_direction', 'pull'),
            'failed',
            0,
            0,
            1,
            json.dumps({'error': error_message})
        ))
    
    def _handle_job_failure(self, job: Dict, error_message: str):
        """Handle job failure with retry logic"""
        job_id = job['sync_queue_id']
        retry_count = job.get('retry_count', 0)
        max_retries = job.get('max_retries', 3)
        
        if retry_count < max_retries:
            # Schedule retry with exponential backoff
            delay_minutes = 2 ** retry_count  # 2, 4, 8 minutes
            retry_time = datetime.now() + timedelta(minutes=delay_minutes)
            
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE sync_queue 
                SET status = 'pending', 
                    retry_count = %s, 
                    scheduled_time = %s
                WHERE sync_queue_id = %s
            """, (retry_count + 1, retry_time, job_id))
            
            logger.info(f"Scheduled retry {retry_count + 1}/{max_retries} for job {job_id} at {retry_time}")
        else:
            # Max retries exceeded
            self._update_job_status(job_id, 'failed')
            logger.error(f"Job {job_id} failed permanently after {max_retries} retries")

def main():
    """Main entry point for running sync workers"""
    
    # Database connection string
    DB_CONNECTION = (
        "host=localhost "
        "dbname=project88_myappdb "
        "user=project88_myappuser "
        "password=your_password"
    )
    
    try:
        # Create and start sync worker
        worker = SyncWorker(DB_CONNECTION, "worker-main")
        worker.start()
        
        logger.info("Sync worker running. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        try:
            while True:
                time.sleep(60)
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            
    except Exception as e:
        logger.error(f"Critical error: {e}")
        
    finally:
        worker.stop()
        logger.info("Sync worker stopped")

if __name__ == "__main__":
    main() 