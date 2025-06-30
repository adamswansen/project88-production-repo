import re
from datetime import datetime, timedelta

# Read the app file
with open('app.py', 'r') as f:
    content = f.read()

# Add datetime import at the top if not already there
if 'from datetime import' not in content:
    content = content.replace('import json', 'import json\nfrom datetime import datetime, timedelta')

# Replace the get_current_runner function to include 5-second timeout
old_function = '''def get_current_runner():
    """Return current runner data from the database - ONLY if both timing data AND roster data exist"""
    try:
        # Check if roster is loaded first
        if not roster_data:
            logger.info("No roster data loaded - returning empty response")
            return jsonify({})
        
        # Get latest timing data from database
        timing_data = get_latest_timing_read()
        if not timing_data:
            logger.info("No timing data available - returning empty response")
            return jsonify({})
        
        bib = timing_data.get('bib')
        if not bib:
            logger.info("No bib number in timing data - returning empty response")
            return jsonify({})
            
        # Only return data if the bib exists in the roster
        if bib not in roster_data:
            logger.info(f"Bib {bib} not found in roster (roster has {len(roster_data)} entries) - returning empty response")
            return jsonify({})
        
        # We have both timing data and matching roster data - return full runner info
        runner_data = get_runner_from_timing_data(timing_data)
        if runner_data:
            logger.info(f"Returning runner data for {runner_data.get('name', 'Unknown')} (bib {bib})")
            return jsonify(runner_data)
        
        return jsonify({})
    except Exception as e:
        logger.error(f"Error getting current runner: {e}")
        return jsonify({})'''

new_function = '''def get_current_runner():
    """Return current runner data from the database - ONLY if both timing data AND roster data exist AND timing is recent (within 5 seconds)"""
    try:
        # Check if roster is loaded first
        if not roster_data:
            logger.info("No roster data loaded - returning empty response")
            return jsonify({})
        
        # Get latest timing data from database
        timing_data = get_latest_timing_read()
        if not timing_data:
            logger.info("No timing data available - returning empty response")
            return jsonify({})
        
        # Check if timing data is recent (within 5 seconds)
        read_timestamp = timing_data.get('read_timestamp')
        if read_timestamp:
            try:
                # Parse the timestamp
                if isinstance(read_timestamp, str):
                    timestamp = datetime.fromisoformat(read_timestamp.replace('Z', '+00:00'))
                else:
                    timestamp = read_timestamp
                
                # Check if it's older than 5 seconds
                now = datetime.now(timestamp.tzinfo) if timestamp.tzinfo else datetime.now()
                time_diff = now - timestamp
                
                if time_diff > timedelta(seconds=5):
                    logger.info(f"Timing data is {time_diff.total_seconds():.1f} seconds old - returning empty response (timeout after 5s)")
                    return jsonify({})
                    
            except Exception as e:
                logger.error(f"Error parsing timestamp {read_timestamp}: {e}")
                return jsonify({})
        
        bib = timing_data.get('bib')
        if not bib:
            logger.info("No bib number in timing data - returning empty response")
            return jsonify({})
            
        # Only return data if the bib exists in the roster
        if bib not in roster_data:
            logger.info(f"Bib {bib} not found in roster (roster has {len(roster_data)} entries) - returning empty response")
            return jsonify({})
        
        # We have both timing data and matching roster data and it's recent - return full runner info
        runner_data = get_runner_from_timing_data(timing_data)
        if runner_data:
            logger.info(f"Returning runner data for {runner_data.get('name', 'Unknown')} (bib {bib}) - data is fresh")
            return jsonify(runner_data)
        
        return jsonify({})
    except Exception as e:
        logger.error(f"Error getting current runner: {e}")
        return jsonify({})'''

content = content.replace(old_function, new_function)

# Write the updated content
with open('app.py', 'w') as f:
    f.write(content)

print('✅ Added 5-second timeout to current-runner endpoint') 