import re

# Read the app file
with open('app.py', 'r') as f:
    content = f.read()

# Update get_roster_data_from_redis to accept session_key parameter
old_get_roster = '''def get_roster_data_from_redis():
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
        return {}'''

new_get_roster = '''def get_roster_data_from_redis(session_key_param=None):
    """Get roster data from Redis for current session or specified session"""
    try:
        redis_client = app.config['SESSION_REDIS']
        session_key = session_key_param or session.get('session_key', 'default_session')
        roster_key = f"roster_data:{session_key}"
        
        roster_json = redis_client.get(roster_key)
        if roster_json:
            roster_data = json.loads(roster_json)
            logger.info(f"Retrieved {len(roster_data)} roster entries from Redis for session {session_key}")
            return roster_data
        return {}
    except Exception as e:
        logger.error(f"Failed to get roster data from Redis: {e}")
        return {}'''

content = content.replace(old_get_roster, new_get_roster)

# Update current-runner endpoint to accept session_key parameter
old_current_runner = '''@app.route('/api/current-runner')
def get_current_runner():
    """Return current runner data from the database - ONLY if both timing data AND roster data exist AND timing is recent (within 5 seconds)"""
    try:
        # Check if roster is loaded first (from Redis)
        roster_data = get_roster_data_from_redis()
        if not roster_data:
            logger.info("No roster data loaded - returning empty response")
            return jsonify({})'''

new_current_runner = '''@app.route('/api/current-runner')
def get_current_runner():
    """Return current runner data from the database - ONLY if both timing data AND roster data exist AND timing is recent (within 5 seconds)"""
    try:
        # Check for session_key parameter in URL
        session_key_param = request.args.get('session_key')
        
        # Check if roster is loaded first (from Redis)
        roster_data = get_roster_data_from_redis(session_key_param)
        if not roster_data:
            logger.info(f"No roster data loaded for session {session_key_param or 'current'} - returning empty response")
            return jsonify({})'''

content = content.replace(old_current_runner, new_current_runner)

# Add a new endpoint to get the current session key
session_key_endpoint = '''
@app.route('/api/session-key')
def get_session_key():
    """Return the current session key for use in display windows"""
    session_key = session.get('session_key', 'default_session')
    return jsonify({'session_key': session_key})
'''

# Insert the new endpoint after the current-runner endpoint
insertion_point = content.find('@app.route(\'/api/debug/timing\')')
if insertion_point != -1:
    content = content[:insertion_point] + session_key_endpoint + '\n' + content[insertion_point:]

# Write the updated content
with open('app.py', 'w') as f:
    f.write(content)

print('✅ Added session key parameter support to current-runner API') 