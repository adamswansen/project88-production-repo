#!/usr/bin/env python3
"""
Focused test for timing partner 9 (credential set 9)
"""

import sys
import os
import time
from datetime import datetime
import logging
import psycopg2

# Add the providers directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'providers'))

from runsignup_adapter import RunSignUpAdapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_timing_partner_9_credentials():
    """Get credentials for timing partner 9"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'project88_myappdb'),
            user=os.getenv('DB_USER', 'project88_admin'),
            password=os.getenv('DB_PASSWORD', 'securepassword123')
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timing_partner_id, principal, secret
            FROM partner_provider_credentials 
            WHERE timing_partner_id = 9
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result
        else:
            logger.error("No credentials found for timing partner 9")
            return None
        
    except Exception as e:
        logger.error(f"Failed to get credentials: {e}")
        return None

def test_timing_partner_9():
    """Test timing partner 9 with limited data"""
    logger.info("🎯 FOCUSED TEST - TIMING PARTNER 9")
    logger.info("=" * 50)
    
    # Get credentials
    creds = get_timing_partner_9_credentials()
    if not creds:
        logger.error("❌ Cannot get credentials for timing partner 9")
        return False
    
    timing_partner_id, principal, secret = creds
    logger.info(f"🔑 Using timing partner {timing_partner_id}")
    
    # Create adapter
    credentials = {
        'principal': principal,
        'secret': secret
    }
    
    adapter = RunSignUpAdapter(credentials, timing_partner_id=timing_partner_id)
    
    # Test authentication
    logger.info("🔐 Testing authentication...")
    if not adapter.authenticate():
        logger.error("❌ Authentication failed")
        return False
    logger.info("✅ Authentication successful")
    
    # Get baseline counts
    logger.info("📊 Getting baseline counts...")
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'project88_myappdb'),
            user=os.getenv('DB_USER', 'project88_admin'),
            password=os.getenv('DB_PASSWORD', 'securepassword123')
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM runsignup_events WHERE timing_partner_id = %s", (timing_partner_id,))
        baseline_events = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runsignup_participants WHERE timing_partner_id = %s", (timing_partner_id,))
        baseline_participants = cursor.fetchone()[0]
        
        logger.info(f"📈 Baseline - Events: {baseline_events}, Participants: {baseline_participants}")
        
    except Exception as e:
        logger.error(f"❌ Failed to get baseline counts: {e}")
        return False
    
    # Test getting events (limited to first 5 for testing)
    logger.info("📅 Getting events (limited to first 5)...")
    try:
        events = adapter.get_events()
        
        if not events:
            logger.warning("⚠️  No events found")
            return True
        
        # Limit to first 5 events for testing
        test_events = events[:5]
        logger.info(f"🎯 Testing with {len(test_events)} events")
        
        events_processed = 0
        participants_processed = 0
        
        for event in test_events:
            try:
                logger.info(f"🔍 Processing event {event.provider_event_id}")
                
                # Get event data
                event_data = event.raw_data.get('event', {})
                race_data = event.raw_data.get('race', {})
                
                event_id = event_data.get('event_id')
                race_id = race_data.get('race_id')
                
                if not event_id or not race_id:
                    logger.warning(f"⚠️  Missing IDs for event {event.provider_event_id}")
                    continue
                
                # Store event
                adapter.store_event(event_data, race_id, conn)
                events_processed += 1
                logger.info(f"✅ Stored event {event_id}")
                
                # Get a few participants for this event
                logger.info(f"👥 Getting participants for event {event_id}...")
                participants = adapter.get_participants(str(race_id), str(event_id))
                
                if participants:
                    # Limit to first 3 participants for testing
                    test_participants = participants[:3]
                    logger.info(f"🎯 Testing with {len(test_participants)} participants")
                    
                    for participant in test_participants:
                        try:
                            participant_data = participant.raw_data
                            adapter.store_participant(participant_data, race_id, event_id, conn)
                            participants_processed += 1
                            logger.info(f"✅ Stored participant {participant.provider_participant_id}")
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to store participant: {e}")
                            continue
                
                # Small delay to be nice to the API
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error processing event {event.provider_event_id}: {e}")
                continue
        
        # Commit changes
        conn.commit()
        conn.close()
        
        # Get final counts
        logger.info("📊 Getting final counts...")
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'project88_myappdb'),
            user=os.getenv('DB_USER', 'project88_admin'),
            password=os.getenv('DB_PASSWORD', 'securepassword123')
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM runsignup_events WHERE timing_partner_id = %s", (timing_partner_id,))
        final_events = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM runsignup_participants WHERE timing_partner_id = %s", (timing_partner_id,))
        final_participants = cursor.fetchone()[0]
        
        conn.close()
        
        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("🎉 TIMING PARTNER 9 TEST COMPLETE")
        logger.info("=" * 50)
        logger.info(f"📈 Events - Before: {baseline_events}, After: {final_events}, Added: {final_events - baseline_events}")
        logger.info(f"👥 Participants - Before: {baseline_participants}, After: {final_participants}, Added: {final_participants - baseline_participants}")
        logger.info(f"✅ Events processed: {events_processed}")
        logger.info(f"✅ Participants processed: {participants_processed}")
        
        if events_processed > 0 and participants_processed > 0:
            logger.info("🎉 SUCCESS - All fixes working correctly!")
            return True
        else:
            logger.warning("⚠️  Limited success - check for issues")
            return False
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = test_timing_partner_9()
    sys.exit(0 if success else 1) 