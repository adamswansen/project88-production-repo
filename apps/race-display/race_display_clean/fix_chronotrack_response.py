import re

# Read the app file
with open('app.py', 'r') as f:
    content = f.read()

# Replace the fetch_complete_roster function to handle different response structures
old_loop = """        for entry in data.get('event_entry', []):
            try:
                roster_data[entry['bib']] = {"""

new_loop = """        # Try different possible response structures from ChronoTrack API
        entries = []
        if 'event_entry' in data:
            entries = data['event_entry']
        elif 'entries' in data:
            entries = data['entries']
        elif 'data' in data:
            entries = data['data']
        elif 'results' in data:
            entries = data['results']
        elif isinstance(data, list):
            entries = data
        else:
            # Log available keys for debugging
            logger.error(f"Unknown ChronoTrack response structure. Available keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            continue
        
        for entry in entries:
            try:
                # Try different possible bib field names
                bib = entry.get('bib') or entry.get('entry_bib') or entry.get('number') or entry.get('bibNumber')
                if not bib:
                    continue
                    
                roster_data[bib] = {"""

content = content.replace(old_loop, new_loop)

# Also update the race_name extraction to be more flexible
old_race_name = """    race_name = data.get('event_entry', [{}])[0].get('race_name', 'Unknown Race')"""
new_race_name = """    # Extract race name from first entry
    race_name = 'Unknown Race'
    if 'event_entry' in data and data['event_entry']:
        race_name = data['event_entry'][0].get('race_name', 'Unknown Race')
    elif 'entries' in data and data['entries']:
        race_name = data['entries'][0].get('race_name', 'Unknown Race')
    elif isinstance(data, list) and data:
        race_name = data[0].get('race_name', 'Unknown Race')"""

content = content.replace(old_race_name, new_race_name)

# Also make the response structure check more forgiving
old_check = """        if not isinstance(data, dict) or 'event_entry' not in data:
            return None, None"""

new_check = """        # Accept various response structures
        if not isinstance(data, (dict, list)):
            logger.error(f"ChronoTrack API returned unexpected data type: {type(data)}")
            return None, None
        
        # If it's a dict, check for common entry keys
        if isinstance(data, dict) and not any(key in data for key in ['event_entry', 'entries', 'data', 'results']):
            logger.error(f"ChronoTrack API response missing expected keys. Available: {list(data.keys())}")
            return None, None"""

content = content.replace(old_check, new_check)

# Write the updated content
with open('app.py', 'w') as f:
    f.write(content)

print('✅ Updated ChronoTrack response handling to support multiple API formats') 