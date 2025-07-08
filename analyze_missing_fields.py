#!/usr/bin/env python3
"""
Analyze all available Haku API fields and identify what we're missing
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

def analyze_missing_fields():
    print("🔍 Analyzing all available Haku fields vs what we're capturing...")
    
    # Create adapter
    adapter = HakuAdapter(test_credentials, timing_partner_id=1)
    
    if not adapter.authenticate():
        print("❌ Authentication failed")
        return
    
    print("✅ Authentication successful")
    
    # Get events and find one with participants
    events = adapter.get_events()
    
    target_event = None
    detailed_data = None
    
    for event in events[:5]:
        try:
            headers = adapter._get_auth_headers()
            
            # Get participant list
            response = adapter._make_api_request(
                f"{adapter.BASE_URL}/events/{event.provider_event_id}/participants",
                headers=headers,
                params={"page": 1, "per_page": 1}
            )
            
            if response.status_code == 200:
                participants = response.json()
                if isinstance(participants, list) and participants:
                    registration_number = participants[0].get('registration_number')
                    
                    # Get detailed info
                    detailed_response = adapter._make_api_request(
                        f"{adapter.BASE_URL}/events/{event.provider_event_id}/registrations/{registration_number}",
                        headers=headers
                    )
                    
                    if detailed_response.status_code == 200:
                        target_event = event
                        detailed_data = detailed_response.json()
                        break
        except Exception as e:
            continue
    
    if not detailed_data:
        print("❌ Could not get detailed participant data")
        return
    
    print(f"📅 Analyzing event: {target_event.event_name}")
    print(f"🔍 Registration: {detailed_data.get('registration_number')}")
    
    # Define what we're currently capturing
    currently_captured = {
        'registration_number': 'provider_participant_id',
        'participant.first_name': 'first_name',
        'participant.last_name': 'last_name', 
        'participant.email': 'email',
        'participant.phone': 'phone',
        'participant.dob': 'date_of_birth',
        'participant.gender': 'gender',
        'participant.address.city': 'city',
        'participant.address.state': 'state',
        'participant.address.country': 'country',
        'emergency_contact_name': 'emergency_contact.name',
        'emergency_contact_phone_number': 'emergency_contact.phone',
        'emergency_contact_relationship': 'emergency_contact.relationship',
        'event_categories[0].name': 'division',
        'event_categories[0].tag_number': 'bib_number',
        'created_at': 'registration_date',
        'is_cancelled': 'registration_status',
        'transaction_amount': 'amount_paid'
    }
    
    # Collect all available fields from the API response
    def collect_all_fields(obj, prefix="", collected=None):
        if collected is None:
            collected = {}
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key
                collected[full_key] = value
                
                if isinstance(value, dict):
                    collect_all_fields(value, full_key, collected)
                elif isinstance(value, list) and value:
                    if isinstance(value[0], dict):
                        collect_all_fields(value[0], full_key + "[0]", collected)
                    else:
                        collected[full_key + "[0]"] = value[0] if value else None
        
        return collected
    
    all_fields = collect_all_fields(detailed_data)
    
    print(f"\n📊 FIELD ANALYSIS:")
    print(f"Total fields available: {len(all_fields)}")
    print(f"Fields currently captured: {len(currently_captured)}")
    
    # Find missing fields
    missing_fields = []
    for field_path, value in all_fields.items():
        if field_path not in currently_captured and value is not None:
            missing_fields.append((field_path, value))
    
    print(f"Fields not captured: {len(missing_fields)}")
    
    print(f"\n✅ CURRENTLY CAPTURED FIELDS:")
    for api_field, our_field in currently_captured.items():
        value = all_fields.get(api_field, "NOT FOUND")
        print(f"   {api_field:<40} → {our_field:<20} | {str(value)[:50]}")
    
    print(f"\n❓ MISSING FIELDS (with data):")
    
    # Categorize missing fields
    personal_info = []
    address_info = []
    event_info = []
    race_info = []
    technical_info = []
    other_info = []
    
    for field_path, value in missing_fields:
        if any(x in field_path.lower() for x in ['name', 'initial', 'account']):
            personal_info.append((field_path, value))
        elif any(x in field_path.lower() for x in ['address', 'line', 'zip']):
            address_info.append((field_path, value))
        elif any(x in field_path.lower() for x in ['shirt', 'pace', 'strava', 'wave', 'corral', 'chip']):
            race_info.append((field_path, value))
        elif any(x in field_path.lower() for x in ['event_categories', 'fundrais']):
            event_info.append((field_path, value))
        elif any(x in field_path.lower() for x in ['browser', 'device', 'os', 'updated']):
            technical_info.append((field_path, value))
        else:
            other_info.append((field_path, value))
    
    categories = [
        ("👤 Personal Info", personal_info),
        ("🏠 Address Details", address_info), 
        ("🏃 Race-Specific", race_info),
        ("🎯 Event Info", event_info),
        ("🔧 Technical", technical_info),
        ("📋 Other", other_info)
    ]
    
    for category_name, fields in categories:
        if fields:
            print(f"\n{category_name}:")
            for field_path, value in sorted(fields):
                value_str = str(value)[:80] if value else "None"
                print(f"   {field_path:<45} | {value_str}")
    
    print(f"\n🎯 RECOMMENDED ADDITIONS:")
    
    valuable_fields = [
        ('participant.middle_initial', 'Middle initial for complete names'),
        ('participant.address.line1', 'Street address'),
        ('participant.address.zip_code', 'ZIP code for location'),
        ('shirt_size_name', 'T-shirt size for logistics'),
        ('current_pace', 'Expected race pace'),
        ('wants_sms_communications', 'Communication preferences'),
        ('event_categories[0].corral_name', 'Start corral assignment'),
        ('event_categories[0].wave_name', 'Start wave assignment'),
        ('event_categories[0].chip_number', 'Timing chip number'),
        ('fundraised_amount', 'Charity fundraising amount'),
        ('additional_questions', 'Custom registration questions'),
    ]
    
    for field, description in valuable_fields:
        if field in all_fields and all_fields[field] is not None:
            value = all_fields[field]
            print(f"   ✅ {field:<35} | {description:<30} | {str(value)[:40]}")
        else:
            print(f"   ⚪ {field:<35} | {description:<30} | No data")
    
    print(f"\n💾 STORAGE RECOMMENDATIONS:")
    print("1. Add middle_initial to participant parsing")
    print("2. Store complete address (line1, zip_code)")
    print("3. Add shirt_size field for logistics")
    print("4. Capture race-specific fields (corral, wave, chip)")
    print("5. Store communication preferences")
    print("6. Consider adding custom fields table for additional_questions")

if __name__ == "__main__":
    analyze_missing_fields() 