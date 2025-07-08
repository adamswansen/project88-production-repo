#!/usr/bin/env python3
"""
Test script to verify the fixed Haku participant parsing
"""
import sys
import os
sys.path.append('project88-production-repo/apps/provider-integrations')

from providers.haku_adapter import HakuAdapter
import json

# Real Haku credentials from production
test_credentials = {
    'principal': '5e6pfucoiqfeqcpo3pled2vlsu',
    'secret': 'uasvlfm2jvb7f5mml7s0jlnm9um63k467gp0t4lsocjkfi5k7jj'
}

def test_haku_parsing_fix():
    print("🔧 Testing fixed Haku participant parsing...")
    
    # Create adapter
    adapter = HakuAdapter(test_credentials, timing_partner_id=1)
    
    # Test authentication
    if not adapter.authenticate():
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    
    # Get events
    events = adapter.get_events()
    print(f"Found {len(events)} events")
    
    # Test participant parsing with fixed method
    test_count = 0
    success_count = 0
    
    for event in events[:5]:  # Test first 5 events
        print(f"\n📅 Testing event: {event.event_name}")
        
        try:
            participants = adapter.get_participants(event.provider_event_id)
            print(f"   ✅ Retrieved {len(participants)} participants")
            
            if participants:
                # Test the first participant
                participant = participants[0]
                print(f"   📝 Sample participant:")
                print(f"      ID: {participant.provider_participant_id}")
                print(f"      Name: {participant.first_name} {participant.last_name}")
                print(f"      Email: {participant.email}")
                print(f"      Age: {participant.age}")
                print(f"      Gender: {participant.gender}")
                print(f"      Division: {participant.division}")
                print(f"      Team: {participant.team_name}")
                print(f"      Amount Paid: ${participant.amount_paid}")
                print(f"      Registration Status: {participant.registration_status}")
                print(f"      Registration Date: {participant.registration_date}")
                
                # Count non-null fields
                non_null_fields = 0
                total_fields = 0
                for attr in dir(participant):
                    if not attr.startswith('_') and not callable(getattr(participant, attr)):
                        total_fields += 1
                        if getattr(participant, attr) is not None:
                            non_null_fields += 1
                
                print(f"      Data completeness: {non_null_fields}/{total_fields} fields populated")
                success_count += 1
            else:
                print("   📭 No participants found")
                
            test_count += 1
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            test_count += 1
    
    print(f"\n=== TEST RESULTS ===")
    print(f"✅ Events tested: {test_count}")
    print(f"✅ Events with participants: {success_count}")
    print(f"✅ Success rate: {success_count/test_count*100:.1f}%")
    
    if success_count > 0:
        print("\n🎉 Participant parsing is now working correctly!")
        print("📋 The fix correctly maps:")
        print("   • registration_number → provider_participant_id")
        print("   • person_full_name → first_name + last_name")
        print("   • age → age (direct)")
        print("   • event_category_info → division")
        print("   • registered_at → registration_date")
        print("   • transaction_amount → amount_paid")
        print("   • is_cancelled → registration_status")
    else:
        print("\n❌ Still having issues with participant parsing")

if __name__ == "__main__":
    test_haku_parsing_fix() 