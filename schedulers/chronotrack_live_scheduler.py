#!/usr/bin/env python3
"""
ChronoTrack Live Event-Driven Scheduler for Project88Hub
Implements sophisticated scheduling for ChronoTrack Live results collection

Results Collection Schedule:
- 5 minutes after event start: First results collection
- Next 5 hours: Every 90 seconds  
- Next 72 hours: Every hour
- After 72 hours: Stop collection

Follows established Haku/RunSignUp scheduler patterns
"""

import psycopg2
import psycopg2.extras
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from providers.chronotrack_live_adapter import ChronoTrackLiveAdapter

class ChronoTrackLiveScheduler:
    """Event-driven scheduler for ChronoTrack Live results collection"""
    
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'project88_myappdb', 
            'user': 'project88_myappuser',
            'password': 'puctuq-cefwyq-3boqRe',
            'port': 5432
        }
        
        # Results collection configuration
        self.results_config = {
            'initial_delay_minutes': 5,        # Wait 5 min after start before first collection
            'intensive_interval_seconds': 90,  # Every 90s for first 5 hours
            'intensive_duration_hours': 5,     # Intensive collection for 5 hours
            'standard_interval_hours': 1,      # Hourly after intensive period
            'max_collection_hours': 72,        # Stop after 72 hours total
            'max_concurrent_events': 10,       # Process max 10 events simultaneously
        }
        
        # Event discovery configuration  
        self.event_config = {
            'discovery_interval_hours': 6,     # Discover new events every 6 hours
            'sync_participants_interval_hours': 24,  # Sync participants daily
            'stop_after_finish_hours': 1,      # Stop syncing 1 hour after event ends
        }
        
        # Statistics tracking
        self.stats = {
            'events_discovered': 0,
            'events_synced': 0,
            'participants_synced': 0,
            'results_collected': 0,
            'api_calls': 0,
            'errors': 0,
            'last_discovery': None,
            'scheduler_start_time': datetime.now()
        }
        
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.shutdown_event = threading.Event()

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

    def discover_events(self) -> int:
        """Discover new events from all timing partners"""
        try:
            partners = self.get_timing_partners_with_credentials()
            new_events_found = 0
            
            for timing_partner_id, company_name, principal, secret, additional_config in partners:
                try:
                    self.logger.info(f"🔍 Discovering events for {company_name} (Partner {timing_partner_id})")
                    
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
                        continue
                    
                    # Get events
                    events = adapter.get_events()
                    self.stats['api_calls'] += adapter.stats['api_calls']
                    
                    # Store new events
                    conn = self.get_connection()
                    cursor = conn.cursor()
                    
                    for event in events:
                        try:
                            # Check if event already exists
                            cursor.execute("""
                                SELECT COUNT(*) FROM ct_events 
                                WHERE provider_event_id = %s 
                                AND timing_partner_id = %s 
                                AND data_source = 'chronotrack_live'
                            """, (event.provider_event_id, timing_partner_id))
                            
                            exists = cursor.fetchone()[0] > 0
                            
                            if not exists:
                                # Insert new event
                                cursor.execute("""
                                    INSERT INTO ct_events (
                                        timing_partner_id, provider_event_id, event_name, event_description,
                                        start_date, end_date, location, event_type, distance,
                                        registration_limit, registration_fee, currency, status,
                                        data_source, api_fetched_date, api_credentials_used, created_at, updated_at
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                                             'chronotrack_live', NOW(), %s, NOW(), NOW())
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
                                    principal[:10] + "..."  # Truncated credential reference
                                ))
                                
                                new_events_found += 1
                                self.logger.info(f"✅ Added new event: {event.event_name}")
                                
                        except Exception as e:
                            self.logger.error(f"Error storing event {event.event_name}: {e}")
                            continue
                    
                    conn.commit()
                    conn.close()
                    
                except Exception as e:
                    self.logger.error(f"Error discovering events for {company_name}: {e}")
                    self.stats['errors'] += 1
                    continue
            
            self.stats['events_discovered'] += new_events_found
            self.stats['last_discovery'] = datetime.now()
            
            self.logger.info(f"🎯 Discovery complete: {new_events_found} new events found")
            return new_events_found
            
        except Exception as e:
            self.logger.error(f"Error in event discovery: {e}")
            return 0

    def get_events_needing_results_collection(self) -> List[Dict]:
        """Get events that need results collection based on timing rules"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            now = datetime.now()
            
            # Get events within collection window
            cursor.execute("""
                SELECT 
                    ce.event_id,
                    ce.timing_partner_id,
                    ce.provider_event_id,
                    ce.event_name,
                    ce.start_date,
                    ce.end_date,
                    tp.company_name,
                    ppc.principal,
                    ppc.secret,
                    ppc.additional_config,
                    COALESCE(MAX(sh.sync_time), ce.created_at) as last_results_sync
                FROM ct_events ce
                JOIN timing_partners tp ON ce.timing_partner_id = tp.timing_partner_id
                JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
                LEFT JOIN sync_history sh ON ce.event_id::text = sh.event_id 
                    AND sh.timing_partner_id = ce.timing_partner_id
                    AND sh.sync_type = 'results'
                    AND sh.status = 'completed'
                WHERE ppc.provider_id = 1  -- ChronoTrack Live
                AND ce.data_source = 'chronotrack_live'
                AND ce.start_date IS NOT NULL
                AND ce.start_date > %s  -- Events that haven't finished collection period
                GROUP BY ce.event_id, ce.timing_partner_id, ce.provider_event_id, ce.event_name, 
                         ce.start_date, ce.end_date, tp.company_name, ppc.principal, ppc.secret, 
                         ppc.additional_config, ce.created_at
                ORDER BY ce.start_date ASC
            """, (now - timedelta(hours=self.results_config['max_collection_hours']),))
            
            events = cursor.fetchall()
            conn.close()
            
            # Filter events based on collection timing rules
            events_to_collect = []
            
            for event in events:
                if self._should_collect_results(event, now):
                    events_to_collect.append(dict(event))
            
            self.logger.info(f"Found {len(events_to_collect)} events needing results collection")
            return events_to_collect
            
        except Exception as e:
            self.logger.error(f"Error getting events for results collection: {e}")
            return []

    def _should_collect_results(self, event: Dict, now: datetime) -> bool:
        """Determine if event needs results collection based on timing rules"""
        try:
            start_date = event['start_date']
            last_sync = event['last_results_sync']
            
            if not start_date:
                return False
            
            # Calculate time since event start
            time_since_start = now - start_date
            time_since_last_sync = now - last_sync if last_sync else timedelta(hours=999)
            
            # Rule 1: Don't collect before 5 minutes after start
            if time_since_start < timedelta(minutes=self.results_config['initial_delay_minutes']):
                return False
            
            # Rule 2: Stop collecting after 72 hours
            if time_since_start > timedelta(hours=self.results_config['max_collection_hours']):
                return False
            
            # Rule 3: Intensive collection (90s intervals) for first 5 hours
            if time_since_start <= timedelta(hours=self.results_config['intensive_duration_hours']):
                return time_since_last_sync >= timedelta(seconds=self.results_config['intensive_interval_seconds'])
            
            # Rule 4: Standard collection (hourly) after intensive period
            return time_since_last_sync >= timedelta(hours=self.results_config['standard_interval_hours'])
            
        except Exception as e:
            self.logger.error(f"Error checking collection timing for event {event.get('event_name', 'unknown')}: {e}")
            return False

    def collect_event_results(self, event: Dict) -> Dict:
        """Collect results for a specific event"""
        timing_partner_id = event['timing_partner_id']
        event_name = event['event_name']
        provider_event_id = event['provider_event_id']
        
        results_collected = 0
        
        try:
            self.logger.info(f"📊 Collecting results for {event_name}")
            
            # Create adapter
            credentials = {
                'principal': event['principal'],
                'secret': event['secret'],
                'additional_config': event.get('additional_config') or {}
            }
            
            adapter = ChronoTrackLiveAdapter(credentials, timing_partner_id)
            
            # Get results from ChronoTrack Live API
            results = adapter.get_results(provider_event_id)
            self.stats['api_calls'] += adapter.stats['api_calls']
            
            if results:
                # Store results in ct_results table
                conn = self.get_connection()
                cursor = conn.cursor()
                
                for result_data in results:
                    try:
                        # Store result with data_source = 'chronotrack_live'
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
                                gender_place = EXCLUDED.gender_place,
                                division_place = EXCLUDED.division_place,
                                finish_time = EXCLUDED.finish_time,
                                split_times = EXCLUDED.split_times,
                                result_status = EXCLUDED.result_status
                        """, (
                            timing_partner_id,
                            event['event_id'],
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
                        
                        results_collected += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error storing result for bib {result_data.get('bib_number', 'unknown')}: {e}")
                        continue
                
                # Record sync history
                cursor.execute("""
                    INSERT INTO sync_history (
                        timing_partner_id, provider_id, event_id, sync_type, 
                        status, results_synced, sync_time
                    ) VALUES (%s, %s, %s, 'results', 'completed', %s, NOW())
                """, (timing_partner_id, 1, provider_event_id, results_collected))
                
                conn.commit()
                conn.close()
            
            self.stats['results_collected'] += results_collected
            
            result = {
                'event_name': event_name,
                'results_collected': results_collected,
                'success': True,
                'timing_partner_id': timing_partner_id
            }
            
            self.logger.info(f"✅ Collected {results_collected} results for {event_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Failed to collect results for {event_name}: {e}")
            self.stats['errors'] += 1
            
            return {
                'event_name': event_name,
                'results_collected': 0,
                'success': False,
                'error': str(e),
                'timing_partner_id': timing_partner_id
            }

    def run_results_collection_cycle(self):
        """Run one cycle of results collection for all eligible events"""
        try:
            events = self.get_events_needing_results_collection()
            
            if not events:
                self.logger.info("📭 No events need results collection at this time")
                return
            
            # Limit concurrent processing
            max_concurrent = min(len(events), self.results_config['max_concurrent_events'])
            
            self.logger.info(f"🚀 Starting results collection for {len(events)} events (max {max_concurrent} concurrent)")
            
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                # Submit collection jobs
                future_to_event = {
                    executor.submit(self.collect_event_results, event): event 
                    for event in events
                }
                
                # Process completed jobs
                for future in as_completed(future_to_event):
                    event = future_to_event[future]
                    try:
                        result = future.result()
                        if result['success']:
                            self.logger.info(f"✅ Results collection completed for {result['event_name']}")
                        else:
                            self.logger.error(f"❌ Results collection failed for {result['event_name']}: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        self.logger.error(f"❌ Results collection exception for {event['event_name']}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error in results collection cycle: {e}")

    def get_events_needing_participant_sync(self) -> List[Dict]:
        """Get events that need participant synchronization based on timing rules"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            now = datetime.now()
            
            cursor.execute("""
                SELECT 
                    ce.event_id,
                    ce.timing_partner_id,
                    ce.provider_event_id,
                    ce.event_name,
                    ce.start_date,
                    ce.end_date,
                    tp.company_name,
                    ppc.principal,
                    ppc.secret,
                    ppc.additional_config,
                    COALESCE(MAX(sh.sync_time), ce.created_at) as last_participant_sync
                FROM ct_events ce
                JOIN timing_partners tp ON ce.timing_partner_id = tp.timing_partner_id
                JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
                LEFT JOIN sync_history sh ON ce.event_id::text = sh.event_id 
                    AND sh.timing_partner_id = ce.timing_partner_id
                    AND sh.sync_type = 'participants'
                    AND sh.status = 'completed'
                WHERE ppc.provider_id = 1  -- ChronoTrack Live
                AND ce.data_source = 'chronotrack_live'
                AND ce.start_date IS NOT NULL
                AND ce.start_date > %s  -- Events not finished
                GROUP BY ce.event_id, ce.timing_partner_id, ce.provider_event_id, ce.event_name,
                         ce.start_date, ce.end_date, tp.company_name, ppc.principal, ppc.secret,
                         ppc.additional_config, ce.created_at
                ORDER BY ce.start_date ASC
            """, (now - timedelta(hours=self.event_config['stop_after_finish_hours']),))
            
            events = cursor.fetchall()
            conn.close()
            
            # Filter events based on participant sync timing rules
            events_to_sync = []
            
            for event in events:
                if self._should_sync_participants(event, now):
                    events_to_sync.append(dict(event))
            
            self.logger.info(f"Found {len(events_to_sync)} events needing participant sync")
            return events_to_sync
            
        except Exception as e:
            self.logger.error(f"Error getting events for participant sync: {e}")
            return []

    def _should_sync_participants(self, event: Dict, now: datetime) -> bool:
        """Determine if event needs participant sync based on timing rules"""
        try:
            start_date = event['start_date']
            last_sync = event['last_participant_sync']
            
            if not start_date:
                return False
            
            # Calculate time since event start
            time_since_start = now - start_date
            time_since_last_sync = now - last_sync if last_sync else timedelta(hours=999)
            
            # Rule 1: Sync participants up to 1 hour after event finish
            if time_since_start > timedelta(hours=self.event_config['stop_after_finish_hours']):
                return False
            
            # Rule 2: Sync every 24 hours before event start
            if time_since_start < timedelta(0):  # Before event start
                return time_since_last_sync >= timedelta(hours=self.event_config['sync_participants_interval_hours'])
            
            # Rule 3: More frequent sync during event (every 6 hours)
            return time_since_last_sync >= timedelta(hours=6)
            
        except Exception as e:
            self.logger.error(f"Error checking participant sync timing for event {event.get('event_name', 'unknown')}: {e}")
            return False

    def sync_event_participants(self, event: Dict) -> Dict:
        """Sync participants for a specific event"""
        timing_partner_id = event['timing_partner_id']
        event_name = event['event_name']
        provider_event_id = event['provider_event_id']
        
        participants_synced = 0
        
        try:
            self.logger.info(f"👥 Syncing participants for {event_name}")
            
            # Create adapter
            credentials = {
                'principal': event['principal'],
                'secret': event['secret'],
                'additional_config': event.get('additional_config') or {}
            }
            
            adapter = ChronoTrackLiveAdapter(credentials, timing_partner_id)
            
            # Get participants from ChronoTrack Live API
            participants = adapter.get_participants(provider_event_id)
            self.stats['api_calls'] += adapter.stats['api_calls']
            
            if participants:
                # Store participants in ct_participants table
                conn = self.get_connection()
                cursor = conn.cursor()
                
                for participant in participants:
                    try:
                        # Store participant with data_source = 'chronotrack_live'
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
                                phone = EXCLUDED.phone,
                                registration_status = EXCLUDED.registration_status,
                                payment_status = EXCLUDED.payment_status,
                                amount_paid = EXCLUDED.amount_paid,
                                updated_at = NOW()
                        """, (
                            timing_partner_id,
                            event['event_id'],
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
                            'active',  # registration_status
                            'paid' if participant.payment_amount else 'pending',  # payment_status
                            participant.payment_amount
                        ))
                        
                        participants_synced += 1
                        
                    except Exception as e:
                        self.logger.error(f"Error storing participant {participant.first_name} {participant.last_name}: {e}")
                        continue
                
                # Record sync history
                cursor.execute("""
                    INSERT INTO sync_history (
                        timing_partner_id, provider_id, event_id, sync_type, 
                        status, participants_synced, sync_time
                    ) VALUES (%s, %s, %s, 'participants', 'completed', %s, NOW())
                """, (timing_partner_id, 1, provider_event_id, participants_synced))
                
                conn.commit()
                conn.close()
            
            self.stats['participants_synced'] += participants_synced
            
            result = {
                'event_name': event_name,
                'participants_synced': participants_synced,
                'success': True,
                'timing_partner_id': timing_partner_id
            }
            
            self.logger.info(f"✅ Synced {participants_synced} participants for {event_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Failed to sync participants for {event_name}: {e}")
            self.stats['errors'] += 1
            
            return {
                'event_name': event_name,
                'participants_synced': 0,
                'success': False,
                'error': str(e),
                'timing_partner_id': timing_partner_id
            }

    def run_participant_sync_cycle(self):
        """Run one cycle of participant synchronization for all eligible events"""
        try:
            events = self.get_events_needing_participant_sync()
            
            if not events:
                self.logger.info("📭 No events need participant sync at this time")
                return
            
            # Limit concurrent processing
            max_concurrent = min(len(events), self.results_config['max_concurrent_events'])
            
            self.logger.info(f"🚀 Starting participant sync for {len(events)} events (max {max_concurrent} concurrent)")
            
            with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
                # Submit sync jobs
                future_to_event = {
                    executor.submit(self.sync_event_participants, event): event 
                    for event in events
                }
                
                # Process completed jobs
                for future in as_completed(future_to_event):
                    event = future_to_event[future]
                    try:
                        result = future.result()
                        if result['success']:
                            self.logger.info(f"✅ Participant sync completed for {result['event_name']}")
                        else:
                            self.logger.error(f"❌ Participant sync failed for {result['event_name']}: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        self.logger.error(f"❌ Participant sync exception for {event['event_name']}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error in participant sync cycle: {e}")

    def run_event_discovery_cycle(self):
        """Run one cycle of event discovery"""
        try:
            last_discovery = self.stats.get('last_discovery')
            now = datetime.now()
            
            # Check if discovery is needed
            if last_discovery:
                time_since_discovery = now - last_discovery
                if time_since_discovery < timedelta(hours=self.event_config['discovery_interval_hours']):
                    return
            
            self.logger.info("🔍 Starting event discovery cycle")
            new_events = self.discover_events()
            
            if new_events > 0:
                self.logger.info(f"🎯 Event discovery completed: {new_events} new events")
            else:
                self.logger.info("📭 Event discovery completed: No new events found")
                
        except Exception as e:
            self.logger.error(f"Error in event discovery cycle: {e}")

    def start(self):
        """Start the ChronoTrack Live scheduler"""
        self.running = True
        self.logger.info("🚀 ChronoTrack Live Scheduler started")
        
        # Initial event discovery
        self.run_event_discovery_cycle()
        
        cycle_count = 0
        
        while self.running and not self.shutdown_event.is_set():
            try:
                cycle_count += 1
                cycle_start = datetime.now()
                
                self.logger.info(f"📊 Scheduler cycle {cycle_count} starting")
                
                # Run results collection every cycle (every 30 seconds)
                self.run_results_collection_cycle()
                
                # Run participant sync every 5 cycles (every 2.5 minutes)
                if cycle_count % 5 == 0:
                    self.run_participant_sync_cycle()
                
                # Run event discovery every 6 hours
                self.run_event_discovery_cycle()
                
                # Log statistics
                if cycle_count % 10 == 0:  # Every 10 cycles (5 minutes)
                    self._log_statistics()
                
                # Sleep until next cycle (30 seconds)
                if self.shutdown_event.wait(30):
                    break
                    
            except KeyboardInterrupt:
                self.logger.info("📝 Received interrupt signal")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in scheduler cycle: {e}")
                self.stats['errors'] += 1
                time.sleep(30)  # Wait before retrying
        
        self.stop()

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        self.shutdown_event.set()
        self.logger.info("🛑 ChronoTrack Live Scheduler stopped")

    def _log_statistics(self):
        """Log scheduler statistics"""
        uptime = datetime.now() - self.stats['scheduler_start_time']
        
        self.logger.info(f"""
📊 ChronoTrack Live Scheduler Statistics:
   ⏱️  Uptime: {uptime}
   🎯 Events discovered: {self.stats['events_discovered']}
   📊 Results collected: {self.stats['results_collected']}
   🔗 API calls made: {self.stats['api_calls']}
   ❌ Errors: {self.stats['errors']}
   🕐 Last discovery: {self.stats.get('last_discovery', 'Never')}
        """)

def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/tmp/chronotrack_live_scheduler.log'),
            logging.StreamHandler()
        ]
    )
    
    scheduler = ChronoTrackLiveScheduler()
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logging.info("Received interrupt signal")
    finally:
        scheduler.stop()

if __name__ == "__main__":
    main() 