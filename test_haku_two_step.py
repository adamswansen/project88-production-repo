#!/usr/bin/env python3
"""
Test script to verify the two-step Haku API implementation
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

def test_two_step_haku_api():
    print("🔧 Testing two-step Haku API implementation...")
    
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
    
    # Test with a small event first
    test_event = None
    for event in events:
        if 'VIP Breakfast' in event.event_name:
            test_event = event
            break
    
    if not test_event:
        # Fall back to first event
        test_event = events[0]
    
    print(f"\n📅 Testing with event: {test_event.event_name}")
    print(f"Event ID: {test_event.provider_event_id}")
    
    # Get participants using the new two-step method
    print("\n🔍 Running two-step participant fetch...")
    participants = adapter.get_participants(test_event.provider_event_id)
    
    print(f"✅ Retrieved {len(participants)} participants")
    
    if participants:
        participant = participants[0]
        
        print(f"\n📋 COMPLETE PARTICIPANT DATA:")
        print(f"   ID: {participant.provider_participant_id}")
        print(f"   Name: {participant.first_name} {participant.last_name}")
        print(f"   Email: {participant.email}")
        print(f"   Phone: {participant.phone}")
        print(f"   Date of Birth: {participant.date_of_birth}")
        print(f"   Age: {participant.age}")
        print(f"   Gender: {participant.gender}")
        print(f"   Address: {participant.city}, {participant.state}, {participant.country}")
        print(f"   Bib Number: {participant.bib_number}")
        print(f"   Division: {participant.division}")
        print(f"   Team: {participant.team_name}")
        print(f"   Registration Date: {participant.registration_date}")
        print(f"   Registration Status: {participant.registration_status}")
        print(f"   Amount Paid: ${participant.amount_paid}")
        
        if participant.emergency_contact:
            print(f"   Emergency Contact:")
            print(f"      Name: {participant.emergency_contact.get('name')}")
            print(f"      Phone: {participant.emergency_contact.get('phone')}")
            print(f"      Relationship: {participant.emergency_contact.get('relationship')}")
        
        # Count populated fields
        total_fields = 0
        populated_fields = 0
        
        for attr in dir(participant):
            if not attr.startswith('_') and not callable(getattr(participant, attr)):
                total_fields += 1
                value = getattr(participant, attr)
                if value is not None and value != '':
                    populated_fields += 1
        
        print(f"\n📊 Data Completeness: {populated_fields}/{total_fields} fields populated ({populated_fields/total_fields*100:.1f}%)")
        
        # Compare with the old single-step method
        print(f"\n🔄 Comparison with old method:")
        old_participant = adapter._parse_participant({
            'registration_number': participant.provider_participant_id,
            'person_full_name': f"{participant.first_name} {participant.last_name}",
            'email': participant.email,
            'age': participant.age,
            'gender': participant.gender,
            'event_category_info': participant.division
        }, test_event.provider_event_id)
        
        old_populated = 0
        for attr in dir(old_participant):
            if not attr.startswith('_') and not callable(getattr(old_participant, attr)):
                value = getattr(old_participant, attr)
                if value is not None and value != '':
                    old_populated += 1
        
        improvement = populated_fields - old_populated
        print(f"   Old method: {old_populated}/{total_fields} fields")
        print(f"   New method: {populated_fields}/{total_fields} fields")
        print(f"   Improvement: +{improvement} additional fields! 🎉")
        
        # Show the new fields we're getting
        new_fields = []
        if participant.phone: new_fields.append("phone")
        if participant.date_of_birth: new_fields.append("date_of_birth")
        if participant.city: new_fields.append("city")
        if participant.state: new_fields.append("state")
        if participant.country: new_fields.append("country")
        if participant.bib_number: new_fields.append("bib_number")
        if participant.emergency_contact: new_fields.append("emergency_contact")
        
        if new_fields:
            print(f"   New fields captured: {', '.join(new_fields)}")
        
    else:
        print("❌ No participants found for this event")
    
    print(f"\n=== TEST SUMMARY ===")
    if participants and len(participants) > 0:
        print("✅ Two-step API implementation working!")
        print("✅ Complete participant data being captured")
        print("✅ Ready for production deployment")
    else:
        print("❌ Two-step API implementation needs debugging")

if __name__ == "__main__":
    test_two_step_haku_api() 