#!/usr/bin/env python3
"""
Debug script to investigate ProviderEvent structure
"""

import sys
import os
sys.path.insert(0, '/opt/project88/provider-integrations')

from providers.runsignup_adapter import RunSignUpAdapter
import psycopg2

def debug_events():
    print("🔍 Debugging ProviderEvent structure...")
    
    # Get database connection
    db_config = {
        'host': 'localhost',
        'database': 'project88_myappdb',
        'user': 'project88_myappuser',
        'password': 'puctuq-cefwyq-3boqRe',
        'port': 5432
    }
    
    # Get credentials for timing partner 1
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT principal, secret FROM partner_provider_credentials 
        WHERE timing_partner_id = 1 AND provider_id = 2
    """)
    
    result = cursor.fetchone()
    if not result:
        print("❌ No credentials found for timing partner 1")
        return
    
    principal, secret = result
    conn.close()
    
    print(f"✅ Found credentials for timing partner 1")
    
    # Create adapter
    credentials = {'principal': principal, 'secret': secret}
    adapter = RunSignUpAdapter(credentials, 1)
    
    # Test authentication
    if not adapter.authenticate():
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    
    # Get events (limit to first few)
    print("📥 Fetching events...")
    events = adapter.get_events()
    
    if not events:
        print("❌ No events returned")
        return
    
    print(f"✅ Got {len(events)} events")
    
    # Debug first event
    event = events[0]
    print(f"\n🔍 First event debug:")
    print(f"   Type: {type(event)}")
    print(f"   Provider Event ID: {event.provider_event_id}")
    print(f"   Event Name: {event.event_name}")
    
    # Check attributes
    attrs = [attr for attr in dir(event) if not attr.startswith('_')]
    print(f"   Attributes: {attrs}")
    
    # Check raw_data
    if hasattr(event, 'raw_data'):
        print(f"   Raw data keys: {list(event.raw_data.keys())}")
        
        if 'race' in event.raw_data:
            race_data = event.raw_data['race']
            print(f"   Race data type: {type(race_data)}")
            print(f"   Race data keys: {list(race_data.keys())}")
            
            if 'race_id' in race_data:
                print(f"   ✅ Race ID found: {race_data['race_id']}")
            else:
                print(f"   ❌ NO RACE_ID in race data!")
                print(f"   Available race keys: {list(race_data.keys())}")
        else:
            print(f"   ❌ NO 'race' key in raw_data!")
            print(f"   Available raw_data keys: {list(event.raw_data.keys())}")
    else:
        print(f"   ❌ NO raw_data attribute!")
    
    # Test the exact code that's failing
    print(f"\n🧪 Testing race_id extraction:")
    try:
        race_id = event.raw_data.get('race', {}).get('race_id')
        print(f"   ✅ Extraction successful: {race_id}")
    except Exception as e:
        print(f"   ❌ Extraction failed: {e}")
        
        # Try to understand what's happening
        try:
            race_data = event.raw_data.get('race', {})
            print(f"   Race data result: {race_data}")
            print(f"   Race data type: {type(race_data)}")
        except Exception as e2:
            print(f"   Even getting race data failed: {e2}")

if __name__ == "__main__":
    debug_events() 