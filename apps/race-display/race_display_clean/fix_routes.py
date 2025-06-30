import re
import psycopg2
from flask import jsonify
from datetime import datetime

# Read the file
with open('app.py', 'r') as f:
    content = f.read()

# Add health endpoint before the catch-all route
health_endpoint = '''
@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        db_connected = True
    except:
        db_connected = False
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0',
        'database_connected': db_connected
    })
'''

# Insert health endpoint before the catch-all route
insert_point = content.find('@app.route("/<path:path>")')
if insert_point != -1:
    content = content[:insert_point] + health_endpoint + '\n' + content[insert_point:]

# Fix catch-all route to exclude API paths
old_func = '''def serve_react_routes(path):
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')'''

new_func = '''def serve_react_routes(path):
    # Don't serve React for API endpoints
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    
    file_path = os.path.join(app.static_folder, path)
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')'''

content = content.replace(old_func, new_func)

# Write the fixed content
with open('app.py', 'w') as f:
    f.write(content)

print('✅ Fixed routing issues')
