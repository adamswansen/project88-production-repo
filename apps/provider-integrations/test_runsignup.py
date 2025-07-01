#!/usr/bin/env python3
"""
Test script for RunSignUp integration
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from providers.runsignup_adapter import RunSignUpAdapter

def test_runsignup_integration():
    """Test RunSignUp integration with actual credentials"""
    
    # Connect to database and get credentials
    db_path = "../../race_results.db"
    if not os.path.exists(db_path):
        print("❌ Database not found. Make sure you're running from the correct directory.")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get RunSignUp credentials (provider_id = 2, using timing partner 9)
    cursor.execute("""
        SELECT principal, secret, timing_partner_id 
        FROM partner_provider_credentials 
        WHERE provider_id = 2 AND timing_partner_id = 9
    """)
    
    result = cursor.fetchone()
    if not result:
        print("❌ No RunSignUp credentials found for timing partner 9")
        return False
    
    principal, secret, timing_partner_id = result
    print(f"🔑 Found credentials for {principal} (timing partner {timing_partner_id})")
    
    # Create adapter
    credentials = {
        'principal': principal,
        'secret': secret
    }
    
    try:
        adapter = RunSignUpAdapter(credentials, timing_partner_id)
        print(f"✅ Created RunSignUp adapter")
        
        # Test authentication
        print("\n🔐 Testing authentication...")
        if adapter.authenticate():
            print("✅ Authentication successful!")
        else:
            print("❌ Authentication failed!")
            return False
        
        # Test getting events (limited to 5 for testing)
        print("\n📅 Testing event retrieval (first 5 events)...")
        events = adapter.get_events()
        
        if events:
            print(f"✅ Found {len(events)} events")
            for i, event in enumerate(events[:5]):
                print(f"  {i+1}. {event.event_name} - {event.event_date}")
                print(f"     ID: {event.provider_event_id}")
                print(f"     Location: {event.location_city}, {event.location_state}")
                
        else:
            print("⚠️  No events found")
        
        # Test getting participants for the first event
        if events:
            first_event = events[0]
            print(f"\n👥 Testing participant retrieval for '{first_event.event_name}'...")
            participants = adapter.get_participants(first_event.provider_event_id)
            
            if participants:
                print(f"✅ Found {len(participants)} participants")
                for i, participant in enumerate(participants[:3]):  # Show first 3
                    print(f"  {i+1}. {participant.first_name} {participant.last_name}")
                    print(f"     Email: {participant.email}")
                    print(f"     Bib: {participant.bib_number}")
            else:
                print("⚠️  No participants found for this event")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing RunSignUp integration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("🧪 Testing RunSignUp Integration")
    print("=" * 50)
    
    success = test_runsignup_integration()
    
    if success:
        print("\n🎉 RunSignUp integration test completed successfully!")
    else:
        print("\n💥 RunSignUp integration test failed!")
    
    print("=" * 50) 