import re

# Read the file
with open('app.py', 'r') as f:
    content = f.read()

# Find the catch-all route and everything after it
catch_all_pattern = r'(@app\.route\(\'/\'\)\ndef serve_react.*?@app\.route\(\'/<path:path>\'\)\ndef serve_react_routes.*?return send_from_directory\(app\.static_folder, \'index\.html\'\))'
match = re.search(catch_all_pattern, content, re.DOTALL)

if match:
    catch_all_section = match.group(1)
    
    # Find any API routes that come after the catch-all
    after_catch_all = content[match.end():]
    
    # Extract API routes that come after catch-all
    api_routes_after = []
    api_pattern = r'(@app\.route\(\'\/api\/[^\']+\'[^@]+?(?=@app\.route|$))'
    api_matches = re.finditer(api_pattern, after_catch_all, re.DOTALL)
    
    for api_match in api_matches:
        api_routes_after.append(api_match.group(1))
    
    # Remove the API routes from after catch-all
    for api_route in api_routes_after:
        after_catch_all = after_catch_all.replace(api_route, '')
    
    # Add health endpoint to the API routes
    health_endpoint = '''@app.route('/api/health')
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
    
    # Fix catch-all route to exclude API paths
    fixed_catch_all = catch_all_section.replace(
        'def serve_react_routes(path):\n    file_path = os.path.join(app.static_folder, path)',
        '''def serve_react_routes(path):
    # Don't serve React for API endpoints
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
    
    file_path = os.path.join(app.static_folder, path)'''
    )
    
    # Reconstruct the file: before catch-all + API routes + health + fixed catch-all + after
    before_catch_all = content[:match.start()]
    
    new_content = (before_catch_all + 
                   ''.join(api_routes_after) + 
                   health_endpoint + 
                   fixed_catch_all + 
                   after_catch_all)
    
    # Write the fixed content
    with open('app.py', 'w') as f:
        f.write(new_content)
    
    print('✅ Fixed route order - moved API routes before catch-all')
else:
    print('❌ Could not find catch-all route pattern') 