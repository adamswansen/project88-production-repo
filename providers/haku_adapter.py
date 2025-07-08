#!/usr/bin/env python3
"""
Haku Provider Adapter for Project88Hub
Implements Haku API integration using OAuth2 client credentials flow
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import requests
import base64

from .base_adapter import BaseProviderAdapter, ProviderEvent, ProviderParticipant

class HakuAdapter(BaseProviderAdapter):
    """Haku API adapter using OAuth2 client credentials authentication"""
    
    # Production API URLs
    BASE_URL = "https://api.hakuapp.com"  # Production API
    AUTH_URL = "https://prod-auth.hakuapp.com/oauth2/token"  # OAuth2 token endpoint
    
    def __init__(self, credentials: Dict[str, Any], timing_partner_id: int = None):
        super().__init__(credentials, rate_limit_per_hour=500)  # Conservative rate limit
        self.timing_partner_id = timing_partner_id
        
        # Map credentials from partner_provider_credentials format
        self.client_id = credentials.get('principal')  # Client ID stored as principal
        self.client_secret = credentials.get('secret')  # Client secret stored as secret
        self.organization_id = credentials.get('additional_config', {}).get('organization_name')
        
        # Legacy support for old format
        if not self.client_id:
            self.client_id = credentials.get('client_id')
            
        if not self.client_secret:
            self.client_secret = credentials.get('client_secret')
            
        if not self.organization_id:
            self.organization_id = credentials.get('haku_event_name')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Haku requires 'principal' (client_id) and 'secret' (client_secret)")
        
        # OAuth2 token management
        self.access_token = None
        self.token_expires_at = None
    
    def get_provider_name(self) -> str:
        return "Haku"
    
    def _get_access_token(self) -> str:
        """Get or refresh OAuth2 access token"""
        # Check if we have a valid token
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at - timedelta(minutes=5):  # 5 min buffer
                return self.access_token
        
        # Get new access token
        auth_string = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        data = {
            'grant_type': 'client_credentials'
        }
        
        try:
            response = requests.post(self.AUTH_URL, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            
            # Calculate expiration time
            expires_in = token_data.get('expires_in', 3600)  # Default 1 hour
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            self.logger.info(f"✅ Got new Haku access token (expires in {expires_in}s)")
            return self.access_token
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get Haku access token: {e}")
            raise
    
    def authenticate(self) -> bool:
        """Test authentication with Haku API"""
        try:
            access_token = self._get_access_token()
            headers = self._get_auth_headers()
            
            # Test with events endpoint (lightweight check)
            response = self._make_api_request(
                f"{self.BASE_URL}/events",
                headers=headers,
                params={"page": 1, "per_page": 1}
            )
            
            return response.status_code == 200
            
        except Exception as e:
            self.logger.error(f"Haku authentication failed: {e}")
            return False
    
    def get_events(self, last_modified_since: Optional[datetime] = None) -> List[ProviderEvent]:
        """Get events from Haku API"""
        events = []
        page = 1
        per_page = 25  # Maximum allowed by API
        
        while True:
            params = {
                "page": page,
                "per_page": per_page,
                "sort_column": "event_date",
                "sort_direction": "desc",
                "show_inactive": "true"  # Include all events
            }
            
            headers = self._get_auth_headers()
            
            try:
                response = self._make_api_request(
                    f"{self.BASE_URL}/events",
                    params=params,
                    headers=headers
                )
                
                if response.status_code != 200:
                    self.logger.error(f"Failed to get events: {response.status_code} - {response.text}")
                    break
                
                data = response.json()
                
                # Handle different response formats
                events_data = data if isinstance(data, list) else data.get('events', [])
                
                if not events_data:
                    break
                
                for event_data in events_data:
                    event = self._parse_event(event_data)
                    if event:
                        # Apply date filter if specified
                        if last_modified_since and event.event_date:
                            if event.event_date < last_modified_since:
                                continue
                        events.append(event)
                
                # Check if there are more pages
                if len(events_data) < per_page:
                    break
                    
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error fetching events page {page}: {e}")
                break
        
        self.logger.info(f"Retrieved {len(events)} events from Haku")
        return events
    
    def get_participants(self, event_id: str, last_modified_since: Optional[datetime] = None) -> List[ProviderParticipant]:
        """Get participants for a specific event"""
        participants = []
        page = 1
        per_page = 25  # Maximum allowed by API
        
        while True:
            params = {
                "page": page,
                "per_page": per_page,
                "sort_column": "updated_at",
                "sort_direction": "desc"
            }
            
            headers = self._get_auth_headers()
            
            try:
                # Correct endpoint: /events/{id}/participants
                response = self._make_api_request(
                    f"{self.BASE_URL}/events/{event_id}/participants",
                    params=params,
                    headers=headers
                )
                
                if response.status_code != 200:
                    self.logger.error(f"Failed to get participants for event {event_id}: {response.status_code}")
                    break
                
                data = response.json()
                
                # Handle different response formats
                participants_data = data if isinstance(data, list) else data.get('participants', [])
                
                if not participants_data:
                    break
                
                for participant_data in participants_data:
                    participant = self._parse_participant(participant_data, event_id)
                    if participant:
                        # Apply date filter if specified
                        if last_modified_since and participant.registration_date:
                            if participant.registration_date < last_modified_since:
                                continue
                        participants.append(participant)
                
                # Check if there are more pages
                if len(participants_data) < per_page:
                    break
                    
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error fetching participants for event {event_id}, page {page}: {e}")
                break
        
        self.logger.info(f"Retrieved {len(participants)} participants for event {event_id}")
        return participants
    
    def _parse_event(self, event_data: Dict) -> Optional[ProviderEvent]:
        """Parse Haku event data into standardized format"""
        try:
            event = ProviderEvent(
                provider_event_id=str(event_data.get('id')),
                event_name=event_data.get('name', ''),
                event_description=event_data.get('description'),
                event_date=self._parse_datetime(event_data.get('event_date')),
                event_end_date=self._parse_datetime(event_data.get('event_end_date')),
                location_name=event_data.get('location_name'),
                location_city=event_data.get('location_city'),
                location_state=event_data.get('location_state'),
                # Note: location_country is not supported by ProviderEvent model
                event_type=event_data.get('event_type', 'running'),
                distance=self._parse_distance(event_data.get('distance')),
                max_participants=event_data.get('registration_limit'),
                registration_open_date=self._parse_datetime(event_data.get('registration_open_date')),
                registration_close_date=self._parse_datetime(event_data.get('registration_close_date')),
                registration_fee=self._parse_fee(event_data.get('base_price')),
                currency=event_data.get('currency', 'USD'),
                status=event_data.get('status', 'active'),
                raw_data=event_data
            )
            
            return event
            
        except Exception as e:
            self.logger.error(f"Failed to parse Haku event {event_data.get('id', 'unknown')}: {e}")
            return None
    
    def _parse_participant(self, participant_data: Dict, event_id: str) -> Optional[ProviderParticipant]:
        """Parse Haku participant data into standardized format"""
        try:
            # Handle emergency contact
            emergency_contact = None
            if participant_data.get('emergency_contact_name'):
                emergency_contact = {
                    'name': participant_data.get('emergency_contact_name'),
                    'phone': participant_data.get('emergency_contact_phone'),
                    'relationship': participant_data.get('emergency_contact_relationship')
                }
            
            participant = ProviderParticipant(
                provider_participant_id=str(participant_data.get('id')),
                event_id=event_id,
                first_name=participant_data.get('first_name', ''),
                last_name=participant_data.get('last_name', ''),
                email=participant_data.get('email'),
                phone=participant_data.get('phone'),
                date_of_birth=self._parse_datetime(participant_data.get('birth_date')),
                age=self._calculate_age(participant_data.get('birth_date')),
                gender=participant_data.get('gender'),
                city=participant_data.get('city'),
                state=participant_data.get('state'),
                country=participant_data.get('country'),
                bib_number=participant_data.get('bib_number'),
                emergency_contact=emergency_contact,
                team_name=participant_data.get('team_name'),
                division=participant_data.get('division'),
                registration_date=self._parse_datetime(participant_data.get('created_at')),
                registration_status=participant_data.get('status', 'active'),
                payment_status=participant_data.get('payment_status'),
                amount_paid=self._parse_fee(participant_data.get('amount_paid')),
                raw_data=participant_data
            )
            
            return participant
            
        except Exception as e:
            self.logger.error(f"Failed to parse Haku participant {participant_data.get('id', 'unknown')}: {e}")
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
    
    def _parse_distance(self, distance_data: Any) -> Optional[float]:
        """Parse distance data into float (in miles)"""
        if distance_data is None:
            return None
        
        try:
            if isinstance(distance_data, (int, float)):
                return float(distance_data)
            elif isinstance(distance_data, str):
                # Handle common distance formats
                distance_str = distance_data.lower()
                
                # Convert common race distances
                if 'marathon' in distance_str:
                    return 26.2
                elif 'half' in distance_str:
                    return 13.1
                elif '10k' in distance_str:
                    return 6.2
                elif '5k' in distance_str:
                    return 3.1
                
                # Try to extract numeric value
                numeric_part = ''.join(c for c in distance_str if c.isdigit() or c == '.')
                if numeric_part:
                    distance = float(numeric_part)
                    # Convert km to miles if needed
                    if 'km' in distance_str:
                        distance = distance * 0.621371
                    return distance
                
            return None
            
        except (ValueError, TypeError):
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
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        access_token = self._get_access_token()
        
        return {
            'Authorization': f'{access_token}',  # Direct token format, not Bearer
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _store_event(self, event: ProviderEvent):
        """Store event in database (implementation depends on database setup)"""
        # This would be implemented based on your database schema
        pass
    
    def _store_participant(self, participant: ProviderParticipant):
        """Store participant in database (implementation depends on database setup)"""
        # This would be implemented based on your database schema
        pass 