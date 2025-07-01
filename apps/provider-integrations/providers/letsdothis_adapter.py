#!/usr/bin/env python3
"""
Let's Do This Provider Adapter for Project88Hub
Implements Let's Do This API integration
API Documentation: https://docs.api.letsdothis.com
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .base_adapter import BaseProviderAdapter, ProviderEvent, ProviderParticipant

class LetsDoThisAdapter(BaseProviderAdapter):
    """Let's Do This API adapter"""
    
    BASE_URL = "https://api.letsdothis.com/v0"
    
    def __init__(self, credentials: Dict[str, Any], timing_partner_id: int = None):
        super().__init__(credentials, rate_limit_per_hour=1000)
        self.timing_partner_id = timing_partner_id
        self.api_key = credentials.get('principal')  # JWT API Key
        
        if not self.api_key:
            raise ValueError("Let's Do This requires 'principal' (API Key/JWT Token)")
    
    def get_provider_name(self) -> str:
        return "Let's Do This"
    
    def authenticate(self) -> bool:
        """Test authentication with Let's Do This API"""
        try:
            headers = self._get_auth_headers()
            
            # Test with applications endpoint
            response = self._make_api_request(
                f"{self.BASE_URL}/applications",
                params={"page[size]": 1},
                headers=headers
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Let's Do This authentication failed: {e}")
            return False
    
    def get_events(self, last_modified_since: Optional[datetime] = None) -> List[ProviderEvent]:
        """Get events from Let's Do This (via applications)"""
        events = []
        cursor = None
        
        while True:
            params = {
                "page[size]": 100
            }
            
            if cursor:
                params["page[after]"] = cursor
            
            if last_modified_since:
                params["updatedAt[after]"] = last_modified_since.isoformat()
            
            headers = self._get_auth_headers()
            
            response = self._make_api_request(
                f"{self.BASE_URL}/applications",
                params=params,
                headers=headers
            )
            
            data = response.json()
            
            if 'data' not in data or not data['data']:
                break
            
            for app_data in data['data']:
                event = self._parse_event_from_application(app_data)
                if event:
                    events.append(event)
            
            # Check for next page using cursor pagination
            page_info = data.get('page', {})
            cursor = page_info.get('next')
            
            if not cursor:
                break
        
        return events
    
    def get_participants(self, event_id: str, last_modified_since: Optional[datetime] = None) -> List[ProviderParticipant]:
        """Get participants for a specific event"""
        participants = []
        cursor = None
        
        while True:
            params = {
                "page[size]": 100
            }
            
            if cursor:
                params["page[after]"] = cursor
            
            if last_modified_since:
                params["updatedAt[after]"] = last_modified_since.isoformat()
            
            headers = self._get_auth_headers()
            
            # Let's Do This uses applications for participants
            # We need to filter by event
            response = self._make_api_request(
                f"{self.BASE_URL}/applications",
                params=params,
                headers=headers
            )
            
            data = response.json()
            
            if 'data' not in data or not data['data']:
                break
            
            for app_data in data['data']:
                # Filter for this specific event
                if str(app_data.get('eventId')) == str(event_id):
                    participant = self._parse_participant_from_application(app_data, event_id)
                    if participant:
                        participants.append(participant)
            
            # Check for next page using cursor pagination
            page_info = data.get('page', {})
            cursor = page_info.get('next')
            
            if not cursor:
                break
        
        return participants
    
    def _parse_event_from_application(self, app_data: Dict) -> Optional[ProviderEvent]:
        """Parse Let's Do This application data to extract event information"""
        try:
            # Get event details - might need separate API call
            event_id = app_data.get('eventId')
            if not event_id:
                return None
            
            # For now, create event from application data
            # In a full implementation, you'd call /events/{eventId} for complete details
            event = ProviderEvent(
                provider_event_id=str(event_id),
                event_name=app_data.get('eventName', ''),
                event_description=None,  # Would need separate API call
                event_date=self._parse_datetime(app_data.get('eventDate')),
                event_end_date=None,  # Would need separate API call
                location_name=app_data.get('eventLocation'),
                location_city=None,  # Would need separate API call
                location_state=None,  # Would need separate API call
                event_type='running',  # Let's Do This is primarily running events
                distance=None,  # Would need separate API call
                max_participants=None,  # Would need separate API call
                registration_open_date=None,  # Would need separate API call
                registration_close_date=None,  # Would need separate API call
                registration_fee=None,  # Would need separate API call
                currency='GBP',  # Let's Do This is UK-based
                status='active',
                raw_data=app_data
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"Failed to parse Let's Do This event from application {app_data.get('id')}: {e}")
            return None
    
    def _parse_participant_from_application(self, app_data: Dict, event_id: str) -> Optional[ProviderParticipant]:
        """Parse Let's Do This application data into participant format"""
        try:
            participant = ProviderParticipant(
                provider_participant_id=str(app_data.get('id')),
                event_id=event_id,
                bib_number=None,  # Not typically available in applications
                first_name=app_data.get('firstName', ''),
                last_name=app_data.get('lastName', ''),
                email=app_data.get('email'),
                phone=app_data.get('phone'),
                date_of_birth=self._parse_datetime(app_data.get('dateOfBirth')),
                gender=app_data.get('gender'),
                age=self._calculate_age(app_data.get('dateOfBirth')),
                city=app_data.get('city'),
                state=app_data.get('region'),
                country=app_data.get('country', 'GB'),  # Default to UK
                emergency_contact=self._parse_emergency_contact(app_data),
                team_name=app_data.get('teamName'),
                division=app_data.get('category'),
                registration_date=self._parse_datetime(app_data.get('applicationDate')),
                registration_status=app_data.get('status', 'registered'),
                payment_status=app_data.get('paymentStatus'),
                amount_paid=self._safe_get(app_data, 'amountPaid'),
                raw_data=app_data
            )
            
            return participant
            
        except Exception as e:
            self.logger.error(f"Failed to parse Let's Do This participant {app_data.get('id')}: {e}")
            return None
    
    def _parse_emergency_contact(self, app_data: Dict) -> Optional[Dict]:
        """Parse emergency contact information"""
        emergency_contact = None
        
        if app_data.get('emergencyContactName') or app_data.get('emergencyContactPhone'):
            emergency_contact = {
                'name': app_data.get('emergencyContactName'),
                'phone': app_data.get('emergencyContactPhone'),
                'relationship': app_data.get('emergencyContactRelationship')
            }
        
        return emergency_contact
    
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
    
    def get_event_details(self, event_id: str) -> Optional[Dict]:
        """Get detailed event information"""
        try:
            headers = self._get_auth_headers()
            
            # Get event tickets for more details
            response = self._make_api_request(
                f"{self.BASE_URL}/events/{event_id}/tickets",
                headers=headers
            )
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Failed to get Let's Do This event details for {event_id}: {e}")
            return None
    
    def get_event_participants_detailed(self, event_id: str) -> List[ProviderParticipant]:
        """Get participants using the dedicated participants endpoint"""
        participants = []
        cursor = None
        
        try:
            while True:
                params = {
                    "page[size]": 100
                }
                
                if cursor:
                    params["page[after]"] = cursor
                
                headers = self._get_auth_headers()
                
                response = self._make_api_request(
                    f"{self.BASE_URL}/participants",
                    params=params,
                    headers=headers
                )
                
                data = response.json()
                
                if 'data' not in data or not data['data']:
                    break
                
                for participant_data in data['data']:
                    # Filter for this specific event if needed
                    participant = self._parse_participant_detailed(participant_data, event_id)
                    if participant:
                        participants.append(participant)
                
                # Check for next page
                page_info = data.get('page', {})
                cursor = page_info.get('next')
                
                if not cursor:
                    break
        
        except Exception as e:
            self.logger.error(f"Failed to get detailed participants for event {event_id}: {e}")
        
        return participants
    
    def _parse_participant_detailed(self, participant_data: Dict, event_id: str) -> Optional[ProviderParticipant]:
        """Parse detailed participant data"""
        try:
            participant = ProviderParticipant(
                provider_participant_id=str(participant_data.get('id')),
                event_id=event_id,
                bib_number=participant_data.get('bibNumber'),
                first_name=participant_data.get('firstName', ''),
                last_name=participant_data.get('lastName', ''),
                email=participant_data.get('email'),
                phone=participant_data.get('phone'),
                date_of_birth=self._parse_datetime(participant_data.get('dateOfBirth')),
                gender=participant_data.get('gender'),
                age=self._calculate_age(participant_data.get('dateOfBirth')),
                city=participant_data.get('city'),
                state=participant_data.get('region'),
                country=participant_data.get('country', 'GB'),
                emergency_contact=self._parse_emergency_contact(participant_data),
                team_name=participant_data.get('teamName'),
                division=participant_data.get('division'),
                registration_date=self._parse_datetime(participant_data.get('registrationDate')),
                registration_status=participant_data.get('status', 'registered'),
                payment_status=participant_data.get('paymentStatus'),
                amount_paid=self._safe_get(participant_data, 'amountPaid'),
                raw_data=participant_data
            )
            
            return participant
            
        except Exception as e:
            self.logger.error(f"Failed to parse detailed Let's Do This participant {participant_data.get('id')}: {e}")
            return None
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Let's Do This API"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _store_event(self, event: ProviderEvent):
        """Store event in Let's Do This events table"""
        # This would be implemented by the sync worker
        self.logger.debug(f"Would store Let's Do This event: {event.provider_event_id} - {event.event_name}")
    
    def _store_participant(self, participant: ProviderParticipant):
        """Store participant in Let's Do This participants table"""
        # This would be implemented by the sync worker
        self.logger.debug(f"Would store Let's Do This participant: {participant.provider_participant_id} - {participant.first_name} {participant.last_name}") 