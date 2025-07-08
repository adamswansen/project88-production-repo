#!/usr/bin/env python3
"""
Debug script to analyze complete Haku API participant data format
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

def analyze_haku_api():
    print("🔍 Analyzing complete Haku API participant data format...")
    
    # Create adapter
    adapter = HakuAdapter(test_credentials, timing_partner_id=1)
    
    # Test authentication
    print("Testing authentication...")
    if not adapter.authenticate():
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    
    # Get events
    events = adapter.get_events()
    print(f"Found {len(events)} events")
    
    # Find events with different participant counts
    test_events = []
    for event in events[:10]:  # Test first 10 events
        try:
            # Get raw API response for this event
            headers = adapter._get_auth_headers()
            response = adapter._make_api_request(
                f"{adapter.BASE_URL}/events/{event.provider_event_id}/participants",
                headers=headers,
                params={"page": 1, "per_page": 3}  # Get a few samples
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    test_events.append({
                        'event_name': event.event_name,
                        'event_id': event.provider_event_id,
                        'participant_count': len(data),
                        'sample_data': data[0]  # First participant as sample
                    })
        except Exception as e:
            print(f"Error with event {event.event_name}: {e}")
    
    print(f"\n=== COMPLETE API RESPONSE ANALYSIS ===")
    print(f"Analyzed {len(test_events)} events with participant data")
    
    # Analyze the data structure
    all_fields = set()
    field_examples = {}
    
    for event_data in test_events:
        sample = event_data['sample_data']
        print(f"\n📊 Event: {event_data['event_name']}")
        print(f"   Participants: {event_data['participant_count']}")
        print(f"   Sample participant data:")
        print(f"   {json.dumps(sample, indent=6)}")
        
        # Collect all fields
        def collect_fields(obj, prefix=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{prefix}.{key}" if prefix else key
                    all_fields.add(full_key)
                    if full_key not in field_examples:
                        field_examples[full_key] = value
                    
                    if isinstance(value, dict):
                        collect_fields(value, full_key)
                    elif isinstance(value, list) and value and isinstance(value[0], dict):
                        collect_fields(value[0], full_key + "[0]")
        
        collect_fields(sample)
    
    print(f"\n=== COMPLETE FIELD MAPPING ===")
    print(f"Total unique fields found: {len(all_fields)}")
    
    # Sort fields for better readability
    sorted_fields = sorted(all_fields)
    for field in sorted_fields:
        example_value = field_examples.get(field, "N/A")
        value_type = type(example_value).__name__
        print(f"  {field:<30} | {value_type:<10} | {str(example_value)[:50]}")
    
    print(f"\n=== CURRENT PARSER vs ACTUAL API COMPARISON ===")
    
    # Compare what our parser expects vs what API provides
    parser_mappings = {
        "Expected by parser": "Actual API field",
        "id": "??? (no 'id' field found)",
        "first_name": "person_full_name (needs splitting)",
        "last_name": "person_full_name (needs splitting)", 
        "email": "email ✅",
        "phone": "??? (need to check)",
        "birth_date": "??? (only 'age' available)",
        "gender": "gender ✅",
        "city": "??? (need to check)",
        "state": "??? (need to check)",
        "country": "??? (need to check)",
        "bib_number": "??? (need to check)",
        "team_name": "team.name",
        "division": "event_category_info",
        "created_at": "registered_at",
        "status": "is_cancelled (boolean)",
        "payment_status": "??? (need to check)",
        "amount_paid": "transaction_amount"
    }
    
    for expected, actual in parser_mappings.items():
        if expected != "Expected by parser":
            print(f"  {expected:<20} → {actual}")
    
    print(f"\n=== RECOMMENDATIONS ===")
    print("1. 🔧 Fix field mapping in _parse_participant method")
    print("2. 🔍 Use registration_number as provider_participant_id")
    print("3. 📝 Split person_full_name into first_name/last_name")
    print("4. 📅 Use 'age' field directly instead of calculating from birth_date")
    print("5. 🏷️ Map event_category_info to division/category")
    print("6. 💰 Use transaction_amount for amount_paid")
    print("7. ✅ Handle is_cancelled boolean for status")

if __name__ == "__main__":
    analyze_haku_api() 