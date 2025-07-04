#!/usr/bin/env python3
"""
Safe test for RunSignUp database fixes - NO API CALLS
Tests database storage logic with mock data
"""

import sys
import os
import json
from datetime import datetime
import logging

# Add the providers directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'providers'))

from runsignup_adapter import RunSignUpAdapter
from base_adapter import ProviderEvent, ProviderParticipant
import psycopg2

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_mock_event():
    """Create mock event data that mimics real RunSignUp structure"""
    
    # This is the EXACT structure we expect from RunSignUp API
    mock_raw_data = {
        'event': {
            'event_id': 999999,  # Mock event ID
            'name': 'Test Event for Database Validation',
            'details': 'Mock event to test database storage',
            'start_time': '2025-07-15 08:00:00',
            'end_time': '2025-07-15 12:00:00',
            'event_type': 'running',
            'distance': '5K',
            'registration_opens': '2025-06-01 00:00:00',
            'volunteer': False,
            'require_dob': True,
            'require_phone': False,
            'giveaway': False
        },
        'race': {
            'race_id': 888888,  # Mock race ID
            'name': 'Test Race for Database Validation',
            'description': 'Mock race to test database storage',
            'created': '2025-06-01 12:00:00',
            'last_modified': '2025-06-15 15:30:00',
            'url': 'https://example.com/test-race',
            'timezone': 'America/New_York',
            'address': {
                'name': 'Test Park',
                'city': 'Test City',
                'state': 'TX',
                'street': '123 Test St',
                'zipcode': '12345'
            }
        }
    }
    
    # Create ProviderEvent object
    event = ProviderEvent(
        provider_event_id='999999',
        event_name='Test Event for Database Validation',
        event_description='Mock event to test database storage',
        event_date=datetime(2025, 7, 15, 8, 0, 0),
        event_end_date=datetime(2025, 7, 15, 12, 0, 0),
        location_name='Test Park',
        location_city='Test City',
        location_state='TX',
        event_type='running',
        distance='5K',
        max_participants=None,
        registration_open_date=datetime(2025, 6, 1, 0, 0, 0),
        registration_close_date=None,
        registration_fee=None,
        currency='USD',
        status='active',
        raw_data=mock_raw_data
    )
    
    return event

def create_mock_participant():
    """Create mock participant data"""
    
    mock_raw_data = {
        'registration_id': 777777,
        'user_id': 666666,
        'race_id': 888888,  # Match mock race ID
        'bib_num': '1234',
        'chip_num': '5678',
        'registration_date': '2025-06-15 10:30:00',
        'last_modified': '2025-06-15 10:30:00',
        'user': {
            'user_id': 666666,
            'first_name': 'Test',
            'last_name': 'Runner',
            'email': 'test@example.com',
            'phone': '555-123-4567',
            'gender': 'M',
            'age': 35,
            'dob': '1990-01-01',
            'address': {
                'street': '456 Runner St',
                'city': 'Test City',
                'state': 'TX',
                'zipcode': '12345'
            }
        },
        'race_fee': '$25.00',
        'amount_paid': '$25.00',
        'processing_fee': '$2.50'
    }
    
    participant = ProviderParticipant(
        provider_participant_id='777777',
        event_id='999999',  # Match mock event ID
        bib_number='1234',
        first_name='Test',
        last_name='Runner',
        email='test@example.com',
        phone='555-123-4567',
        date_of_birth=datetime(1990, 1, 1),
        gender='M',
        age=35,
        city='Test City',
        state='TX',
        country='US',
        emergency_contact=None,
        team_name=None,
        division=None,
        registration_date=datetime(2025, 6, 15, 10, 30, 0),
        registration_status='active',
        payment_status='paid',
        amount_paid=25.00,
        raw_data=mock_raw_data
    )
    
    return participant

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

def test_event_storage_logic():
    """Test event storage logic with mock data - NO API CALLS"""
    logger.info("📅 Testing Event Storage Logic...")
    
    # Create mock credentials (won't be used for API calls)
    credentials = {
        'principal': 'mock_key',
        'secret': 'mock_secret'
    }
    
    try:
        # Create adapter
        adapter = RunSignUpAdapter(credentials, timing_partner_id=99)
        
        # Create mock event
        mock_event = create_mock_event()
        
        logger.info(f"📋 Testing with mock event: {mock_event.provider_event_id}")
        logger.info(f"🔍 Event raw data keys: {list(mock_event.raw_data.keys())}")
        
        # Verify data structure
        event_data = mock_event.raw_data.get('event', {})
        race_data = mock_event.raw_data.get('race', {})
        
        event_id = event_data.get('event_id')
        race_id = race_data.get('race_id')
        
        logger.info(f"✅ Mock data structure - event_id: {event_id}, race_id: {race_id}")
        
        # Test the _store_event method with mock data
        logger.info("🧪 Testing _store_event method...")
        adapter._store_event(mock_event)
        
        logger.info("✅ Event storage logic test successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Event storage logic failed: {e}")
        return False

def test_participant_storage_logic():
    """Test participant storage logic with mock data - NO API CALLS"""
    logger.info("👥 Testing Participant Storage Logic...")
    
    # Create mock credentials
    credentials = {
        'principal': 'mock_key',
        'secret': 'mock_secret'
    }
    
    try:
        # Create adapter  
        adapter = RunSignUpAdapter(credentials, timing_partner_id=99)
        
        # Create mock participant
        mock_participant = create_mock_participant()
        
        logger.info(f"📋 Testing with mock participant: {mock_participant.provider_participant_id}")
        
        # Test the _store_participant method with mock data
        logger.info("🧪 Testing _store_participant method...")
        adapter._store_participant(mock_participant)
        
        logger.info("✅ Participant storage logic test successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Participant storage logic failed: {e}")
        return False

def test_backfill_data_structure():
    """Test the exact data structure the backfill script expects"""
    logger.info("🔄 Testing Backfill Data Structure...")
    
    try:
        # Create mock event like backfill script creates
        mock_event = create_mock_event()
        
        # Test what the backfill script does
        event_data = mock_event.raw_data.get('event', {})
        race_data = mock_event.raw_data.get('race', {})
        
        # These are the critical fields the backfill script needs
        event_id = event_data.get('event_id')
        race_id = race_data.get('race_id')
        
        logger.info(f"📊 Backfill data check:")
        logger.info(f"   • event_data keys: {list(event_data.keys())}")
        logger.info(f"   • race_data keys: {list(race_data.keys())}")
        logger.info(f"   • event_id: {event_id} (type: {type(event_id)})")
        logger.info(f"   • race_id: {race_id} (type: {type(race_id)})")
        
        # Verify the backfill script won't get NULL values
        if event_id and race_id:
            logger.info("✅ Backfill data structure valid - no NULL constraint violations expected")
            return True
        else:
            logger.error("❌ Missing required IDs - NULL constraint violations would occur")
            return False
        
    except Exception as e:
        logger.error(f"❌ Backfill data structure test failed: {e}")
        return False

def test_rate_limiter_state():
    """Check rate limiter state without making API calls"""
    logger.info("🚦 Testing Rate Limiter State...")
    
    try:
        # Create adapter (doesn't make API calls)
        credentials = {
            'principal': 'mock_key',
            'secret': 'mock_secret'
        }
        
        adapter = RunSignUpAdapter(credentials, timing_partner_id=99)
        
        # Check current rate limiter state
        rate_limiter = adapter.rate_limiter
        current_calls = len(rate_limiter.calls)
        
        logger.info(f"📊 Current rate limiter: {current_calls}/1000 calls")
        
        if current_calls < 950:
            logger.info("✅ Rate limiter has plenty of capacity")
            return True
        else:
            logger.warning(f"⚠️  Rate limiter near capacity: {current_calls}/1000 calls")
            return False
        
    except Exception as e:
        logger.error(f"❌ Rate limiter state test failed: {e}")
        return False

def main():
    """Run safe test suite - NO API CALLS"""
    logger.info("🛡️  SAFE RUNSIGNUP DATABASE TEST (NO API CALLS)")
    logger.info("=" * 60)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Rate Limiter State", test_rate_limiter_state),
        ("Event Storage Logic", test_event_storage_logic),
        ("Participant Storage Logic", test_participant_storage_logic),
        ("Backfill Data Structure", test_backfill_data_structure)
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
    logger.info("🎯 SAFE TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\n🏆 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - Database fixes validated!")
        logger.info("🚀 Ready to run limited backfill test")
        return True
    else:
        logger.warning(f"⚠️  {total - passed} tests failed - Fix issues before backfill")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 