#!/usr/bin/env python3
"""
Debug script to test Haku's second API call for detailed participant information
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

def test_haku_detailed_api():
    print("🔍 Testing Haku's detailed participant API calls...")
    
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
    
    # Get a sample event with participants
    target_event = None
    for event in events:
        # Get basic participant list
        headers = adapter._get_auth_headers()
        response = adapter._make_api_request(
            f"{adapter.BASE_URL}/events/{event.provider_event_id}/participants",
            headers=headers,
            params={"page": 1, "per_page": 1}
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                target_event = event
                sample_participant = data[0]
                break
    
    if not target_event:
        print("❌ No events with participants found")
        return
    
    print(f"\n📅 Testing with event: {target_event.event_name}")
    print(f"Sample participant from list: {sample_participant.get('registration_number')}")
    
    # Now test different endpoints to get detailed participant info
    participant_id = sample_participant.get('registration_number')
    
    potential_endpoints = [
        f"/participants/{participant_id}",
        f"/registrations/{participant_id}",
        f"/events/{target_event.provider_event_id}/participants/{participant_id}",
        f"/events/{target_event.provider_event_id}/registrations/{participant_id}",
        f"/participant/{participant_id}",
        f"/registration/{participant_id}"
    ]
    
    headers = adapter._get_auth_headers()
    
    for endpoint in potential_endpoints:
        try:
            print(f"\n🔍 Testing endpoint: {endpoint}")
            response = adapter._make_api_request(
                f"{adapter.BASE_URL}{endpoint}",
                headers=headers
            )
            
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ SUCCESS! Got detailed data:")
                print(f"Response type: {type(data)}")
                
                if isinstance(data, dict):
                    print(f"Fields available: {list(data.keys())}")
                    print(f"Sample data:\n{json.dumps(data, indent=2)}")
                    
                    # Compare with basic participant data
                    basic_fields = set(sample_participant.keys())
                    detailed_fields = set(data.keys())
                    
                    new_fields = detailed_fields - basic_fields
                    if new_fields:
                        print(f"\n🎉 Additional fields in detailed call:")
                        for field in sorted(new_fields):
                            print(f"   + {field}: {data.get(field)}")
                    else:
                        print("⚠️  No additional fields found")
                        
                elif isinstance(data, list):
                    print(f"List with {len(data)} items")
                    if data:
                        print(f"Sample: {json.dumps(data[0], indent=2)}")
                
                break  # Found working endpoint
                
            elif response.status_code == 404:
                print("❌ Not found")
            elif response.status_code == 403:
                print("❌ Forbidden")
            else:
                print(f"❌ Error: {response.status_code} - {response.text[:100]}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    print(f"\n=== TESTING ALTERNATIVE APPROACHES ===")
    
    # Test if there are query parameters that give more detail
    print("\n🔍 Testing query parameters for more detail:")
    
    response = adapter._make_api_request(
        f"{adapter.BASE_URL}/events/{target_event.provider_event_id}/participants",
        headers=headers,
        params={
            "page": 1, 
            "per_page": 1,
            "include_details": "true",
            "include_personal_info": "true", 
            "include_contact_info": "true",
            "include_emergency_contact": "true",
            "expand": "all"
        }
    )
    
    if response.status_code == 200:
        detailed_data = response.json()
        if isinstance(detailed_data, list) and detailed_data:
            participant = detailed_data[0]
            basic_fields = set(sample_participant.keys())
            detailed_fields = set(participant.keys())
            
            new_fields = detailed_fields - basic_fields
            if new_fields:
                print(f"✅ Query parameters worked! Additional fields:")
                for field in sorted(new_fields):
                    print(f"   + {field}: {participant.get(field)}")
            else:
                print("⚠️  Query parameters didn't add new fields")
        else:
            print("❌ No data returned with query parameters")
    else:
        print(f"❌ Query parameters failed: {response.status_code}")

if __name__ == "__main__":
    test_haku_detailed_api() 