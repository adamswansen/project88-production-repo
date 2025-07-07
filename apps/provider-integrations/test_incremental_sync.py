#!/usr/bin/env python3
"""
Test script to validate incremental sync optimization
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from runsignup_production_sync import RunSignUpProductionSync

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_incremental_sync.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def test_incremental_sync():
    """Test incremental sync performance vs full sync"""
    logger.info("🧪 Starting Incremental Sync Performance Test")
    logger.info("=" * 80)
    
    # Test with first timing partner only
    sync = RunSignUpProductionSync()
    credentials = sync.get_runsignup_credentials()
    
    if not credentials:
        logger.error("❌ No credentials found!")
        return
    
    timing_partner_id, principal, secret, credential_id = credentials[0]
    logger.info(f"Testing with timing partner {timing_partner_id}")
    
    # Test 1: Full sync
    logger.info("\n📊 Test 1: Full Sync Performance")
    sync.force_full_sync = True
    start_time = time.time()
    
    results_full = sync.sync_timing_partner(timing_partner_id, principal, secret, credential_id)
    
    full_sync_duration = time.time() - start_time
    logger.info(f"✅ Full sync completed in {full_sync_duration:.2f} seconds")
    logger.info(f"   • Participants synced: {results_full['participants']}")
    logger.info(f"   • Events synced: {results_full['events']}")
    
    # Wait a moment to ensure timestamp differences
    time.sleep(2)
    
    # Test 2: Incremental sync
    logger.info("\n📊 Test 2: Incremental Sync Performance")
    sync.force_full_sync = False
    sync.incremental_days = 1  # Very recent for testing
    start_time = time.time()
    
    results_incremental = sync.sync_timing_partner(timing_partner_id, principal, secret, credential_id)
    
    incremental_sync_duration = time.time() - start_time
    logger.info(f"✅ Incremental sync completed in {incremental_sync_duration:.2f} seconds")
    logger.info(f"   • Participants synced: {results_incremental['participants']}")
    logger.info(f"   • Events synced: {results_incremental['events']}")
    
    # Performance comparison
    logger.info("\n📈 Performance Comparison")
    logger.info("=" * 80)
    
    if full_sync_duration > 0 and incremental_sync_duration > 0:
        speedup = full_sync_duration / incremental_sync_duration
        time_saved = full_sync_duration - incremental_sync_duration
        
        logger.info(f"🚀 Speed improvement: {speedup:.2f}x faster")
        logger.info(f"⏱️  Time saved: {time_saved:.2f} seconds")
        logger.info(f"📊 Full sync: {full_sync_duration:.2f}s ({results_full['participants']} participants)")
        logger.info(f"📊 Incremental sync: {incremental_sync_duration:.2f}s ({results_incremental['participants']} participants)")
        
        if speedup > 2:
            logger.info("✅ OPTIMIZATION SUCCESSFUL! Significant performance improvement detected!")
        else:
            logger.warning("⚠️  Performance improvement may be limited - check if events have recent changes")
    
    # Test 3: Ulster Project specific test
    logger.info("\n🏃‍♂️ Test 3: Ulster Project Specific Test")
    test_ulster_project_sync()

def test_ulster_project_sync():
    """Test sync specifically for Ulster Project"""
    try:
        from datetime import datetime
        import psycopg2
        
        # Connect to database
        db_config = {
            'host': 'localhost',
            'database': 'project88_myappdb',
            'user': 'project88_myappuser',
            'password': 'puctuq-cefwyq-3boqRe',
            'port': 5432
        }
        
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Get Ulster Project event details
        cursor.execute("""
            SELECT e.event_id, e.name, e.start_time, 
                   COUNT(p.registration_id) as participant_count,
                   MAX(p.fetched_date) as last_sync
            FROM runsignup_events e
            JOIN runsignup_races r ON e.race_id = r.race_id
            LEFT JOIN runsignup_participants p ON e.event_id = p.event_id
            WHERE r.name LIKE '%Ulster%' AND e.start_time > NOW()
            GROUP BY e.event_id, e.name, e.start_time
            ORDER BY e.start_time
        """)
        
        results = cursor.fetchall()
        
        if results:
            logger.info("📊 Ulster Project Event Status:")
            for event_id, name, start_time, participant_count, last_sync in results:
                logger.info(f"   • Event {event_id}: {name}")
                logger.info(f"     Date: {start_time}")
                logger.info(f"     Participants: {participant_count}")
                logger.info(f"     Last sync: {last_sync}")
                
                # Check if this would use incremental sync
                if last_sync:
                    days_since_sync = (datetime.now() - last_sync).days
                    if days_since_sync <= 7:
                        logger.info(f"     ✅ Would use incremental sync (last sync {days_since_sync} days ago)")
                    else:
                        logger.info(f"     🔄 Would use full sync (last sync {days_since_sync} days ago)")
                else:
                    logger.info(f"     🔄 Would use full sync (first sync)")
        else:
            logger.warning("⚠️  No Ulster Project events found")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error testing Ulster Project sync: {e}")

if __name__ == "__main__":
    test_incremental_sync() 