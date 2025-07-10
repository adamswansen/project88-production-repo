#!/usr/bin/env python3
"""
ChronoTrack Live Provider Adapter for Project88Hub
Implements ChronoTrack Live API integration with SHA password encoding
and X-Ctlive-* custom pagination headers

Key Differences from existing ChronoTrack:
- Current ChronoTrack: TCP-based hardware integration on port 61611
- ChronoTrack Live: API-based integration following provider adapter pattern
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import requests
import hashlib
import logging
import time

from .base_adapter import BaseProviderAdapter, ProviderEvent, ProviderParticipant

class ChronoTrackLiveAdapter(BaseProviderAdapter):
    """ChronoTrack Live API adapter with SHA authentication and custom pagination"""
    
    # Production API URLs (placeholder - need actual ChronoTrack Live endpoints)
    BASE_URL = "https://api.chronotracklive.com"  # Placeholder URL
    
    def __init__(self, credentials: Dict[str, Any], timing_partner_id: int = None):
        # ChronoTrack Live rate limit: 1500 concurrent connections per 60 seconds
        # Convert to hourly rate: 1500 * 60 = 90,000 per hour
        super().__init__(credentials, rate_limit_per_hour=90000)
        self.timing_partner_id = timing_partner_id
        
        # Map credentials from partner_provider_credentials format
        self.username = credentials.get('principal')  # Username stored as principal
        self.password = credentials.get('secret')     # Password stored as secret
        
        # Legacy support for old format
        if not self.username:
            self.username = credentials.get('username')
        if not self.password:
            self.password = credentials.get('password')
        
        if not self.username or not self.password:
            raise ValueError("ChronoTrack Live requires 'principal' (username) and 'secret' (password)")
        
        # ChronoTrack Live configuration
        self.config = {
            'max_page_size': 1000,        # ChronoTrack Live max page size
            'retry_attempts': 5,          # Retry failed requests
            'retry_delay_base': 2,        # Base delay for exponential backoff
            'timeout': 30,                # Request timeout
            'rate_limit_buffer': 0.1,     # 10% buffer on rate limits
            'sha_encoding': 'utf-8',      # Character encoding for SHA
        }
        
        # Statistics tracking
        self.stats = {
            'api_calls': 0,
            'retries': 0,
            'events_processed': 0,
            'participants_processed': 0,
            'results_processed': 0,
            'errors': []
        }
        
        # Authentication cache
        self.auth_hash = None
        self.auth_expires_at = None

    def get_provider_name(self) -> str:
        return "ChronoTrack Live"

    def _generate_sha_password(self) -> str:
        """Generate SHA-encoded password for ChronoTrack Live authentication"""
        if not self.password:
            raise ValueError("Password is required for SHA encoding")
        
        # Encode password using SHA-256 (or SHA-1 if that's what ChronoTrack uses)
        password_bytes = self.password.encode(self.config['sha_encoding'])
        sha_hash = hashlib.sha256(password_bytes).hexdigest()
        
        self.logger.debug(f"Generated SHA hash for authentication")
        return sha_hash

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for ChronoTrack Live API"""
        if not self.auth_hash or (self.auth_expires_at and datetime.now() > self.auth_expires_at):
            self.auth_hash = self._generate_sha_password()
            # Cache for 1 hour
            self.auth_expires_at = datetime.now() + timedelta(hours=1)
        
        return {
            'Authorization': f'Basic {self.username}:{self.auth_hash}',  # Basic auth with SHA password
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Project88Hub/1.0 ChronoTrackLiveAdapter'
        }

    def _make_paginated_request(self, endpoint: str, params: Dict = None, 
                              page_size: int = None) -> List[Dict]:
        """
        Make paginated request using ChronoTrack Live's X-Ctlive-* headers
        
        ChronoTrack Live uses custom pagination headers:
        - X-Ctlive-Page: Current page number
        - X-Ctlive-Per-Page: Number of items per page
        - X-Ctlive-Total: Total number of items
        - X-Ctlive-Pages: Total number of pages
        """
        all_data = []
        page = 1
        page_size = page_size or self.config['max_page_size']
        
        while True:
            # Add ChronoTrack Live pagination headers
            headers = self._get_auth_headers()
            headers.update({
                'X-Ctlive-Page': str(page),
                'X-Ctlive-Per-Page': str(page_size)
            })
            
            try:
                self.rate_limiter.wait_if_needed()
                self.stats['api_calls'] += 1
                
                response = requests.get(
                    f"{self.BASE_URL}/{endpoint}",
                    headers=headers,
                    params=params,
                    timeout=self.config['timeout']
                )
                
                if response.status_code != 200:
                    self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                
                # Handle different response formats
                if isinstance(data, list):
                    page_data = data
                else:
                    page_data = data.get('data', data.get('results', []))
                
                if not page_data:
                    break
                
                all_data.extend(page_data)
                
                # Check pagination info from response headers
                total_pages = response.headers.get('X-Ctlive-Pages')
                current_page = response.headers.get('X-Ctlive-Page')
                
                if total_pages and current_page:
                    if int(current_page) >= int(total_pages):
                        break
                elif len(page_data) < page_size:
                    # No pagination headers, check if we got fewer items than requested
                    break
                
                page += 1
                
                # Small delay between pages to be respectful
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in paginated request page {page}: {e}")
                self.stats['errors'].append(str(e))
                break
        
        self.logger.info(f"Retrieved {len(all_data)} items from {endpoint} in {page-1} pages")
        return all_data

    def authenticate(self) -> bool:
        """Test authentication with ChronoTrack Live API"""
        try:
            headers = self._get_auth_headers()
            
            # Test with a lightweight endpoint (e.g., user info or events list with limit 1)
            response = requests.get(
                f"{self.BASE_URL}/events",
                headers=headers,
                params={'limit': 1},
                timeout=self.config['timeout']
            )
            
            if response.status_code == 200:
                self.logger.info("✅ ChronoTrack Live authentication successful")
                return True
            elif response.status_code == 401:
                self.logger.error("❌ ChronoTrack Live authentication failed: Invalid credentials")
                return False
            else:
                self.logger.error(f"❌ ChronoTrack Live authentication error: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"ChronoTrack Live authentication failed: {e}")
            return False

    def get_events(self, last_modified_since: Optional[datetime] = None) -> List[ProviderEvent]:
        """Get events from ChronoTrack Live API"""
        try:
            params = {}
            if last_modified_since:
                params['modified_since'] = last_modified_since.isoformat()
            
            # Add event status filters to get active events
            params.update({
                'status': 'active',
                'include_inactive': 'false'
            })
            
            events_data = self._make_paginated_request('events', params)
            
            events = []
            for event_data in events_data:
                # Check for duplicates with existing ChronoTrack data
                if not self._is_duplicate_event(event_data):
                    event = self._parse_event(event_data)
                    if event:
                        events.append(event)
                        self.stats['events_processed'] += 1
                else:
                    self.logger.debug(f"Skipping duplicate event: {event_data.get('id', 'unknown')}")
            
            self.logger.info(f"Retrieved {len(events)} unique events from ChronoTrack Live")
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to get events: {e}")
            self.stats['errors'].append(str(e))
            return []

    def get_participants(self, event_id: str, last_modified_since: Optional[datetime] = None) -> List[ProviderParticipant]:
        """Get participants for a specific event from ChronoTrack Live"""
        try:
            params = {}
            if last_modified_since:
                params['modified_since'] = last_modified_since.isoformat()
            
            participants_data = self._make_paginated_request(f'events/{event_id}/participants', params)
            
            participants = []
            for participant_data in participants_data:
                participant = self._parse_participant(participant_data, event_id)
                if participant:
                    participants.append(participant)
                    self.stats['participants_processed'] += 1
            
            self.logger.info(f"Retrieved {len(participants)} participants for event {event_id}")
            return participants
            
        except Exception as e:
            self.logger.error(f"Failed to get participants for event {event_id}: {e}")
            self.stats['errors'].append(str(e))
            return []

    def get_results(self, event_id: str, last_modified_since: Optional[datetime] = None) -> List[Dict]:
        """
        Get race results for a specific event from ChronoTrack Live
        This is unique to ChronoTrack Live - other providers don't typically have results
        """
        try:
            params = {}
            if last_modified_since:
                params['modified_since'] = last_modified_since.isoformat()
            
            results_data = self._make_paginated_request(f'events/{event_id}/results', params)
            
            results = []
            for result_data in results_data:
                result = self._parse_result(result_data, event_id)
                if result:
                    results.append(result)
                    self.stats['results_processed'] += 1
            
            self.logger.info(f"Retrieved {len(results)} results for event {event_id}")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to get results for event {event_id}: {e}")
            self.stats['errors'].append(str(e))
            return []

    def _is_duplicate_event(self, event_data: Dict) -> bool:
        """
        Check if this event already exists in our system from the existing ChronoTrack integration
        This prevents duplicate events between ChronoTrack hardware and ChronoTrack Live
        """
        try:
            # Use database function to check for duplicates
            event_name = event_data.get('name', '')
            event_date = self._parse_datetime(event_data.get('start_date'))
            
            if not event_name or not event_date or not self.timing_partner_id:
                return False
            
            # This would use the check_duplicate_chronotrack_event function from database
            # For now, return False to allow all events (implement actual DB check in production)
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking for duplicate event: {e}")
            return False

    def _parse_event(self, event_data: Dict) -> Optional[ProviderEvent]:
        """Parse ChronoTrack Live event data into standardized format"""
        try:
            event = ProviderEvent(
                provider_event_id=str(event_data.get('id')),
                event_name=event_data.get('name', ''),
                event_description=event_data.get('description'),
                event_date=self._parse_datetime(event_data.get('start_date')),
                event_end_date=self._parse_datetime(event_data.get('end_date')),
                location_name=event_data.get('location_name'),
                location_city=event_data.get('city'),
                location_state=event_data.get('state'),
                location_country=event_data.get('country'),
                event_type=event_data.get('event_type', 'running'),
                distance=self._parse_distance(event_data.get('distance')),
                max_participants=event_data.get('max_participants'),
                registration_open_date=self._parse_datetime(event_data.get('registration_start')),
                registration_close_date=self._parse_datetime(event_data.get('registration_end')),
                registration_fee=self._parse_fee(event_data.get('entry_fee')),
                currency=event_data.get('currency', 'USD'),
                status=event_data.get('status', 'active'),
                raw_data=event_data
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"Failed to parse ChronoTrack Live event {event_data.get('id', 'unknown')}: {e}")
            return None

    def _parse_participant(self, participant_data: Dict, event_id: str) -> Optional[ProviderParticipant]:
        """Parse ChronoTrack Live participant data into standardized format"""
        try:
            # Handle emergency contact
            emergency_contact = None
            if participant_data.get('emergency_contact'):
                emergency_contact = {
                    'name': participant_data['emergency_contact'].get('name'),
                    'phone': participant_data['emergency_contact'].get('phone'),
                    'relationship': participant_data['emergency_contact'].get('relationship')
                }
            
            participant = ProviderParticipant(
                provider_participant_id=str(participant_data.get('id')),
                event_id=event_id,
                first_name=participant_data.get('first_name', ''),
                last_name=participant_data.get('last_name', ''),
                email=participant_data.get('email'),
                phone=participant_data.get('phone'),
                date_of_birth=self._parse_datetime(participant_data.get('date_of_birth')),
                age=self._calculate_age(participant_data.get('date_of_birth')),
                gender=participant_data.get('gender'),
                city=participant_data.get('city'),
                state=participant_data.get('state'),
                country=participant_data.get('country'),
                bib_number=participant_data.get('bib_number'),
                emergency_contact=emergency_contact,
                team_name=participant_data.get('team_name'),
                division=participant_data.get('division'),
                registration_date=self._parse_datetime(participant_data.get('registered_at')),
                registration_status=participant_data.get('status', 'active'),
                payment_status=participant_data.get('payment_status'),
                amount_paid=self._parse_fee(participant_data.get('amount_paid')),
                raw_data=participant_data
            )
            
            return participant
            
        except Exception as e:
            self.logger.error(f"Failed to parse ChronoTrack Live participant {participant_data.get('id', 'unknown')}: {e}")
            return None

    def _parse_result(self, result_data: Dict, event_id: str) -> Optional[Dict]:
        """Parse ChronoTrack Live result data"""
        try:
            return {
                'event_id': event_id,
                'participant_id': result_data.get('participant_id'),
                'bib_number': result_data.get('bib_number'),
                'chip_time': result_data.get('chip_time'),
                'gun_time': result_data.get('gun_time'),
                'overall_place': result_data.get('overall_place'),
                'gender_place': result_data.get('gender_place'),
                'division_place': result_data.get('division_place'),
                'finish_time': self._parse_datetime(result_data.get('finish_time')),
                'split_times': result_data.get('split_times', []),
                'status': result_data.get('status', 'finished'),
                'raw_data': result_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to parse ChronoTrack Live result: {e}")
            return None

    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string into datetime object"""
        if not date_str:
            return None
        
        try:
            # Handle different datetime formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            self.logger.warning(f"Could not parse datetime: {date_str}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing datetime {date_str}: {e}")
            return None

    def _parse_fee(self, fee_data: Any) -> Optional[float]:
        """Parse fee data into float"""
        if fee_data is None:
            return None
        
        try:
            if isinstance(fee_data, (int, float)):
                return float(fee_data)
            elif isinstance(fee_data, str):
                return float(fee_data.replace('$', '').replace(',', ''))
            else:
                return None
        except (ValueError, TypeError):
            return None

    def _parse_distance(self, distance_data: Any) -> Optional[str]:
        """Parse distance data into string"""
        if not distance_data:
            return None
        
        try:
            if isinstance(distance_data, (int, float)):
                return f"{distance_data} miles"
            elif isinstance(distance_data, str):
                return distance_data
            else:
                return str(distance_data)
        except Exception:
            return None

    def _calculate_age(self, birth_date_str: str) -> Optional[int]:
        """Calculate age from birth date string"""
        if not birth_date_str:
            return None
        
        try:
            birth_date = self._parse_datetime(birth_date_str)
            if birth_date:
                today = datetime.now()
                age = today.year - birth_date.year
                # Adjust if birthday hasn't occurred this year
                if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                    age -= 1
                return age
            return None
            
        except Exception as e:
            self.logger.error(f"Error calculating age from {birth_date_str}: {e}")
            return None

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics"""
        return {
            'provider': self.get_provider_name(),
            'timing_partner_id': self.timing_partner_id,
            'stats': self.stats.copy(),
            'config': {
                'rate_limit_per_hour': 90000,
                'max_page_size': self.config['max_page_size'],
                'retry_attempts': self.config['retry_attempts']
            }
        }

    # Abstract method implementations for ct_ tables
    def _store_event(self, event: ProviderEvent):
        """Store event in ct_events table with data_source = 'chronotrack_live'"""
        try:
            # This would be implemented with actual database connection
            # For now, this is a placeholder showing the intended structure
            
            insert_sql = """
                INSERT INTO ct_events (
                    timing_partner_id, provider_event_id, event_name, event_description,
                    start_date, end_date, location, event_type, distance,
                    registration_limit, registration_fee, currency, status,
                    data_source, api_fetched_date, api_credentials_used, created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    'chronotrack_live', NOW(), %s, NOW(), NOW()
                )
                ON CONFLICT (timing_partner_id, provider_event_id, data_source)
                DO UPDATE SET
                    event_name = EXCLUDED.event_name,
                    event_description = EXCLUDED.event_description,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    location = EXCLUDED.location,
                    updated_at = NOW()
            """
            
            # Values would be: timing_partner_id, provider_event_id, event_name, etc.
            self.logger.info(f"Would store ChronoTrack Live event: {event.event_name}")
            
        except Exception as e:
            self.logger.error(f"Error storing event: {e}")

    def _store_participant(self, participant: ProviderParticipant):
        """Store participant in ct_participants table with data_source = 'chronotrack_live'"""
        try:
            # This would be implemented with actual database connection
            # For now, this is a placeholder showing the intended structure
            
            insert_sql = """
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
            """
            
            # Values would be: timing_partner_id, event_id, provider_participant_id, etc.
            self.logger.info(f"Would store ChronoTrack Live participant: {participant.first_name} {participant.last_name}")
            
        except Exception as e:
            self.logger.error(f"Error storing participant: {e}")

    def store_result(self, result_data: Dict, event_id: str):
        """Store result in ct_results table with data_source = 'chronotrack_live'"""
        try:
            # This would be implemented with actual database connection
            # For now, this is a placeholder showing the intended structure
            
            insert_sql = """
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
            """
            
            # Values would be: timing_partner_id, event_id, participant_id, etc.
            self.logger.info(f"Would store ChronoTrack Live result for bib {result_data.get('bib_number')}")
            
        except Exception as e:
            self.logger.error(f"Error storing result: {e}") 