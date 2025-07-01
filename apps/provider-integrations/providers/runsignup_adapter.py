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

from .base_adapter import BaseProviderAdapter, ProviderEvent, ProviderParticipant

class RunSignUpAdapter(BaseProviderAdapter):
    """RunSignUp API adapter"""
    
    BASE_URL = "https://runsignup.com/REST"
    
    def __init__(self, credentials: Dict[str, Any], timing_partner_id: int = None):
        super().__init__(credentials, rate_limit_per_hour=1000)
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
                "results_per_page": 100,
                "page": page,
                "include_event_days": "T"
            }
            
            if last_modified_since:
                # RunSignUp uses last_modified parameter
                params["last_modified"] = last_modified_since.strftime("%Y-%m-%d %H:%M:%S")
            
            response = self._make_runsignup_request("/races", params)
            
            if 'races' not in response:
                break
                
            races = response.get('races', [])
            if not races:
                break
            
            for race_entry in races:
                # Get events for this race
                race_data = race_entry['race']  # Race data is nested under 'race' key
                race_events = self._get_race_events(race_data['race_id'])
                events.extend(race_events)
            
            page += 1
            
            # Break if we've got all pages
            if len(races) < 100:
                break
        
        return events
    
    def get_participants(self, event_id: str, last_modified_since: Optional[datetime] = None) -> List[ProviderParticipant]:
        """Get participants for a specific event"""
        participants = []
        page = 1
        
        while True:
            params = {
                "event_id": event_id,
                "results_per_page": 100,
                "page": page,
                "include_individual_info": "T"
            }
            
            if last_modified_since:
                params["last_modified"] = last_modified_since.strftime("%Y-%m-%d %H:%M:%S")
            
            response = self._make_runsignup_request("/race/participants", params)
            
            if 'participants' not in response:
                break
                
            participant_data = response.get('participants', [])
            if not participant_data:
                break
            
            for p_data in participant_data:
                participant = self._parse_participant(p_data, event_id)
                if participant:
                    participants.append(participant)
            
            page += 1
            
            # Break if we've got all pages
            if len(participant_data) < 100:
                break
        
        return participants
    
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
        
        # Insert or update race
        cursor.execute("""
            INSERT OR REPLACE INTO runsignup_races (
                race_id, name, last_date, last_end_date, next_date, next_end_date,
                is_draft_race, is_private_race, is_registration_open, created, 
                last_modified, description, url, external_race_url, external_results_url,
                fb_page_id, fb_event_id, street, street2, city, state, zipcode,
                country_code, timezone, logo_url, real_time_notifications_enabled,
                fetched_date, credentials_used, timing_partner_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            address.get('street'),
            address.get('street2'),
            address.get('city'),
            address.get('state'),
            address.get('zipcode'),
            address.get('country_code'),
            race_data.get('timezone'),
            race_data.get('logo_url'),
            race_data.get('real_time_notifications_enabled'),
            datetime.now().isoformat(),
            self.api_key,
            self.timing_partner_id
        ))
        
        return race_data.get('race_id')
    
    def store_event(self, event_data: Dict, race_id: int, db_connection) -> int:
        """Store event data in runsignup_events table"""
        from datetime import datetime
        
        cursor = db_connection.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO runsignup_events (
                event_id, race_id, name, details, start_time, end_time,
                age_calc_base_date, registration_opens, event_type, distance,
                volunteer, require_dob, require_phone, giveaway,
                fetched_date, credentials_used, timing_partner_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            event_data.get('distance'),
            event_data.get('volunteer'),
            event_data.get('require_dob'),
            event_data.get('require_phone'),
            event_data.get('giveaway'),
            datetime.now().isoformat(),
            self.api_key,
            self.timing_partner_id
        ))
        
        return event_data.get('event_id')
    
    def store_participant(self, participant_data: Dict, race_id: int, event_id: int, db_connection):
        """Store participant data in runsignup_participants table"""
        from datetime import datetime
        
        cursor = db_connection.cursor()
        
        user_data = participant_data.get('user', {})
        
        cursor.execute("""
            INSERT OR REPLACE INTO runsignup_participants (
                race_id, event_id, registration_id, user_id, first_name, middle_name,
                last_name, email, street, city, state, zipcode, country_code,
                dob, gender, phone, profile_image_url, rsu_transaction_id,
                transaction_id, bib_num, chip_num, age, registration_date,
                team_id, team_name, team_type_id, team_type, team_gender,
                team_bib_num, last_modified, imported, race_fee,
                offline_payment_amount, processing_fee, processing_fee_paid_by_user,
                processing_fee_paid_by_race, partner_fee, affiliate_profit,
                extra_fees, amount_paid, usatf_discount_amount_in_cents,
                usatf_discount_additional_field, giveaway, giveaway_option_id,
                fundraiser_id, fundraiser_charity_id, fundraiser_charity_name,
                team_fundraiser_id, multi_race_bundle_id, multi_race_bundle,
                signed_waiver_details, fetched_date, credentials_used, timing_partner_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            race_id,
            event_id,
            participant_data.get('registration_id'),
            user_data.get('user_id'),
            user_data.get('first_name'),
            user_data.get('middle_name'),
            user_data.get('last_name'),
            user_data.get('email'),
            user_data.get('address', {}).get('street'),
            user_data.get('address', {}).get('city'),
            user_data.get('address', {}).get('state'),
            user_data.get('address', {}).get('zipcode'),
            user_data.get('address', {}).get('country_code'),
            user_data.get('dob'),
            user_data.get('gender'),
            user_data.get('phone'),
            user_data.get('profile_image_url'),
            participant_data.get('rsu_transaction_id'),
            participant_data.get('transaction_id'),
            participant_data.get('bib_num'),
            participant_data.get('chip_num'),
            participant_data.get('age'),
            participant_data.get('registration_date'),
            participant_data.get('team_id'),
            participant_data.get('team_name'),
            participant_data.get('team_type_id'),
            participant_data.get('team_type'),
            participant_data.get('team_gender'),
            participant_data.get('team_bib_num'),
            participant_data.get('last_modified'),
            participant_data.get('imported'),
            participant_data.get('race_fee'),
            participant_data.get('offline_payment_amount'),
            participant_data.get('processing_fee'),
            participant_data.get('processing_fee_paid_by_user'),
            participant_data.get('processing_fee_paid_by_race'),
            participant_data.get('partner_fee'),
            participant_data.get('affiliate_profit'),
            participant_data.get('extra_fees'),
            participant_data.get('amount_paid'),
            participant_data.get('usatf_discount_amount_in_cents'),
            participant_data.get('usatf_discount_additional_field'),
            participant_data.get('giveaway'),
            participant_data.get('giveaway_option_id'),
            participant_data.get('fundraiser_id'),
            participant_data.get('fundraiser_charity_id'),
            participant_data.get('fundraiser_charity_name'),
            participant_data.get('team_fundraiser_id'),
            participant_data.get('multi_race_bundle_id'),
            participant_data.get('multi_race_bundle'),
            participant_data.get('signed_waiver_details'),
            datetime.now().isoformat(),
            self.api_key,
            self.timing_partner_id
        ))
    
    def _store_event(self, event: ProviderEvent):
        """Store event in RunSignUp events table (legacy method for base class)"""
        # This is called by the base class but we handle storage differently
        # The actual storage is done via store_race, store_event, store_participant methods
        pass
    
    def _store_participant(self, participant: ProviderParticipant):
        """Store participant in RunSignUp participants table (legacy method for base class)"""
        # This is called by the base class but we handle storage differently
        # The actual storage is done via store_race, store_event, store_participant methods
        pass 