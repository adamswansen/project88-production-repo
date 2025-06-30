import re

# Read the app file
with open('app.py', 'r') as f:
    content = f.read()

# Add Redis roster storage functions
redis_functions = '''
def store_roster_data_in_redis(roster_data, race_name_data):
    """Store roster data in Redis for session persistence"""
    try:
        redis_client = app.config['SESSION_REDIS']
        # Use a session-specific key
        session_key = session.get('session_key', 'default_session')
        roster_key = f"roster_data:{session_key}"
        race_name_key = f"race_name:{session_key}"
        
        # Store data with expiration (1 hour)
        redis_client.setex(roster_key, 3600, json.dumps(roster_data))
        redis_client.setex(race_name_key, 3600, race_name_data)
        
        logger.info(f"Stored {len(roster_data)} roster entries in Redis for session {session_key}")
        return True
    except Exception as e:
        logger.error(f"Failed to store roster data in Redis: {e}")
        return False

def get_roster_data_from_redis():
    """Get roster data from Redis for current session"""
    try:
        redis_client = app.config['SESSION_REDIS']
        session_key = session.get('session_key', 'default_session')
        roster_key = f"roster_data:{session_key}"
        
        roster_json = redis_client.get(roster_key)
        if roster_json:
            roster_data = json.loads(roster_json)
            logger.info(f"Retrieved {len(roster_data)} roster entries from Redis for session {session_key}")
            return roster_data
        return {}
    except Exception as e:
        logger.error(f"Failed to get roster data from Redis: {e}")
        return {}

def get_race_name_from_redis():
    """Get race name from Redis for current session"""
    try:
        redis_client = app.config['SESSION_REDIS']
        session_key = session.get('session_key', 'default_session')
        race_name_key = f"race_name:{session_key}"
        
        race_name = redis_client.get(race_name_key)
        return race_name.decode('utf-8') if race_name else 'Unknown Race'
    except Exception as e:
        logger.error(f"Failed to get race name from Redis: {e}")
        return 'Unknown Race'

'''

# Insert the Redis functions after the imports
import_section = content.find('# Global variables')
if import_section == -1:
    import_section = content.find('roster_data = {}')

content = content[:import_section] + redis_functions + '\n' + content[import_section:]

# Update the fetch_complete_roster function to store in Redis and set session key
old_roster_function = '''def fetch_complete_roster(event_id, credentials):
    """Fetch all pages of roster data"""
    global roster_data, race_name, login_progress
    roster_data = {}'''

new_roster_function = '''def fetch_complete_roster(event_id, credentials):
    """Fetch all pages of roster data"""
    global login_progress
    roster_data = {}
    
    # Ensure session has a consistent key
    if 'session_key' not in session:
        session['session_key'] = f"session_{int(time.time())}_{secrets.token_hex(8)}"
    '''

content = content.replace(old_roster_function, new_roster_function)

# Update the end of fetch_complete_roster to store in Redis
old_completion = '''    login_progress['complete'] = True
    # Extract race name from first entry
    race_name = 'Unknown Race'
    if 'event_entry' in data and data['event_entry']:
        race_name = data['event_entry'][0].get('race_name', 'Unknown Race')
    elif 'entries' in data and data['entries']:
        race_name = data['entries'][0].get('race_name', 'Unknown Race')
    elif isinstance(data, list) and data:
        race_name = data[0].get('race_name', 'Unknown Race')
    return True'''

new_completion = '''    login_progress['complete'] = True
    # Extract race name from first entry
    race_name = 'Unknown Race'
    if 'event_entry' in data and data['event_entry']:
        race_name = data['event_entry'][0].get('race_name', 'Unknown Race')
    elif 'entries' in data and data['entries']:
        race_name = data['entries'][0].get('race_name', 'Unknown Race')
    elif isinstance(data, list) and data:
        race_name = data[0].get('race_name', 'Unknown Race')
    
    # Store in Redis instead of global variables
    store_roster_data_in_redis(roster_data, race_name)
    return True'''

content = content.replace(old_completion, new_completion)

# Update get_current_runner to use Redis instead of global roster_data
old_current_runner = '''        # Check if roster is loaded first
        if not roster_data:
            logger.info("No roster data loaded - returning empty response")
            return jsonify({})'''

new_current_runner = '''        # Check if roster is loaded first (from Redis)
        roster_data = get_roster_data_from_redis()
        if not roster_data:
            logger.info("No roster data loaded - returning empty response")
            return jsonify({})'''

content = content.replace(old_current_runner, new_current_runner)

# Update the bib lookup to use the local roster_data variable
old_bib_lookup = '''        # Only return data if the bib exists in the roster
        if bib not in roster_data:
            logger.info(f"Bib {bib} not found in roster (roster has {len(roster_data)} entries) - returning empty response")
            return jsonify({})'''

new_bib_lookup = '''        # Only return data if the bib exists in the roster
        if bib not in roster_data:
            logger.info(f"Bib {bib} not found in roster (roster has {len(roster_data)} entries) - returning empty response")
            return jsonify({})'''

# This doesn't need to change since we're using the local roster_data variable

# Update login endpoint to return session info
old_login_response = '''            response.update({
                "success": True,
                "status": "Ready to display timing data",
                "stage": 3,
                "race_name": race_name,
                "runners_loaded": len(roster_data),
                "credentials_valid": True,'''

new_login_response = '''            response.update({
                "success": True,
                "status": "Ready to display timing data",
                "stage": 3,
                "race_name": get_race_name_from_redis(),
                "runners_loaded": len(get_roster_data_from_redis()),
                "credentials_valid": True,
                "session_key": session.get('session_key'),'''

content = content.replace(old_login_response, new_login_response)

# Write the updated content
with open('app.py', 'w') as f:
    f.write(content)

print('✅ Updated roster data storage to use Redis sessions for multi-worker consistency') 