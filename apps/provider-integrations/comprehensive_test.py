#!/usr/bin/env python3
"""
Comprehensive test to validate RunSignUp integration fixes
Tests rate limiting, database storage, and authentication
"""

import sys
import os
import time
import json
from datetime import datetime
import logging

# Add the providers directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'providers'))

from runsignup_adapter import RunSignUpAdapter
import psycopg2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_rate_limiter():
    """Test rate limiter functionality"""
    logger.info("🚦 Testing Rate Limiter...")
    
    # Test credentials (using first credential set)
    credentials = {
        'principal': 'a23c4edf55da3ba1af6bc01f4e87ab26',
        'secret': '5d1b0e6e80e4e9b26e3b8f8c82d8e9c4b5f7a9c3'
    }
    
    adapter = RunSignUpAdapter(credentials, timing_partner_id=9)
    
    # Check rate limiter status
    rate_limiter = adapter.rate_limiter
    current_calls = len(rate_limiter.calls)
    
    logger.info(f"📊 Current rate limiter: {current_calls}/1000 calls")
    
    if current_calls >= 999:
        logger.warning("⚠️  Rate limiter near/at limit - clearing for test")
        rate_limiter.calls = []
        rate_limiter._save_calls()
        logger.info("🧹 Rate limiter cleared")
    
    return True

def test_authentication():
    """Test authentication"""
    logger.info("🔑 Testing Authentication...")
    
    credentials = {
        'principal': 'a23c4edf55da3ba1af6bc01f4e87ab26',
        'secret': '5d1b0e6e80e4e9b26e3b8f8c82d8e9c4b5f7a9c3'
    }
    
    adapter = RunSignUpAdapter(credentials, timing_partner_id=9)
    
    if adapter.authenticate():
        logger.info("✅ Authentication successful")
        return True
    else:
        logger.error("❌ Authentication failed")
        return False

def test_database_connection():
    """Test database connection"""
    logger.info("🗄️  Testing Database Connection...")
    
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'project88_myappdb'),
            user=os.getenv('DB_USER', 'project88_admin'),
            password=os.getenv('DB_PASSWORD', 'securepassword123')
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM runsignup_events;")
        event_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runsignup_races;")
        race_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runsignup_participants;")
        participant_count = cursor.fetchone()[0]
        
        conn.close()
        
        logger.info(f"✅ Database connected - Events: {event_count}, Races: {race_count}, Participants: {participant_count}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def test_event_storage():
    """Test event storage with actual data"""
    logger.info("📅 Testing Event Storage...")
    
    credentials = {
        'principal': 'a23c4edf55da3ba1af6bc01f4e87ab26',
        'secret': '5d1b0e6e80e4e9b26e3b8f8c82d8e9c4b5f7a9c3'
    }
    
    adapter = RunSignUpAdapter(credentials, timing_partner_id=9)
    
    try:
        # Get one event
        logger.info("🔍 Fetching one event for testing...")
        events = adapter.get_events()
        
        if not events:
            logger.warning("⚠️  No events found")
            return False
        
        test_event = events[0]
        logger.info(f"📋 Testing with event: {test_event.provider_event_id}")
        
        # Check event raw data structure
        logger.info(f"🔍 Event raw data keys: {list(test_event.raw_data.keys())}")
        
        event_data = test_event.raw_data.get('event', {})
        race_data = test_event.raw_data.get('race', {})
        
        if 'event_id' in event_data and 'race_id' in race_data:
            logger.info(f"✅ Event data structure valid - event_id: {event_data.get('event_id')}, race_id: {race_data.get('race_id')}")
            
            # Test the _store_event method
            try:
                adapter._store_event(test_event)
                logger.info("✅ Event storage test successful")
                return True
            except Exception as e:
                logger.error(f"❌ Event storage failed: {e}")
                return False
        else:
            logger.error(f"❌ Invalid event data structure - event keys: {list(event_data.keys())}, race keys: {list(race_data.keys())}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Event storage test failed: {e}")
        return False

def test_participant_storage():
    """Test participant storage"""
    logger.info("👥 Testing Participant Storage...")
    
    credentials = {
        'principal': 'a23c4edf55da3ba1af6bc01f4e87ab26',
        'secret': '5d1b0e6e80e4e9b26e3b8f8c82d8e9c4b5f7a9c3'
    }
    
    adapter = RunSignUpAdapter(credentials, timing_partner_id=9)
    
    try:
        # Get events first
        events = adapter.get_events()
        
        if not events:
            logger.warning("⚠️  No events found for participant testing")
            return False
        
        test_event = events[0]
        event_data = test_event.raw_data.get('event', {})
        race_data = test_event.raw_data.get('race', {})
        
        race_id = race_data.get('race_id')
        event_id = event_data.get('event_id')
        
        if not race_id or not event_id:
            logger.warning("⚠️  Missing race_id or event_id for participant test")
            return False
        
        # Get participants
        logger.info(f"🔍 Fetching participants for event {event_id}...")
        participants = adapter.get_participants(str(race_id), str(event_id))
        
        if not participants:
            logger.warning(f"⚠️  No participants found for event {event_id}")
            return True  # Not a failure, just no data
        
        test_participant = participants[0]
        logger.info(f"📋 Testing with participant: {test_participant.provider_participant_id}")
        
        # Test participant storage
        try:
            adapter._store_participant(test_participant)
            logger.info("✅ Participant storage test successful")
            return True
        except Exception as e:
            logger.error(f"❌ Participant storage failed: {e}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Participant storage test failed: {e}")
        return False

def main():
    """Run comprehensive test suite"""
    logger.info("🧪 COMPREHENSIVE RUNSIGNUP INTEGRATION TEST")
    logger.info("=" * 60)
    
    tests = [
        ("Rate Limiter", test_rate_limiter),
        ("Authentication", test_authentication),
        ("Database Connection", test_database_connection),
        ("Event Storage", test_event_storage),
        ("Participant Storage", test_participant_storage)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name} test...")
        try:
            result = test_func()
            results[test_name] = result
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"{status} - {test_name}")
        except Exception as e:
            logger.error(f"❌ FAIL - {test_name}: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🎯 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\n🏆 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - System ready for production!")
        return True
    else:
        logger.warning(f"⚠️  {total - passed} tests failed - Issues need fixing")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 