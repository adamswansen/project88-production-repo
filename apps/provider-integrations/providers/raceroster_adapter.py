#!/usr/bin/env python3
"""
Race Roster Provider Adapter for Project88Hub
Implements Race Roster API integration
API Documentation: https://racerosterv1.docs.apiary.io/
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .base_adapter import BaseProviderAdapter, ProviderEvent, ProviderParticipant

class RaceRosterAdapter(BaseProviderAdapter):
    """Race Roster API adapter"""
    
    BASE_URL = "https://raceroster.com/api/v1"
    
    def __init__(self, credentials: Dict[str, Any], timing_partner_id: int = None):
        super().__init__(credentials, rate_limit_per_hour=1000)
        self.timing_partner_id = timing_partner_id
        self.client_id = credentials.get('principal')
        self.client_secret = credentials.get('secret')
        self.access_token = None
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Race Roster requires 'principal' (Client ID) and 'secret' (Client Secret)")
    
    def get_provider_name(self) -> str:
        return "Race Roster"
    
    def authenticate(self) -> bool:
        """Authenticate with Race Roster using OAuth2 client credentials"""
        try:
            auth_url = f"{self.BASE_URL}/oauth/token"
            
            auth_data = {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            response = self._make_api_request(
                auth_url, 
                method='POST', 
                data=auth_data,
                headers={'Content-Type': 'application/json'}
            )
            
            auth_response = response.json()
            
            if 'access_token' in auth_response:
                self.access_token = auth_response['access_token']
                self.logger.info("Race Roster authentication successful")
                return True
            else:
                self.logger.error(f"Race Roster authentication failed: {auth_response}")
                return False
                
        except Exception as e:
            self.logger.error(f"Race Roster authentication error: {e}")
            return False
    
    def get_events(self, last_modified_since: Optional[datetime] = None) -> List[ProviderEvent]:
        """Get events from Race Roster"""
        if not self.access_token and not self.authenticate():
            raise Exception("Authentication required")
        
        events = []
        page = 1
        per_page = 100
        
        while True:
            params = {
                "page": page,
                "per_page": per_page,
                "include": "races"  # Include race details
            }
            
            if last_modified_since:
                params["updated_since"] = last_modified_since.isoformat()
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = self._make_api_request(
                f"{self.BASE_URL}/events",
                params=params,
                headers=headers
            )
            
            data = response.json()
            
            if 'events' not in data or not data['events']:
                break
            
            for event_data in data['events']:
                event = self._parse_event(event_data)
                if event:
                    events.append(event)
            
            # Check if there are more pages
            if len(data['events']) < per_page:
                break
                
            page += 1
        
        return events
    
    def get_participants(self, event_id: str, last_modified_since: Optional[datetime] = None) -> List[ProviderParticipant]:
        """Get participants for a specific event"""
        if not self.access_token and not self.authenticate():
            raise Exception("Authentication required")
        
        participants = []
        page = 1
        per_page = 100
        
        while True:
            params = {
                "page": page,
                "per_page": per_page
            }
            
            if last_modified_since:
                params["updated_since"] = last_modified_since.isoformat()
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            response = self._make_api_request(
                f"{self.BASE_URL}/events/{event_id}/registrations",
                params=params,
                headers=headers
            )
            
            data = response.json()
            
            if 'registrations' not in data or not data['registrations']:
                break
            
            for reg_data in data['registrations']:
                participant = self._parse_participant(reg_data, event_id)
                if participant:
                    participants.append(participant)
            
            # Check if there are more pages
            if len(data['registrations']) < per_page:
                break
                
            page += 1
        
        return participants
    
    def _parse_event(self, event_data: Dict) -> Optional[ProviderEvent]:
        """Parse Race Roster event data into standardized format"""
        try:
            # Race Roster events can have multiple races
            # We'll create events for each race within the event
            races = event_data.get('races', [event_data])  # Fallback to event if no races
            
            parsed_events = []
            for race_data in races:
                event = ProviderEvent(
                    provider_event_id=str(event_data.get('id')),
                    event_name=event_data.get('name', ''),
                    event_description=event_data.get('description'),
                    event_date=self._parse_datetime(event_data.get('start_date')),
                    event_end_date=self._parse_datetime(event_data.get('end_date')),
                    location_name=self._safe_get(event_data, 'venue.name'),
                    location_city=self._safe_get(event_data, 'venue.city'),
                    location_state=self._safe_get(event_data, 'venue.province_state'),
                    event_type=race_data.get('race_type', 'running'),
                    distance=self._parse_distance(race_data.get('distance')),
                    max_participants=event_data.get('registration_limit'),
                    registration_open_date=self._parse_datetime(event_data.get('registration_open_date')),
                    registration_close_date=self._parse_datetime(event_data.get('registration_close_date')),
                    registration_fee=self._safe_get(event_data, 'price'),
                    currency=event_data.get('currency', 'CAD'),  # Race Roster is Canadian
                    status=event_data.get('status', 'active'),
                    raw_data=event_data
                )
                
                return event  # Return first race as primary event
                
        except Exception as e:
            self.logger.error(f"Failed to parse Race Roster event {event_data.get('id')}: {e}")
            return None
    
    def _parse_participant(self, registration_data: Dict, event_id: str) -> Optional[ProviderParticipant]:
        """Parse Race Roster participant data into standardized format"""
        try:
            participant_data = registration_data.get('participant', {})
            
            # Handle emergency contact
            emergency_contact = None
            if participant_data.get('emergency_contact_name') or participant_data.get('emergency_contact_phone'):
                emergency_contact = {
                    'name': participant_data.get('emergency_contact_name'),
                    'phone': participant_data.get('emergency_contact_phone'),
                    'relationship': participant_data.get('emergency_contact_relationship')
                }
            
            participant = ProviderParticipant(
                provider_participant_id=str(registration_data.get('id')),
                event_id=event_id,
                bib_number=registration_data.get('bib_number'),
                first_name=participant_data.get('first_name', ''),
                last_name=participant_data.get('last_name', ''),
                email=participant_data.get('email'),
                phone=participant_data.get('phone'),
                date_of_birth=self._parse_datetime(participant_data.get('date_of_birth')),
                gender=participant_data.get('gender'),
                age=self._calculate_age(participant_data.get('date_of_birth')),
                city=participant_data.get('city'),
                state=participant_data.get('province_state'),
                country=participant_data.get('country', 'CA'),
                emergency_contact=emergency_contact,
                team_name=registration_data.get('team_name'),
                division=registration_data.get('division'),
                registration_date=self._parse_datetime(registration_data.get('created_at')),
                registration_status=registration_data.get('status', 'registered'),
                payment_status=registration_data.get('payment_status'),
                amount_paid=self._safe_get(registration_data, 'total_paid'),
                raw_data=registration_data
            )
            
            return participant
            
        except Exception as e:
            self.logger.error(f"Failed to parse Race Roster participant {registration_data.get('id')}: {e}")
            return None
    
    def _parse_distance(self, distance_str: str) -> Optional[float]:
        """Parse distance string to float (kilometers)"""
        if not distance_str:
            return None
        
        try:
            # Handle common distance formats
            distance_str = distance_str.lower().replace(' ', '')
            
            if 'km' in distance_str:
                return float(distance_str.replace('km', ''))
            elif 'mile' in distance_str or 'mi' in distance_str:
                miles = float(distance_str.replace('mile', '').replace('mi', ''))
                return miles * 1.60934  # Convert to kilometers
            elif 'm' in distance_str and 'km' not in distance_str:
                meters = float(distance_str.replace('m', ''))
                return meters / 1000  # Convert to kilometers
            else:
                # Try to parse as plain number (assume kilometers)
                return float(distance_str)
                
        except (ValueError, TypeError):
            return None
    
    def _calculate_age(self, birth_date_str: str) -> Optional[int]:
        """Calculate age from birth date"""
        if not birth_date_str:
            return None
        
        try:
            birth_date = self._parse_datetime(birth_date_str)
            if birth_date:
                today = datetime.now()
                age = today.year - birth_date.year
                if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
                    age -= 1
                return age
        except:
            pass
        
        return None
    
    def _store_event(self, event: ProviderEvent):
        """Store event in Race Roster events table"""
        # This would be implemented by the sync worker
        self.logger.debug(f"Would store Race Roster event: {event.provider_event_id} - {event.event_name}")
    
    def _store_participant(self, participant: ProviderParticipant):
        """Store participant in Race Roster participants table"""
        # This would be implemented by the sync worker
        self.logger.debug(f"Would store Race Roster participant: {participant.provider_participant_id} - {participant.first_name} {participant.last_name}") 