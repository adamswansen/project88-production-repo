#!/usr/bin/env python3
"""
Base Provider Adapter for Project88Hub
Defines the interface for all provider integrations
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pickle
import os

logger = logging.getLogger('ProviderAdapter')

# Global shared rate limiters for each provider
_SHARED_RATE_LIMITERS = {}

@dataclass
@dataclass
class ProviderEvent:
    """Standardized event data structure"""
    provider_event_id: str
    event_name: str
    event_description: Optional[str]
    event_date: datetime
    event_end_date: Optional[datetime]
    location_name: Optional[str]
    location_city: Optional[str]
    location_state: Optional[str]
    event_type: Optional[str]
    distance: Optional[float]
    max_participants: Optional[int]
    registration_open_date: Optional[datetime]
    registration_close_date: Optional[datetime]
    registration_fee: Optional[float]
    currency: Optional[str]
    status: Optional[str]
    raw_data: Dict

    def to_dict(self) -> Dict:
        """Convert ProviderEvent to dictionary with proper datetime serialization"""
        from dataclasses import asdict
        result = asdict(self)
        
        # Convert datetime objects to ISO strings
        datetime_fields = [
            'event_date', 'event_end_date', 'registration_open_date', 
            'registration_close_date'
        ]
        
        for field in datetime_fields:
            if field in result and result[field] is not None:
                if hasattr(result[field], 'isoformat'):
                    result[field] = result[field].isoformat()
        
        return result

    def to_dict(self) -> Dict:
        """Convert ProviderEvent to dictionary with proper datetime serialization"""
        from dataclasses import asdict
        result = asdict(self)
        
        # Convert datetime objects to ISO strings
        datetime_fields = [
            'event_date', 'event_end_date', 'registration_open_date', 
            'registration_close_date'
        ]
        
        for field in datetime_fields:
            if field in result and result[field] is not None:
                if hasattr(result[field], 'isoformat'):
                    result[field] = result[field].isoformat()
        
        return result
    
    def to_dict(self) -> Dict:
        """Convert ProviderEvent to dictionary for storage"""
        return {
            'provider_event_id': self.provider_event_id,
            'event_name': self.event_name,
            'event_description': self.event_description,
            'event_date': self.event_date,
            'event_end_date': self.event_end_date,
            'location_name': self.location_name,
            'location_city': self.location_city,
            'location_state': self.location_state,
            'event_type': self.event_type,
            'distance': self.distance,
            'max_participants': self.max_participants,
            'registration_open_date': self.registration_open_date,
            'registration_close_date': self.registration_close_date,
            'registration_fee': self.registration_fee,
            'currency': self.currency,
            'status': self.status,
            'raw_data': self.raw_data
        }

@dataclass
class ProviderParticipant:
    """Standardized participant data structure"""
    provider_participant_id: str
    event_id: str
    bib_number: Optional[str]
    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]
    date_of_birth: Optional[datetime]
    gender: Optional[str]
    age: Optional[int]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    emergency_contact: Optional[Dict]
    team_name: Optional[str]
    division: Optional[str]
    registration_date: Optional[datetime]
    registration_status: Optional[str]
    payment_status: Optional[str]
    amount_paid: Optional[float]
    raw_data: Dict
    
    def to_dict(self) -> Dict:
        """Convert ProviderParticipant to dictionary for storage"""
        return {
            'provider_participant_id': self.provider_participant_id,
            'event_id': self.event_id,
            'bib_number': self.bib_number,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'age': self.age,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'emergency_contact': self.emergency_contact,
            'team_name': self.team_name,
            'division': self.division,
            'registration_date': self.registration_date,
            'registration_status': self.registration_status,
            'payment_status': self.payment_status,
            'amount_paid': self.amount_paid,
            'raw_data': self.raw_data
        }

@dataclass
class SyncResult:
    """Result of a sync operation"""
    success: bool
    total_records: int
    processed_records: int
    error_count: int
    errors: List[str]
    sync_type: str
    provider_name: str
    event_id: Optional[str]
    duration_seconds: float
    last_modified_filter: Optional[datetime]

class RateLimiter:
    """Simple rate limiter for API calls with persistence"""
    
    def __init__(self, max_calls_per_hour: int, provider_name: str = "default"):
        self.max_calls_per_hour = max_calls_per_hour
        self.provider_name = provider_name
        self.cache_file = f"/tmp/rate_limiter_{provider_name.lower()}.pkl"
        self.calls = self._load_calls()
        
    def _load_calls(self) -> List[datetime]:
        """Load call history from disk"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    calls = pickle.load(f)
                    # Only keep calls from last hour
                    now = datetime.now()
                    calls = [call for call in calls if (now - call).total_seconds() < 3600]
                    return calls
        except Exception as e:
            logger.warning(f"Failed to load rate limiter cache: {e}")
        return []
    
    def _save_calls(self):
        """Save call history to disk"""
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.calls, f)
        except Exception as e:
            logger.warning(f"Failed to save rate limiter cache: {e}")
        
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = datetime.now()
        
        # Remove calls older than 1 hour
        old_calls_count = len(self.calls)
        self.calls = [call_time for call_time in self.calls 
                     if (now - call_time).total_seconds() < 3600]
        new_calls_count = len(self.calls)
        
        if old_calls_count != new_calls_count:
            logger.info(f"Rate limiter ({self.provider_name}): Removed {old_calls_count - new_calls_count} old calls, {new_calls_count} recent calls remaining")
        
        # Check if we're at the limit BEFORE making the call
        logger.info(f"Rate limiter ({self.provider_name}): {new_calls_count}/{self.max_calls_per_hour} calls in last hour")
        
        # Wait if we would exceed the limit by making this call
        if len(self.calls) >= self.max_calls_per_hour:
            # Wait until the oldest call is more than 1 hour old
            oldest_call = min(self.calls)
            wait_time = 3600 - (now - oldest_call).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached for {self.provider_name}, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
                
                # After waiting, refresh the call list and get new 'now' time
                now = datetime.now()
                self.calls = [call_time for call_time in self.calls 
                             if (now - call_time).total_seconds() < 3600]
                logger.info(f"Rate limiter ({self.provider_name}): After wait, {len(self.calls)}/{self.max_calls_per_hour} calls remaining")
        
        # Record this call
        self.calls.append(now)
        self._save_calls()
        logger.debug(f"Rate limiter ({self.provider_name}): Recorded API call, total calls: {len(self.calls)}")
        
        # Mandatory sleep to ensure we never exceed rate limits (1000 calls/hour = ~4 seconds per call)
        time.sleep(4)
        logger.debug(f"Rate limiter ({self.provider_name}): Sleeping 4 seconds to prevent rate limit")

def get_shared_rate_limiter(provider_name: str, max_calls_per_hour: int) -> RateLimiter:
    """Get or create a shared rate limiter for a provider"""
    if provider_name not in _SHARED_RATE_LIMITERS:
        _SHARED_RATE_LIMITERS[provider_name] = RateLimiter(max_calls_per_hour, provider_name)
    return _SHARED_RATE_LIMITERS[provider_name]

class BaseProviderAdapter(ABC):
    """Base class for all provider adapters"""
    
    def __init__(self, credentials: Dict[str, Any], rate_limit_per_hour: int = 1000):
        self.credentials = credentials
        # Use shared rate limiter based on provider name
        provider_name = self.get_provider_name()
        self.rate_limiter = get_shared_rate_limiter(provider_name, rate_limit_per_hour)
        self.logger = logging.getLogger(f"Provider.{self.__class__.__name__}")
        
        # Setup HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the provider API"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name"""
        pass
    
    @abstractmethod
    def get_events(self, last_modified_since: Optional[datetime] = None) -> List[ProviderEvent]:
        """Get events from the provider"""
        pass
    
    @abstractmethod
    def get_participants(self, event_id: str, last_modified_since: Optional[datetime] = None) -> List[ProviderParticipant]:
        """Get participants for a specific event"""
        pass
    
    def sync_events(self, last_modified_since: Optional[datetime] = None) -> SyncResult:
        """Sync events from provider"""
        start_time = datetime.now()
        errors = []
        processed_count = 0
        
        try:
            self.logger.info(f"Starting event sync for {self.get_provider_name()}")
            
            # Authenticate first
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            # Get events
            events = self.get_events(last_modified_since)
            total_count = len(events)
            
            self.logger.info(f"Retrieved {total_count} events from {self.get_provider_name()}")
            
            # Process each event
            for event in events:
                try:
                    self._store_event(event)
                    processed_count += 1
                except Exception as e:
                    error_msg = f"Failed to store event {event.provider_event_id}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return SyncResult(
                success=len(errors) == 0,
                total_records=total_count,
                processed_records=processed_count,
                error_count=len(errors),
                errors=errors,
                sync_type='events',
                provider_name=self.get_provider_name(),
                event_id=None,
                duration_seconds=duration,
                last_modified_filter=last_modified_since
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"Event sync failed: {str(e)}"
            self.logger.error(error_msg)
            
            return SyncResult(
                success=False,
                total_records=0,
                processed_records=processed_count,
                error_count=1,
                errors=[error_msg],
                sync_type='events',
                provider_name=self.get_provider_name(),
                event_id=None,
                duration_seconds=duration,
                last_modified_filter=last_modified_since
            )
    
    def sync_participants(self, event_id: str, last_modified_since: Optional[datetime] = None) -> SyncResult:
        """Sync participants for a specific event"""
        start_time = datetime.now()
        errors = []
        processed_count = 0
        
        try:
            self.logger.info(f"Starting participant sync for {self.get_provider_name()} event {event_id}")
            
            # Authenticate first
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            # Get participants
            participants = self.get_participants(event_id, last_modified_since)
            total_count = len(participants)
            
            self.logger.info(f"Retrieved {total_count} participants from {self.get_provider_name()} event {event_id}")
            
            # Process each participant
            for participant in participants:
                try:
                    self._store_participant(participant)
                    processed_count += 1
                except Exception as e:
                    error_msg = f"Failed to store participant {participant.provider_participant_id}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            duration = (datetime.now() - start_time).total_seconds()
            
            return SyncResult(
                success=len(errors) == 0,
                total_records=total_count,
                processed_records=processed_count,
                error_count=len(errors),
                errors=errors,
                sync_type='participants',
                provider_name=self.get_provider_name(),
                event_id=event_id,
                duration_seconds=duration,
                last_modified_filter=last_modified_since
            )
            
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_msg = f"Participant sync failed for event {event_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return SyncResult(
                success=False,
                total_records=0,
                processed_records=processed_count,
                error_count=1,
                errors=[error_msg],
                sync_type='participants',
                provider_name=self.get_provider_name(),
                event_id=event_id,
                duration_seconds=duration,
                last_modified_filter=last_modified_since
            )
    
    def _make_api_request(self, url: str, method: str = 'GET', params: Dict = None, 
                         data: Dict = None, headers: Dict = None) -> requests.Response:
        """Make an API request with rate limiting and error handling"""
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        # Make request
        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = self.session.post(url, params=params, json=data, headers=headers, timeout=30)
            elif method.upper() == 'PUT':
                response = self.session.put(url, params=params, json=data, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {url} - {str(e)}")
            raise
    
    @abstractmethod
    def _store_event(self, event: ProviderEvent):
        """Store event in database (implemented by sync worker)"""
        pass
    
    @abstractmethod
    def _store_participant(self, participant: ProviderParticipant):
        """Store participant in database (implemented by sync worker)"""
        pass
    
    def _safe_get(self, data: Dict, key: str, default: Any = None) -> Any:
        """Safely get a value from a dictionary"""
        try:
            keys = key.split('.')
            result = data
            for k in keys:
                if isinstance(result, dict):
                    result = result.get(k)
                else:
                    return default
            return result if result is not None else default
        except (KeyError, TypeError, AttributeError):
            return default
    
    def _parse_datetime(self, date_value, formats: List[str] = None) -> Optional[datetime]:
        """Parse datetime from string, integer timestamp, or datetime object"""
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
        
        # If it's not a string at this point, we can't parse it
        if not isinstance(date_value, str):
            self.logger.warning(f"Unexpected date type: {type(date_value)} - {date_value}")
            return None
            
        if formats is None:
            formats = [
                # ISO formats
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d",
                # RunSignUp formats - try no leading zeros first (most common)
                "%m/%d/%Y %H:%M",      # "9/28/2025 09:00" or "09/28/2025 09:00"
                "%m/%d/%Y %H:%M:%S",   # "9/28/2025 09:00:00"
                "%m/%d/%Y",            # "9/28/2025"
                # Additional common US date formats
                "%m-%d-%Y %H:%M:%S",
                "%m-%d-%Y %H:%M",
                "%m-%d-%Y",
            ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_value, fmt)
            except ValueError:
                continue
        
        self.logger.warning(f"Could not parse datetime: {date_value}")
        return None 