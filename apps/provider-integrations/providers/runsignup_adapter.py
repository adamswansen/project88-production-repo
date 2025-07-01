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
    
    def _store_event(self, event: ProviderEvent):
        """Store event in RunSignUp events table"""
        # This would be implemented by the sync worker
        # For now, just log that we would store it
        self.logger.debug(f"Would store RunSignUp event: {event.provider_event_id} - {event.event_name}")
    
    def _store_participant(self, participant: ProviderParticipant):
        """Store participant in RunSignUp participants table"""
        # This would be implemented by the sync worker
        # For now, just log that we would store it
        self.logger.debug(f"Would store RunSignUp participant: {participant.provider_participant_id} - {participant.first_name} {participant.last_name}") 