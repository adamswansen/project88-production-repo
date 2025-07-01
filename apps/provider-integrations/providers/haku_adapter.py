#!/usr/bin/env python3
"""
Haku Provider Adapter for Project88Hub
Implements Haku API integration
API Documentation: https://api.hakuapp.com/v1/docs
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .base_adapter import BaseProviderAdapter, ProviderEvent, ProviderParticipant

class HakuAdapter(BaseProviderAdapter):
    """Haku API adapter"""
    
    BASE_URL = "https://api.hakuapp.com/v1"
    
    def __init__(self, credentials: Dict[str, Any], timing_partner_id: int = None):
        super().__init__(credentials, rate_limit_per_hour=500)  # Haku has lower rate limits
        self.timing_partner_id = timing_partner_id
        self.api_key = credentials.get('principal')
        self.api_secret = credentials.get('secret')
        self.organization_id = credentials.get('haku_event_name')  # This maps to organization
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Haku requires 'principal' (API Key) and 'secret' (API Secret)")
    
    def get_provider_name(self) -> str:
        return "Haku"
    
    def authenticate(self) -> bool:
        """Test authentication with Haku API"""
        try:
            headers = self._get_auth_headers()
            
            # Test with organization info endpoint
            response = self._make_api_request(
                f"{self.BASE_URL}/organizations",
                headers=headers
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Haku authentication failed: {e}")
            return False
    
    def get_events(self, last_modified_since: Optional[datetime] = None) -> List[ProviderEvent]:
        """Get events from Haku"""
        events = []
        page = 1
        per_page = 50  # Haku typically uses smaller page sizes
        
        while True:
            params = {
                "page": page,
                "per_page": per_page
            }
            
            # Add organization filter if specified
            if self.organization_id:
                params["organization_id"] = self.organization_id
            
            if last_modified_since:
                params["updated_since"] = last_modified_since.isoformat()
            
            headers = self._get_auth_headers()
            
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
        participants = []
        page = 1
        per_page = 50
        
        while True:
            params = {
                "page": page,
                "per_page": per_page
            }
            
            if last_modified_since:
                params["updated_since"] = last_modified_since.isoformat()
            
            headers = self._get_auth_headers()
            
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
        """Parse Haku event data into standardized format"""
        try:
            # Haku events structure
            event = ProviderEvent(
                provider_event_id=str(event_data.get('id')),
                event_name=event_data.get('name', ''),
                event_description=event_data.get('description'),
                event_date=self._parse_datetime(event_data.get('start_date')),
                event_end_date=self._parse_datetime(event_data.get('end_date')),
                location_name=self._safe_get(event_data, 'venue.name'),
                location_city=self._safe_get(event_data, 'venue.city'),
                location_state=self._safe_get(event_data, 'venue.state'),
                event_type=event_data.get('event_type', 'running'),
                distance=self._parse_distance(event_data.get('distance')),
                max_participants=event_data.get('registration_limit'),
                registration_open_date=self._parse_datetime(event_data.get('registration_opens_at')),
                registration_close_date=self._parse_datetime(event_data.get('registration_closes_at')),
                registration_fee=self._safe_get(event_data, 'registration_fee'),
                currency=event_data.get('currency', 'USD'),
                status=event_data.get('status', 'active'),
                raw_data=event_data
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"Failed to parse Haku event {event_data.get('id')}: {e}")
            return None
    
    def _parse_participant(self, registration_data: Dict, event_id: str) -> Optional[ProviderParticipant]:
        """Parse Haku participant data into standardized format"""
        try:
            participant_data = registration_data.get('participant', {})
            
            # Handle emergency contact
            emergency_contact = None
            if participant_data.get('emergency_contact'):
                emergency_contact = participant_data.get('emergency_contact')
            
            # Parse custom fields that might contain additional info
            custom_fields = registration_data.get('custom_fields', {})
            team_name = custom_fields.get('team_name') or registration_data.get('team_name')
            
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
                city=self._safe_get(participant_data, 'address.city'),
                state=self._safe_get(participant_data, 'address.state'),
                country=self._safe_get(participant_data, 'address.country', 'US'),
                emergency_contact=emergency_contact,
                team_name=team_name,
                division=registration_data.get('category'),
                registration_date=self._parse_datetime(registration_data.get('created_at')),
                registration_status=registration_data.get('status', 'registered'),
                payment_status=registration_data.get('payment_status'),
                amount_paid=self._safe_get(registration_data, 'amount_paid'),
                raw_data=registration_data
            )
            
            return participant
            
        except Exception as e:
            self.logger.error(f"Failed to parse Haku participant {registration_data.get('id')}: {e}")
            return None
    
    def _parse_distance(self, distance_data: Any) -> Optional[float]:
        """Parse distance data to float (kilometers)"""
        if not distance_data:
            return None
        
        try:
            if isinstance(distance_data, (int, float)):
                return float(distance_data)
            
            if isinstance(distance_data, str):
                # Handle string distances
                distance_str = distance_data.lower().replace(' ', '')
                
                if 'km' in distance_str:
                    return float(distance_str.replace('km', ''))
                elif 'mile' in distance_str or 'mi' in distance_str:
                    miles = float(distance_str.replace('mile', '').replace('mi', ''))
                    return miles * 1.60934  # Convert to kilometers
                elif 'm' in distance_str and 'km' not in distance_str:
                    meters = float(distance_str.replace('m', ''))
                    return meters / 1000  # Convert to kilometers
                else:
                    # Try to parse as plain number
                    return float(distance_str)
            
            # If it's a dict, look for distance value
            if isinstance(distance_data, dict):
                return self._safe_get(distance_data, 'value') or self._safe_get(distance_data, 'distance')
                
        except (ValueError, TypeError):
            pass
        
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
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for Haku API"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-API-Secret": self.api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _store_event(self, event: ProviderEvent):
        """Store event in Haku events table"""
        # This would be implemented by the sync worker
        self.logger.debug(f"Would store Haku event: {event.provider_event_id} - {event.event_name}")
    
    def _store_participant(self, participant: ProviderParticipant):
        """Store participant in Haku participants table"""
        # This would be implemented by the sync worker
        self.logger.debug(f"Would store Haku participant: {participant.provider_participant_id} - {participant.first_name} {participant.last_name}") 