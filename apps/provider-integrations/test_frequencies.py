#!/usr/bin/env python3
"""Simple test for frequency calculations without database dependencies"""

from datetime import datetime, timedelta

def calculate_sync_frequency(event_start_time: datetime, current_time: datetime) -> int:
    """Calculate sync frequency in minutes based on time until event start"""
    time_until_start = event_start_time - current_time
    time_since_start = current_time - event_start_time
    
    # Stop syncing 1 hour after event start
    if time_since_start > timedelta(hours=1):
        return 0  # Stop syncing
    
    # Within 4 hours (including post-start until +1hr): Every minute
    if time_until_start <= timedelta(hours=4):
        return 1
    
    # Within 24 hours: Every 5 minutes
    elif time_until_start <= timedelta(hours=24):
        return 5
    
    # Outside 24 hours: Every hour
    else:
        return 60

# Test the frequency calculations
print("🧪 Testing sync frequency calculations")
now = datetime.now()
test_times = [
    ("2 days ahead", now + timedelta(days=2)),
    ("12 hours ahead", now + timedelta(hours=12)),
    ("2 hours ahead", now + timedelta(hours=2)),
    ("30 minutes ahead", now + timedelta(minutes=30)),
    ("10 minutes ago", now - timedelta(minutes=10)),
    ("2 hours ago", now - timedelta(hours=2))
]

for label, test_time in test_times:
    freq = calculate_sync_frequency(test_time, now)
    print(f"{label:20} -> {freq:3d} minutes (or stop if 0)")
