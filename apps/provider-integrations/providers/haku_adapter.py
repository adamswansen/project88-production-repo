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
        per_page = 500  # Increased from 100 to reduce API calls
        
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
        """Get participants for a specific event using two-step API pattern"""
        participants = []
        page = 1
        per_page = 500  # Increased from 100 to reduce API calls
        
        # Step 1: Get participant list
        self.logger.info(f"🔍 Step 1: Getting participant list for event {event_id}")
        participant_list = []
        
        while True:
            params = {
                "page": page,
                "per_page": per_page,
                "sort_column": "updated_at",
                "sort_direction": "desc"
            }
            
            headers = self._get_auth_headers()
            
            try:
                # Get basic participant list
                response = self._make_api_request(
                    f"{self.BASE_URL}/events/{event_id}/participants",
                    params=params,
                    headers=headers
                )
                
                if response.status_code != 200:
                    self.logger.error(f"Failed to get participant list for event {event_id}: {response.status_code}")
                    break
                
                data = response.json()
                
                # Handle different response formats
                participants_data = data if isinstance(data, list) else data.get('participants', [])
                
                if not participants_data:
                    break
                
                # Collect registration numbers for detailed calls
                for participant_data in participants_data:
                    registration_number = participant_data.get('registration_number')
                    if registration_number:
                        participant_list.append(registration_number)
                
                # Check if there are more pages
                if len(participants_data) < per_page:
                    break
                    
                page += 1
                
            except Exception as e:
                self.logger.error(f"Error fetching participant list for event {event_id}, page {page}: {e}")
                break
        
        self.logger.info(f"📋 Step 1 complete: Found {len(participant_list)} participants")
        
        # Step 2: Get detailed information for each participant
        self.logger.info(f"🔍 Step 2: Getting detailed info for {len(participant_list)} participants")
        
        for i, registration_number in enumerate(participant_list):
            try:
                headers = self._get_auth_headers()
                
                # Get detailed participant information
                response = self._make_api_request(
                    f"{self.BASE_URL}/events/{event_id}/registrations/{registration_number}",
                    headers=headers
                )
                
                if response.status_code != 200:
                    self.logger.warning(f"Failed to get detailed info for participant {registration_number}: {response.status_code}")
                    continue
                
                detailed_data = response.json()
                
                # Parse the detailed participant data
                participant = self._parse_detailed_participant(detailed_data, event_id)
                if participant:
                    # Apply date filter if specified
                    if last_modified_since and participant.registration_date:
                        if participant.registration_date < last_modified_since:
                            continue
                    participants.append(participant)
                
                # Progress logging every 10 participants
                if (i + 1) % 10 == 0:
                    self.logger.info(f"📊 Progress: {i + 1}/{len(participant_list)} participants processed")
                
            except Exception as e:
                self.logger.error(f"Error fetching detailed info for participant {registration_number}: {e}")
                continue
        
        self.logger.info(f"✅ Retrieved complete data for {len(participants)} participants for event {event_id}")
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
            # Split person_full_name into first_name and last_name
            full_name = participant_data.get('person_full_name', '').strip()
            first_name = ''
            last_name = ''
            
            if full_name:
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = ' '.join(name_parts[1:])
                elif len(name_parts) == 1:
                    first_name = name_parts[0]
                    last_name = ''
            
            # Handle team information
            team_data = participant_data.get('team', {})
            team_name = team_data.get('name') if team_data else None
            
            # Convert is_cancelled boolean to status string
            is_cancelled = participant_data.get('is_cancelled', False)
            registration_status = 'cancelled' if is_cancelled else 'active'
            
            # Handle registration date
            registration_date = self._parse_datetime(participant_data.get('registered_at'))
            
            # Create participant object with correct field mappings
            participant = ProviderParticipant(
                provider_participant_id=str(participant_data.get('registration_number', '')),
                event_id=event_id,
                first_name=first_name,
                last_name=last_name,
                email=participant_data.get('email'),
                phone=None,  # Not available in Haku API
                date_of_birth=None,  # Not available in Haku API
                age=participant_data.get('age'),  # Direct age field
                gender=participant_data.get('gender'),
                city=None,  # Not available in Haku API
                state=None,  # Not available in Haku API
                country=None,  # Not available in Haku API
                bib_number=None,  # Not available in Haku API
                emergency_contact=None,  # Not available in Haku API
                team_name=team_name,
                division=participant_data.get('event_category_info'),  # Maps to event category
                registration_date=registration_date,
                registration_status=registration_status,
                payment_status=None,  # Not explicitly available
                amount_paid=participant_data.get('transaction_amount'),
                raw_data=participant_data  # Store complete API response for debugging
            )
            
            return participant
            
        except Exception as e:
            self.logger.error(f"Failed to parse Haku participant {participant_data.get('registration_number', 'unknown')}: {e}")
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
    
    def _parse_detailed_participant(self, detailed_data: Dict, event_id: str) -> Optional[ProviderParticipant]:
        """Parse detailed Haku participant data from registrations endpoint - CAPTURE EVERYTHING"""
        try:
            # Extract participant info from nested structure
            participant_info = detailed_data.get('participant', {})
            
            # Get address information
            address = participant_info.get('address', {})
            
            # Get emergency contact info
            emergency_contact = None
            if detailed_data.get('emergency_contact_name'):
                emergency_contact = {
                    'name': detailed_data.get('emergency_contact_name'),
                    'phone': detailed_data.get('emergency_contact_phone_number'),
                    'relationship': detailed_data.get('emergency_contact_relationship')
                }
            
            # Get event category info (contains bib/tag numbers and more)
            event_categories = detailed_data.get('event_categories', [])
            division = None
            bib_number = None
            event_category_info = {}
            
            if event_categories:
                category = event_categories[0]  # Take first category
                division = category.get('name')
                bib_number = category.get('tag_number') or category.get('chip_number')
                
                # Capture ALL event category fields
                event_category_info = {
                    'id': category.get('id'),
                    'name': category.get('name'),
                    'master_name': category.get('master_name'),
                    'is_active': category.get('is_active'),
                    'participation_option': category.get('participation_option'),
                    'corral_name': category.get('corral_name'),
                    'wave_name': category.get('wave_name'),
                    'wave_code': category.get('wave_code'),
                    'tag_number': category.get('tag_number'),
                    'chip_number': category.get('chip_number'),
                    'created_at': category.get('created_at'),
                    'updated_at': category.get('updated_at')
                }
            
            # Convert is_cancelled boolean to status string
            is_cancelled = detailed_data.get('is_cancelled', False)
            registration_status = 'cancelled' if is_cancelled else 'active'
            
            # Handle registration date
            registration_date = self._parse_datetime(detailed_data.get('created_at'))
            
            # Handle date of birth
            date_of_birth = self._parse_datetime(participant_info.get('dob'))
            
            # Calculate age from date of birth if available
            age = None
            if date_of_birth:
                age = self._calculate_age(participant_info.get('dob'))
            
            # Build comprehensive extended data with ALL available fields
            extended_data = {
                # Participant account info
                'account_number': participant_info.get('account_number'),
                'source_system_identifier': participant_info.get('source_system_identifier'),
                'middle_initial': participant_info.get('middle_initial'),
                'participant_created_at': participant_info.get('created_at'),
                'participant_updated_at': participant_info.get('updated_at'),
                'participant_additional_questions': participant_info.get('additional_questions', []),
                
                # Complete address
                'address_line1': address.get('line1'),
                'address_line2': address.get('line2'),
                'zip_code': address.get('zip_code'),
                
                # Race/Event specific
                'shirt_size_name': detailed_data.get('shirt_size_name'),
                'shirt_size_code': detailed_data.get('shirt_size_code'),
                'current_pace': detailed_data.get('current_pace'),
                'strava_athlete_identification': detailed_data.get('strava_athlete_identification'),
                'formatted_submitted_result_time': detailed_data.get('formatted_submitted_result_time'),
                
                # Fundraising
                'fundraising_option': detailed_data.get('fundraising_option'),
                'fundraised_amount': detailed_data.get('fundraised_amount'),
                'fundraiser_goal': detailed_data.get('fundraiser_goal'),
                
                # Communication preferences
                'wants_sms_communications': detailed_data.get('wants_sms_communications'),
                'subscription_number': detailed_data.get('subscription_number'),
                
                # Team/Club/Partner info
                'team': detailed_data.get('team'),
                'entity': detailed_data.get('entity'),
                'club': detailed_data.get('club'),
                'partner': detailed_data.get('partner'),
                
                # Technical tracking
                'device': detailed_data.get('device'),
                'browser': detailed_data.get('browser'),
                'browser_version': detailed_data.get('browser_version'),
                'os': detailed_data.get('os'),
                'os_version': detailed_data.get('os_version'),
                
                # Event category details
                'event_category_info': event_category_info,
                
                # Registration details
                'registration_updated_at': detailed_data.get('updated_at'),
                'cancelled_at': detailed_data.get('cancelled_at'),
                
                # Products and additional questions
                'products': detailed_data.get('products', []),
                'additional_questions': detailed_data.get('additional_questions', []),
                
                # Complete raw response for future use
                'raw_api_response': detailed_data
            }
            
            # Create participant object with all available fields
            participant = ProviderParticipant(
                provider_participant_id=str(detailed_data.get('registration_number', '')),
                event_id=event_id,
                first_name=participant_info.get('first_name', ''),
                last_name=participant_info.get('last_name', ''),
                email=participant_info.get('email'),
                phone=participant_info.get('phone'),
                date_of_birth=date_of_birth,
                age=age,
                gender=participant_info.get('gender'),
                city=address.get('city'),
                state=address.get('state'),
                country=address.get('country'),
                bib_number=bib_number,
                emergency_contact=emergency_contact,
                team_name=None,  # Will use extended_data.team for full team info
                division=division,
                registration_date=registration_date,
                registration_status=registration_status,
                payment_status=None,  # Not explicitly available
                amount_paid=detailed_data.get('transaction_amount'),
                raw_data=extended_data  # Store ALL additional data here
            )
            
            return participant
            
        except Exception as e:
            self.logger.error(f"Failed to parse detailed Haku participant {detailed_data.get('registration_number', 'unknown')}: {e}")
            return None 