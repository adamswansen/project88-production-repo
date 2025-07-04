#!/usr/bin/env python3

import os
import psycopg2
from datetime import datetime, timedelta

def debug_sync_timing():
    """Debug the sync timing logic for Event 974559"""
    
    # Database connection
    conn = psycopg2.connect(
        host='localhost',
        database='project88_myappdb', 
        user='project88_myappuser',
        password='puctuq-cefwyq-3boqRe'
    )
    cursor = conn.cursor()
    
    now = datetime.now()
    event_id = '974559'
    
    print("=== DEBUGGING SYNC TIMING FOR EVENT 974559 ===")
    print(f"Current time: {now}")
    print()
    
    # 1. Check all sync history for this event
    print("1. All sync history for Event 974559:")
    cursor.execute("""
        SELECT sync_time, status, num_of_synced_records 
        FROM sync_history 
        WHERE event_id = %s AND timing_partner_id = 1
        ORDER BY sync_time DESC 
        LIMIT 10
    """, (event_id,))
    
    sync_records = cursor.fetchall()
    for i, (sync_time, status, records) in enumerate(sync_records):
        time_ago = now - sync_time
        print(f"  {i+1}. {sync_time} ({time_ago} ago) - {status} - {records} records")
    print()
    
    # 2. Test the exact query from get_events_for_sync
    print("2. Testing get_events_for_sync query:")
    cursor.execute("""
        SELECT 
            re.event_id,
            re.start_time,
            re.created_at,
            COALESCE(MAX(sh.sync_time), re.created_at) as last_sync_time,
            COUNT(sh.sync_time) as sync_count
        FROM runsignup_events re
        JOIN timing_partners tp ON re.timing_partner_id = tp.timing_partner_id
        JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
        LEFT JOIN sync_history sh ON re.event_id::text = sh.event_id 
            AND sh.timing_partner_id = re.timing_partner_id
            AND sh.status = 'completed'
        WHERE ppc.provider_id = 2
        AND re.event_id = %s
        GROUP BY re.event_id, re.start_time, re.timing_partner_id, re.name, 
                 tp.company_name, ppc.principal, ppc.secret, re.created_at
    """, (event_id,))
    
    result = cursor.fetchone()
    if result:
        event_id_db, start_time, created_at, last_sync_time, sync_count = result
        print(f"  Event ID: {event_id_db}")
        print(f"  Start time: {start_time}")
        print(f"  Created at: {created_at}")
        print(f"  Last sync time: {last_sync_time}")
        print(f"  Sync count: {sync_count}")
        print(f"  Time since last sync: {now - last_sync_time}")
        print()
        
        # 3. Test frequency calculation
        print("3. Testing frequency calculation:")
        time_until_start = start_time - now
        time_since_start = now - start_time
        
        # Simulate the frequency logic
        stop_after_hours = 1
        if time_since_start > timedelta(hours=stop_after_hours):
            frequency = 0
            reason = f"Stop syncing (>{stop_after_hours}h after start)"
        elif time_until_start <= timedelta(hours=4):
            frequency = 1
            reason = "Within 4h window (1 min frequency)"
        elif time_until_start <= timedelta(hours=24):
            frequency = 5  
            reason = "Within 24h window (5 min frequency)"
        else:
            frequency = 60
            reason = "Outside 24h window (60 min frequency)"
            
        print(f"  Time until start: {time_until_start}")
        print(f"  Time since start: {time_since_start}")
        print(f"  Calculated frequency: {frequency} minutes")
        print(f"  Reason: {reason}")
        print()
        
        # 4. Check if should sync now
        print("4. Should sync check:")
        time_since_sync = now - last_sync_time
        should_sync = time_since_sync >= timedelta(minutes=frequency)
        print(f"  Time since last sync: {time_since_sync}")
        print(f"  Required interval: {frequency} minutes")
        print(f"  Should sync now? {should_sync}")
        
    else:
        print("  Event not found in query results")
    
    conn.close()

if __name__ == "__main__":
    debug_sync_timing() 