#!/usr/bin/env python3
"""
RunSignUp Provider Adapter for Project88Hub
Implements RunSignUp REST API integration
API Documentation: https://runsignup.com/API
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import base64
import hashlib
import json

from .base_adapter import BaseProviderAdapter, ProviderEvent, ProviderParticipant

class RunSignUpAdapter(BaseProviderAdapter):
    """RunSignUp API adapter"""
    
    BASE_URL = "https://runsignup.com/REST"
    
    def __init__(self, credentials: Dict[str, Any], timing_partner_id: int = None):
        super().__init__(credentials, rate_limit_per_hour=1000)  # Back to production limit
        self.timing_partner_id = timing_partner_id
        self.api_key = credentials.get('principal')  # API Key
        self.api_secret = credentials.get('secret')   # API Secret
        
        if not self.api_key or not self.api_secret:
            raise ValueError("RunSignUp requires 'principal' (API Key) and 'secret' (API Secret)")
    
    def get_provider_name(self) -> str:
        return "RunSignUp"
    
    def authenticate(self) -> bool:
        """Test authentication with RunSignUp API"""
        try:
            # Test with a simple API call
            response = self._make_runsignup_request("/races", {"results_per_page": 1})
            # RunSignUp doesn't return a 'success' field - check if we got races data
            return 'races' in response and isinstance(response['races'], list)
        except Exception as e:
            self.logger.error(f"RunSignUp authentication failed: {e}")
            return False
    
    def get_events(self, last_modified_since: Optional[datetime] = None) -> List[ProviderEvent]:
        """Get events (RunSignUp calls them races/events)"""
        events = []
        page = 1
        
        while True:
            params = {
                "results_per_page": 1000,  # Increase to match participants pagination
                "page": page,
                "include_event_days": "T"
            }
            
            if last_modified_since:
                # RunSignUp uses last_modified parameter
                params["last_modified"] = last_modified_since.strftime("%Y-%m-%d %H:%M:%S")
            
            response = self._make_runsignup_request("/races", params)
            
            if 'races' not in response:
                self.logger.info(f"No races found on page {page}")
                break
                
            races = response.get('races', [])
            if not races:
                self.logger.info(f"Empty races list on page {page}")
                break
            
            self.logger.info(f"Found {len(races)} races on page {page}")
            
            for race_entry in races:
                # Get events for this race
                race_data = race_entry['race']  # Race data is nested under 'race' key
                race_events = self._get_race_events(race_data['race_id'])
                events.extend(race_events)
            
            page += 1
            
            # Break if we've got all pages (less than full page size)
            if len(races) < 1000:
                self.logger.info(f"Completed race pagination - got {len(events)} total events")
                break
        
        return events
    
    def get_participants(self, race_id: str, event_id: str = None, last_modified_since: Optional[datetime] = None) -> List[ProviderParticipant]:
        """Get participants for a specific event (event_id is required by RunSignUp API)"""
        if not event_id:
            self.logger.warning(f"No event_id provided for race {race_id} - cannot fetch participants")
            return []
            
        participants = []
        page = 1
        
        while True:
            params = {
                "race_id": race_id,  # Required by API spec
                "event_id": event_id,  # Required by RunSignUp API
                "results_per_page": 1000,  # Increase to reduce API calls
                "page": page,
                "include_individual_info": "T"
            }
            
            if last_modified_since:
                params["modified_after_timestamp"] = last_modified_since.strftime("%Y-%m-%d %H:%M:%S")
            
            # Use correct endpoint structure per OpenAPI spec: /race/{race_id}/participants
            response = self._make_runsignup_request(f"/race/{race_id}/participants", params)
            
            # Handle both list and dict response formats
            participant_data = []
            if isinstance(response, list):
                # Response is a list of event objects with participants
                for event_obj in response:
                    if 'participants' in event_obj:
                        participant_data.extend(event_obj['participants'])
            elif isinstance(response, dict) and 'participants' in response:
                # Response is a dict with participants key
                participant_data = response['participants']
            else:
                # No participants found or unexpected format
                break
                
            if not participant_data:
                self.logger.info(f"No participants found on page {page} for event {event_id}")
                break
            
            self.logger.info(f"Found {len(participant_data)} participants on page {page} for event {event_id}")
            
            for p_data in participant_data:
                participant = self._parse_participant(p_data, event_id)
                if participant:
                    participants.append(participant)
            
            page += 1
            
            # Break if we've got all pages (less than full page size)
            if len(participant_data) < 1000:
                self.logger.info(f"Completed pagination for event {event_id} - got {len(participants)} total participants")
                break
        
        return participants
    
    def get_participant_counts(self, race_id: str) -> Dict[str, Any]:
        """Get participant count summary for a race"""
        try:
            response = self._make_runsignup_request(f"/race/{race_id}/participant-counts")
            return response
        except Exception as e:
            self.logger.error(f"Failed to get participant counts for race {race_id}: {e}")
            return {}
    
    def _get_race_events(self, race_id: str) -> List[ProviderEvent]:
        """Get events for a specific race"""
        response = self._make_runsignup_request(f"/race/{race_id}", {"include_event_days": "T"})
        
        if 'race' not in response:
            return []
        
        race = response.get('race', {})
        events_data = race.get('events', [])
        
        parsed_events = []
        for event_data in events_data:
            event = self._parse_event(event_data, race)
            if event:
                parsed_events.append(event)
        
        return parsed_events
    
    def _parse_event(self, event_data: Dict, race_data: Dict) -> Optional[ProviderEvent]:
        """Parse RunSignUp event data into standardized format"""
        try:
            # Extract address information
            address = race_data.get('address', {})
            
            event = ProviderEvent(
                provider_event_id=str(event_data.get('event_id')),
                event_name=event_data.get('name', ''),
                event_description=event_data.get('details'),
                event_date=self._parse_datetime(event_data.get('start_time')),
                event_end_date=self._parse_datetime(event_data.get('end_time')),
                location_name=address.get('name'),
                location_city=address.get('city'),
                location_state=address.get('state'),
                event_type=event_data.get('event_type'),
                distance=self._safe_get(event_data, 'distance'),
                max_participants=None,  # RunSignUp doesn't provide this in events
                registration_open_date=self._parse_datetime(event_data.get('registration_opens')),
                registration_close_date=None,  # Not typically provided
                registration_fee=None,  # Would need separate call to get pricing
                currency='USD',  # RunSignUp is primarily US-based
                status='active' if event_data.get('active') else 'inactive',
                raw_data={
                    'event': event_data,
                    'race': race_data
                }
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"Failed to parse RunSignUp event {event_data.get('event_id')}: {e}")
            return None
    
    def _parse_participant(self, participant_data: Dict, event_id: str) -> Optional[ProviderParticipant]:
        """Parse RunSignUp participant data into standardized format"""
        try:
            user_data = participant_data.get('user', {})
            address_data = user_data.get('address', {})
            
            participant = ProviderParticipant(
                provider_participant_id=str(participant_data.get('registration_id', participant_data.get('user_id'))),
                event_id=event_id,
                bib_number=participant_data.get('bib_num'),
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                email=user_data.get('email'),
                phone=user_data.get('phone'),
                date_of_birth=self._parse_datetime(user_data.get('dob')),
                gender=user_data.get('gender'),
                age=participant_data.get('age'),
                city=address_data.get('city'),
                state=address_data.get('state'),
                country=address_data.get('country', 'US'),
                emergency_contact=user_data.get('emergency_contact'),
                team_name=participant_data.get('team_name'),
                division=None,  # Would need to derive from age/gender
                registration_date=self._parse_datetime(participant_data.get('registration_date')),
                registration_status='registered',  # RunSignUp doesn't have status field
                payment_status=participant_data.get('payment_status'),
                amount_paid=self._safe_get(participant_data, 'amount_paid'),
                raw_data=participant_data
            )
            
            return participant
            
        except Exception as e:
            self.logger.error(f"Failed to parse RunSignUp participant {participant_data.get('registration_id')}: {e}")
            return None
    
    def _make_runsignup_request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make authenticated request to RunSignUp API"""
        if params is None:
            params = {}
        
        # Add authentication parameters
        params.update({
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "format": "json"
        })
        
        url = f"{self.BASE_URL}{endpoint}"
        response = self._make_api_request(url, params=params)
        
        return response.json()
    
    def store_race(self, race_data: Dict, db_connection) -> int:
        """Store race data in runsignup_races table"""
        from datetime import datetime
        
        cursor = db_connection.cursor()
        
        # Extract address information
        address = race_data.get('address', {})
        
        # Insert or update race using PostgreSQL syntax with JSONB address
        cursor.execute("""
            INSERT INTO runsignup_races (
                race_id, name, last_date, last_end_date, next_date, next_end_date,
                is_draft_race, is_private_race, is_registration_open, created, 
                last_modified, description, url, external_race_url, external_results_url,
                fb_page_id, fb_event_id, address, timezone, logo_url, real_time_notifications_enabled,
                fetched_date, credentials_used, timing_partner_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (race_id) DO UPDATE SET
                name = EXCLUDED.name,
                last_date = EXCLUDED.last_date,
                last_end_date = EXCLUDED.last_end_date,
                next_date = EXCLUDED.next_date,
                next_end_date = EXCLUDED.next_end_date,
                is_draft_race = EXCLUDED.is_draft_race,
                is_private_race = EXCLUDED.is_private_race,
                is_registration_open = EXCLUDED.is_registration_open,
                last_modified = EXCLUDED.last_modified,
                description = EXCLUDED.description,
                url = EXCLUDED.url,
                external_race_url = EXCLUDED.external_race_url,
                external_results_url = EXCLUDED.external_results_url,
                fb_page_id = EXCLUDED.fb_page_id,
                fb_event_id = EXCLUDED.fb_event_id,
                address = EXCLUDED.address,
                timezone = EXCLUDED.timezone,
                logo_url = EXCLUDED.logo_url,
                real_time_notifications_enabled = EXCLUDED.real_time_notifications_enabled,
                fetched_date = EXCLUDED.fetched_date
        """, (
            race_data.get('race_id'),
            race_data.get('name'),
            race_data.get('last_date'),
            race_data.get('last_end_date'),
            race_data.get('next_date'),
            race_data.get('next_end_date'),
            race_data.get('is_draft_race'),
            race_data.get('is_private_race'),
            race_data.get('is_registration_open'),
            race_data.get('created'),
            race_data.get('last_modified'),
            race_data.get('description'),
            race_data.get('url'),
            race_data.get('external_race_url'),
            race_data.get('external_results_url'),
            race_data.get('fb_page_id'),
            race_data.get('fb_event_id'),
            json.dumps(address) if address else None,
            race_data.get('timezone'),
            race_data.get('logo_url'),
            race_data.get('real_time_notifications_enabled'),
            datetime.now(),
            self.api_key,
            self.timing_partner_id
        ))
        
        return race_data.get('race_id')
    
    def store_event(self, event_data: Dict, race_id: int, db_connection) -> int:
        """Store event data in runsignup_events table"""
        from datetime import datetime
        
        cursor = db_connection.cursor()
        
        # Handle distance conversion for numeric field
        distance_value = event_data.get('distance')
        if distance_value:
            try:
                # Try to extract numeric value from text like "3.2 Miles" 
                import re
                numeric_match = re.search(r'(\d+\.?\d*)', str(distance_value))
                if numeric_match:
                    distance_value = float(numeric_match.group(1))
                else:
                    distance_value = None
            except (ValueError, TypeError):
                distance_value = None
        
        cursor.execute("""
            INSERT INTO runsignup_events (
                event_id, race_id, name, details, start_time, end_time,
                age_calc_base_date, registration_opens, event_type, distance,
                volunteer, require_dob, require_phone, giveaway,
                fetched_date, credentials_used, timing_partner_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (event_id) DO UPDATE SET
                race_id = EXCLUDED.race_id,
                name = EXCLUDED.name,
                details = EXCLUDED.details,
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                age_calc_base_date = EXCLUDED.age_calc_base_date,
                registration_opens = EXCLUDED.registration_opens,
                event_type = EXCLUDED.event_type,
                distance = EXCLUDED.distance,
                volunteer = EXCLUDED.volunteer,
                require_dob = EXCLUDED.require_dob,
                require_phone = EXCLUDED.require_phone,
                giveaway = EXCLUDED.giveaway,
                fetched_date = EXCLUDED.fetched_date
        """, (
            event_data.get('event_id'),
            race_id,
            event_data.get('name'),
            event_data.get('details'),
            event_data.get('start_time'),
            event_data.get('end_time'),
            event_data.get('age_calc_base_date'),
            event_data.get('registration_opens'),
            event_data.get('event_type'),
            distance_value,
            event_data.get('volunteer'),
            event_data.get('require_dob'),
            event_data.get('require_phone'),
            event_data.get('giveaway'),
            datetime.now(),
            self.api_key,
            self.timing_partner_id
        ))
        
        return event_data.get('event_id')
    
    def store_participant(self, participant_data: Dict, race_id: int, event_id: int, db_connection):
        """Store participant data in database with proper duplicate handling"""
        cursor = db_connection.cursor()
        
        # Check if participant already exists using registration_id and timing_partner_id
        cursor.execute("""
            SELECT id FROM runsignup_participants 
            WHERE registration_id = %s AND timing_partner_id = %s
        """, (participant_data.get('registration_id'), self.timing_partner_id))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            cursor.execute("""
                UPDATE runsignup_participants SET
                    race_id = %s, event_id = %s, user_id = %s, first_name = %s, middle_name = %s, last_name = %s,
                    email = %s, address = %s, dob = %s, gender = %s, phone = %s, profile_image_url = %s,
                    bib_num = %s, chip_num = %s, age = %s, registration_date = %s, 
                    team_info = %s, payment_info = %s, additional_data = %s,
                    fetched_date = %s, credentials_used = %s, last_modified = %s
                WHERE id = %s
            """, (
                race_id,
                event_id,
                participant_data.get('user', {}).get('user_id'),
                participant_data.get('user', {}).get('first_name'),
                participant_data.get('user', {}).get('middle_name'),
                participant_data.get('user', {}).get('last_name'),
                participant_data.get('user', {}).get('email'),
                json.dumps(participant_data.get('user', {}).get('address', {})) if participant_data.get('user', {}).get('address') else None,
                self._parse_runsignup_date(participant_data.get('user', {}).get('dob')),
                participant_data.get('user', {}).get('gender'),
                participant_data.get('user', {}).get('phone'),
                participant_data.get('user', {}).get('profile_image_url'),
                participant_data.get('bib_num'),
                participant_data.get('chip_num'),
                participant_data.get('user', {}).get('age'),
                self._parse_runsignup_date(participant_data.get('registration_date')),
                json.dumps({
                    'team_id': participant_data.get('team_id'),
                    'team_name': participant_data.get('team_name'),
                    'team_type_id': participant_data.get('team_type_id'),
                    'team_type': participant_data.get('team_type'),
                    'team_gender': participant_data.get('team_gender'),
                    'team_bib_num': participant_data.get('team_bib_num')
                }),
                json.dumps({
                    'race_fee': self._clean_currency_string(participant_data.get('race_fee', '0')),
                    'offline_payment_amount': self._clean_currency_string(participant_data.get('offline_payment_amount', '0')),
                    'processing_fee': self._clean_currency_string(participant_data.get('processing_fee', '0')),
                    'processing_fee_paid_by_user': self._clean_currency_string(participant_data.get('processing_fee_paid_by_user', '0')),
                    'processing_fee_paid_by_race': self._clean_currency_string(participant_data.get('processing_fee_paid_by_race', '0')),
                    'partner_fee': self._clean_currency_string(participant_data.get('partner_fee', '0')),
                    'affiliate_profit': self._clean_currency_string(participant_data.get('affiliate_profit', '0')),
                    'extra_fees': self._clean_currency_string(participant_data.get('extra_fees', '0')),
                    'amount_paid': self._clean_currency_string(participant_data.get('amount_paid', '0')),
                    'rsu_transaction_id': participant_data.get('rsu_transaction_id'),
                    'transaction_id': participant_data.get('transaction_id')
                }),
                json.dumps({
                    'usatf_discount_amount_in_cents': participant_data.get('usatf_discount_amount_in_cents'),
                    'usatf_discount_additional_field': participant_data.get('usatf_discount_additional_field'),
                    'giveaway': participant_data.get('giveaway'),
                    'giveaway_option_id': participant_data.get('giveaway_option_id'),
                    'fundraiser_id': participant_data.get('fundraiser_id'),
                    'fundraiser_charity_id': participant_data.get('fundraiser_charity_id'),
                    'fundraiser_charity_name': participant_data.get('fundraiser_charity_name'),
                    'team_fundraiser_id': participant_data.get('team_fundraiser_id'),
                    'multi_race_bundle_id': participant_data.get('multi_race_bundle_id'),
                    'multi_race_bundle': participant_data.get('multi_race_bundle'),
                    'signed_waiver_details': participant_data.get('signed_waiver_details'),
                    'imported': participant_data.get('imported')
                }),
                datetime.now(),
                self.api_key,
                self._parse_runsignup_date(participant_data.get('last_modified')),
                existing[0]  # id
            ))
        else:
            # Insert new record (without specifying id, let it auto-increment)
            cursor.execute("""
                INSERT INTO runsignup_participants (
                    race_id, event_id, registration_id, user_id, first_name, middle_name, last_name,
                    email, address, dob, gender, phone, profile_image_url,
                    bib_num, chip_num, age, registration_date, 
                    team_info, payment_info, additional_data,
                    fetched_date, credentials_used, timing_partner_id, last_modified, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                race_id,
                event_id,
                participant_data.get('registration_id'),
                participant_data.get('user', {}).get('user_id'),
                participant_data.get('user', {}).get('first_name'),
                participant_data.get('user', {}).get('middle_name'),
                participant_data.get('user', {}).get('last_name'),
                participant_data.get('user', {}).get('email'),
                json.dumps(participant_data.get('user', {}).get('address', {})) if participant_data.get('user', {}).get('address') else None,
                self._parse_runsignup_date(participant_data.get('user', {}).get('dob')),
                participant_data.get('user', {}).get('gender'),
                participant_data.get('user', {}).get('phone'),
                participant_data.get('user', {}).get('profile_image_url'),
                participant_data.get('bib_num'),
                participant_data.get('chip_num'),
                participant_data.get('user', {}).get('age'),
                self._parse_runsignup_date(participant_data.get('registration_date')),
                json.dumps({
                    'team_id': participant_data.get('team_id'),
                    'team_name': participant_data.get('team_name'),
                    'team_type_id': participant_data.get('team_type_id'),
                    'team_type': participant_data.get('team_type'),
                    'team_gender': participant_data.get('team_gender'),
                    'team_bib_num': participant_data.get('team_bib_num')
                }),
                json.dumps({
                    'race_fee': self._clean_currency_string(participant_data.get('race_fee', '0')),
                    'offline_payment_amount': self._clean_currency_string(participant_data.get('offline_payment_amount', '0')),
                    'processing_fee': self._clean_currency_string(participant_data.get('processing_fee', '0')),
                    'processing_fee_paid_by_user': self._clean_currency_string(participant_data.get('processing_fee_paid_by_user', '0')),
                    'processing_fee_paid_by_race': self._clean_currency_string(participant_data.get('processing_fee_paid_by_race', '0')),
                    'partner_fee': self._clean_currency_string(participant_data.get('partner_fee', '0')),
                    'affiliate_profit': self._clean_currency_string(participant_data.get('affiliate_profit', '0')),
                    'extra_fees': self._clean_currency_string(participant_data.get('extra_fees', '0')),
                    'amount_paid': self._clean_currency_string(participant_data.get('amount_paid', '0')),
                    'rsu_transaction_id': participant_data.get('rsu_transaction_id'),
                    'transaction_id': participant_data.get('transaction_id')
                }),
                json.dumps({
                    'usatf_discount_amount_in_cents': participant_data.get('usatf_discount_amount_in_cents'),
                    'usatf_discount_additional_field': participant_data.get('usatf_discount_additional_field'),
                    'giveaway': participant_data.get('giveaway'),
                    'giveaway_option_id': participant_data.get('giveaway_option_id'),
                    'fundraiser_id': participant_data.get('fundraiser_id'),
                    'fundraiser_charity_id': participant_data.get('fundraiser_charity_id'),
                    'fundraiser_charity_name': participant_data.get('fundraiser_charity_name'),
                    'team_fundraiser_id': participant_data.get('team_fundraiser_id'),
                    'multi_race_bundle_id': participant_data.get('multi_race_bundle_id'),
                    'multi_race_bundle': participant_data.get('multi_race_bundle'),
                    'signed_waiver_details': participant_data.get('signed_waiver_details'),
                    'imported': participant_data.get('imported')
                }),
                datetime.now(),
                self.api_key,
                self.timing_partner_id,
                self._parse_runsignup_date(participant_data.get('last_modified')),
                datetime.now()
            ))
    
    def _store_event(self, event: ProviderEvent):
        """Store event in RunSignUp events table (called by base class)"""
        try:
            # Get database connection
            import psycopg2
            import os
            
            # Connect to PostgreSQL database
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'project88_myappdb'),
                user=os.getenv('DB_USER', 'project88_admin'),
                password=os.getenv('DB_PASSWORD', 'securepassword123')
            )
            
            cursor = conn.cursor()
            
            # Extract event data from ProviderEvent
            race_data = event.raw_data.get('race', {})
            event_data = event.raw_data.get('event', {})
            race_id = race_data.get('race_id')
            event_id = event_data.get('event_id')
            
            # Validate required fields
            if not event_id:
                self.logger.error(f"Missing event_id for event {event.provider_event_id}. Raw data keys: {list(event.raw_data.keys())}")
                if event_data:
                    self.logger.error(f"Event data keys: {list(event_data.keys())}")
                return
            
            if not race_id:
                self.logger.error(f"Missing race_id for event {event_id}. Race data keys: {list(race_data.keys()) if race_data else 'No race data'}")
                return
                
            # Store the event using our existing method - pass the extracted event_data dict
            self.store_event(event_data, race_id, conn)
            
            # Commit and close
            conn.commit()
            conn.close()
            
            self.logger.info(f"✅ Successfully stored event {event_id} via _store_event")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to store event {event.provider_event_id} via _store_event: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
    
    def _store_participant(self, participant: ProviderParticipant):
        """Store participant in RunSignUp participants table (called by base class)"""
        try:
            # Get database connection
            import psycopg2
            import os
            
            # Connect to PostgreSQL database
            conn = psycopg2.connect(
                host=os.getenv('DB_HOST', 'localhost'),
                database=os.getenv('DB_NAME', 'project88_myappdb'),
                user=os.getenv('DB_USER', 'project88_admin'),
                password=os.getenv('DB_PASSWORD', 'securepassword123')
            )
            
            cursor = conn.cursor()
            
            # Extract participant data
            participant_data = participant.raw_data
            race_id = participant_data.get('race_id')
            event_id = participant.event_id
            
            # Validate required fields
            if not event_id:
                self.logger.error(f"Missing event_id for participant {participant.provider_participant_id}")
                return
            
            if not race_id:
                self.logger.error(f"Missing race_id for participant {participant.provider_participant_id}")
                return
                
            # Store the participant using our existing method
            self.store_participant(participant_data, race_id, event_id, conn)
            
            # Commit and close
            conn.commit()
            conn.close()
            
            self.logger.debug(f"Successfully stored participant {participant.provider_participant_id} via _store_participant")
            
        except Exception as e:
            self.logger.error(f"Failed to store participant {participant.provider_participant_id} via _store_participant: {e}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()

    def _clean_currency_string(self, value: str) -> float:
        """Convert currency string like '$55.00' to float"""
        if not value:
            return None
        try:
            # Remove currency symbols and convert to float
            cleaned = str(value).replace('$', '').replace(',', '').strip()
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None

    def _parse_runsignup_date(self, date_value) -> Optional[datetime]:
        """Parse RunSignUp date format - handles strings, integers (timestamps), and datetime objects"""
        if not date_value:
            return None
        
        # If it's already a datetime object, return it as-is
        if isinstance(date_value, datetime):
            return date_value
        
        # If it's an integer, treat it as a Unix timestamp
        if isinstance(date_value, int):
            try:
                return datetime.fromtimestamp(date_value)
            except (ValueError, OSError) as e:
                self.logger.warning(f"Could not parse timestamp {date_value}: {e}")
                return None
        
        # If it's a string, try various parsing methods
        if isinstance(date_value, str):
            try:
                # Handle RunSignUp's MM/DD/YYYY HH:MM format
                return datetime.strptime(date_value, "%m/%d/%Y %H:%M")
            except (ValueError, TypeError):
                # Fallback to standard ISO format
                return self._parse_datetime(date_value)
        
        # If it's none of the above, log and return None
        self.logger.warning(f"Unexpected date format: {type(date_value)} - {date_value}")
        return None 