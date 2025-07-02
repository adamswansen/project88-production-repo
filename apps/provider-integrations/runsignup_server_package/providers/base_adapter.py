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

logger = logging.getLogger('ProviderAdapter')

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
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls_per_hour: int):
        self.max_calls_per_hour = max_calls_per_hour
        self.calls = []
        
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = datetime.now()
        
        # Remove calls older than 1 hour
        self.calls = [call_time for call_time in self.calls 
                     if (now - call_time).total_seconds() < 3600]
        
        # Check if we're at the limit
        if len(self.calls) >= self.max_calls_per_hour:
            # Wait until the oldest call is more than 1 hour old
            oldest_call = min(self.calls)
            wait_time = 3600 - (now - oldest_call).total_seconds()
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f} seconds")
                time.sleep(wait_time)
        
        # Record this call
        self.calls.append(now)

class BaseProviderAdapter(ABC):
    """Base class for all provider adapters"""
    
    def __init__(self, credentials: Dict[str, Any], rate_limit_per_hour: int = 1000):
        self.credentials = credentials
        self.rate_limiter = RateLimiter(rate_limit_per_hour)
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
    
    def _parse_datetime(self, date_str: str, formats: List[str] = None) -> Optional[datetime]:
        """Parse datetime string with multiple format attempts"""
        if not date_str:
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
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        self.logger.warning(f"Could not parse datetime: {date_str}")
        return None 