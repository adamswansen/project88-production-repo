#!/usr/bin/env python3
"""
Project88 Dashboard Application
Comprehensive metrics dashboard with timing partner filtering
"""

from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
import json
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional
import redis
from functools import wraps
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'project88_myappdb'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
}

# Redis configuration for caching
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', '6379')),
    'db': int(os.getenv('REDIS_DB', '0')),
}

# Cache configuration
CACHE_TTL = 300  # 5 minutes

class DatabaseManager:
    """Database connection and query manager"""
    
    def __init__(self):
        self.connection = None
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(**REDIS_CONFIG)
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis_client = None
    
    def get_connection(self):
        """Get database connection with retry logic"""
        if self.connection is None or self.connection.closed:
            try:
                self.connection = psycopg2.connect(**DB_CONFIG)
                self.connection.autocommit = True
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise
        return self.connection
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query and return results"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                if cursor.description:
                    return [dict(row) for row in cursor.fetchall()]
                return []
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def cache_get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        if not self.redis_client:
            return None
        try:
            cached = self.redis_client.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache get failed: {e}")
        return None
    
    def cache_set(self, key: str, value: Any, ttl: int = CACHE_TTL):
        """Set cached value"""
        if not self.redis_client:
            return
        try:
            self.redis_client.setex(key, ttl, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")

# Global database manager
db = DatabaseManager()

def cache_result(cache_key_prefix: str, ttl: int = CACHE_TTL):
    """Decorator for caching API results"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Build cache key
            timing_partner_id = request.args.get('timing_partner_id', 'all')
            cache_key = f"{cache_key_prefix}:{timing_partner_id}"
            
            # Try to get from cache
            cached_result = db.cache_get(cache_key)
            if cached_result:
                return cached_result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            db.cache_set(cache_key, result, ttl)
            return result
        return decorated_function
    return decorator

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute_query("SELECT 1")
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'database': 'connected',
                'redis': 'connected' if db.redis_client else 'disconnected'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/overview')
@cache_result('overview')
def get_overview():
    """Get platform overview statistics"""
    try:
        timing_partner_id = request.args.get('timing_partner_id')
        
        # Build base queries with optional timing partner filter
        filter_clause = ""
        params = []
        
        if timing_partner_id and timing_partner_id != 'all':
            filter_clause = "WHERE timing_partner_id = %s"
            params = [timing_partner_id]
        
        # Get total counts across all providers
        queries = {
            'timing_partners': "SELECT COUNT(*) as count FROM timing_partners",
            'total_events': f"""
                SELECT COUNT(*) as count FROM (
                    SELECT event_id FROM runsignup_events {filter_clause}
                    UNION ALL
                    SELECT event_id FROM ct_events {filter_clause}
                    UNION ALL
                    SELECT event_id FROM raceroster_events {filter_clause}
                    UNION ALL
                    SELECT event_id FROM copernico_events {filter_clause}
                    UNION ALL
                    SELECT event_id FROM haku_events {filter_clause}
                ) as all_events
            """,
            'total_participants': f"""
                SELECT COUNT(*) as count FROM (
                    SELECT id FROM runsignup_participants {filter_clause}
                    UNION ALL
                    SELECT entry_id FROM ct_participants {filter_clause}
                    UNION ALL
                    SELECT id FROM raceroster_participants {filter_clause}
                    UNION ALL
                    SELECT id FROM copernico_participants {filter_clause}
                    UNION ALL
                    SELECT id FROM haku_participants {filter_clause}
                ) as all_participants
            """,
            'total_results': f"""
                SELECT COUNT(*) as count FROM (
                    SELECT id FROM ct_results {filter_clause}
                    UNION ALL
                    SELECT id FROM copernico_results {filter_clause}
                ) as all_results
            """,
        }
        
        # Execute queries
        results = {}
        for key, query in queries.items():
            if key == 'timing_partners' and timing_partner_id and timing_partner_id != 'all':
                results[key] = 1  # Single partner selected
            else:
                query_params = params if key != 'timing_partners' else []
                result = db.execute_query(query, query_params)
                results[key] = result[0]['count'] if result else 0
        
        # Get provider breakdown
        provider_breakdown = []
        providers = [
            ('RunSignUp', 'runsignup_events', 'runsignup_participants'),
            ('ChronoTrack', 'ct_events', 'ct_participants'),
            ('Race Roster', 'raceroster_events', 'raceroster_participants'),
            ('Copernico', 'copernico_events', 'copernico_participants'),
            ('Haku', 'haku_events', 'haku_participants'),
        ]
        
        for provider_name, events_table, participants_table in providers:
            events_query = f"SELECT COUNT(*) as count FROM {events_table} {filter_clause}"
            participants_query = f"SELECT COUNT(*) as count FROM {participants_table} {filter_clause}"
            
            events_result = db.execute_query(events_query, params)
            participants_result = db.execute_query(participants_query, params)
            
            provider_breakdown.append({
                'provider': provider_name,
                'events': events_result[0]['count'] if events_result else 0,
                'participants': participants_result[0]['count'] if participants_result else 0
            })
        
        # Get timing partners list
        timing_partners = db.execute_query("""
            SELECT timing_partner_id, company_name, contact_email, created_at
            FROM timing_partners
            ORDER BY company_name
        """)
        
        return jsonify({
            'overview': results,
            'provider_breakdown': provider_breakdown,
            'timing_partners': timing_partners,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Overview endpoint failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/providers')
@cache_result('providers')
def get_providers():
    """Get provider statistics and status"""
    try:
        timing_partner_id = request.args.get('timing_partner_id')
        
        filter_clause = ""
        params = []
        
        if timing_partner_id and timing_partner_id != 'all':
            filter_clause = "WHERE timing_partner_id = %s"
            params = [timing_partner_id]
        
        # Get detailed provider statistics
        provider_stats = []
        
        # RunSignUp
        runsignup_stats = db.execute_query(f"""
            SELECT 
                COUNT(DISTINCT e.event_id) as events,
                COUNT(DISTINCT p.id) as participants,
                0 as results,
                MIN(e.created_at) as first_event_date,
                MAX(e.created_at) as last_event_date,
                COUNT(DISTINCT DATE(e.created_at)) as active_days
            FROM runsignup_events e
            LEFT JOIN runsignup_participants p ON e.event_id = p.event_id
            {filter_clause}
        """, params)
        
        provider_stats.append({
            'provider': 'RunSignUp',
            'status': 'Active',
            'type': 'Registration',
            **runsignup_stats[0] if runsignup_stats else {}
        })
        
        # ChronoTrack
        chronotrack_stats = db.execute_query(f"""
            SELECT 
                COUNT(DISTINCT e.event_id) as events,
                COUNT(DISTINCT p.entry_id) as participants,
                COUNT(DISTINCT r.id) as results,
                MIN(e.created_at) as first_event_date,
                MAX(e.created_at) as last_event_date,
                COUNT(DISTINCT DATE(e.created_at)) as active_days
            FROM ct_events e
            LEFT JOIN ct_participants p ON e.event_id = p.event_id
            LEFT JOIN ct_results r ON e.event_id = r.event_id
            {filter_clause}
        """, params)
        
        provider_stats.append({
            'provider': 'ChronoTrack',
            'status': 'Active',
            'type': 'Timing & Registration',
            **chronotrack_stats[0] if chronotrack_stats else {}
        })
        
        # Ready providers (no data yet)
        ready_providers = [
            ('Race Roster', 'Registration'),
            ('Copernico', 'Timing & Registration'),
            ('Haku', 'Registration'),
        ]
        
        for provider_name, provider_type in ready_providers:
            provider_stats.append({
                'provider': provider_name,
                'status': 'Ready',
                'type': provider_type,
                'events': 0,
                'participants': 0,
                'results': 0,
                'first_event_date': None,
                'last_event_date': None,
                'active_days': 0
            })
        
        return jsonify({
            'providers': provider_stats,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Providers endpoint failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/timing-partners')
@cache_result('timing_partners')
def get_timing_partners():
    """Get timing partner statistics"""
    try:
        # Get all timing partners with their statistics
        timing_partners = db.execute_query("""
            SELECT 
                tp.timing_partner_id,
                tp.company_name,
                tp.contact_email,
                tp.api_access_enabled,
                tp.created_at,
                COUNT(DISTINCT u.id) as user_count
            FROM timing_partners tp
            LEFT JOIN users u ON tp.timing_partner_id = u.timing_partner_id
            GROUP BY tp.timing_partner_id, tp.company_name, tp.contact_email, tp.api_access_enabled, tp.created_at
            ORDER BY tp.company_name
        """)
        
        # Get event counts per timing partner
        for partner in timing_partners:
            partner_id = partner['timing_partner_id']
            
            # Get events across all providers
            events_query = """
                SELECT COUNT(*) as count FROM (
                    SELECT event_id FROM runsignup_events WHERE timing_partner_id = %s
                    UNION ALL
                    SELECT event_id FROM ct_events WHERE timing_partner_id = %s
                    UNION ALL
                    SELECT event_id FROM raceroster_events WHERE timing_partner_id = %s
                    UNION ALL
                    SELECT event_id FROM copernico_events WHERE timing_partner_id = %s
                    UNION ALL
                    SELECT event_id FROM haku_events WHERE timing_partner_id = %s
                ) as all_events
            """
            
            events_result = db.execute_query(events_query, [partner_id] * 5)
            partner['total_events'] = events_result[0]['count'] if events_result else 0
            
            # Get participants across all providers
            participants_query = """
                SELECT COUNT(*) as count FROM (
                    SELECT id FROM runsignup_participants WHERE timing_partner_id = %s
                    UNION ALL
                    SELECT entry_id FROM ct_participants WHERE timing_partner_id = %s
                    UNION ALL
                    SELECT id FROM raceroster_participants WHERE timing_partner_id = %s
                    UNION ALL
                    SELECT id FROM copernico_participants WHERE timing_partner_id = %s
                    UNION ALL
                    SELECT id FROM haku_participants WHERE timing_partner_id = %s
                ) as all_participants
            """
            
            participants_result = db.execute_query(participants_query, [partner_id] * 5)
            partner['total_participants'] = participants_result[0]['count'] if participants_result else 0
        
        return jsonify({
            'timing_partners': timing_partners,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Timing partners endpoint failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/real-time')
@cache_result('real_time', ttl=30)  # Cache for 30 seconds only
def get_real_time_metrics():
    """Get real-time system metrics"""
    try:
        # Note: Adjust these queries based on your actual timing tables
        # The schema shows raw_tag_data database for live timing
        
        # Get recent activity (last 24 hours)
        recent_activity = db.execute_query("""
            SELECT 
                'event_created' as activity_type,
                'RunSignUp' as provider,
                name as description,
                created_at as timestamp
            FROM runsignup_events
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            
            UNION ALL
            
            SELECT 
                'event_created' as activity_type,
                'ChronoTrack' as provider,
                event_name as description,
                created_at as timestamp
            FROM ct_events
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            
            ORDER BY timestamp DESC
            LIMIT 50
        """)
        
        # Get system health metrics
        health_metrics = {
            'database_connections': 1,  # Current connection
            'cache_status': 'connected' if db.redis_client else 'disconnected',
            'last_sync': datetime.now().isoformat(),
            'uptime': '24/7',  # Based on your production status
        }
        
        # Get provider sync status
        sync_status = db.execute_query("""
            SELECT 
                provider_name,
                sync_type,
                status,
                records_processed,
                completed_at
            FROM sync_history
            WHERE completed_at >= NOW() - INTERVAL '24 hours'
            ORDER BY completed_at DESC
            LIMIT 20
        """)
        
        return jsonify({
            'recent_activity': recent_activity,
            'health_metrics': health_metrics,
            'sync_status': sync_status,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Real-time metrics endpoint failed: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics')
@cache_result('analytics')
def get_analytics():
    """Get analytics and trends"""
    try:
        timing_partner_id = request.args.get('timing_partner_id')
        
        filter_clause = ""
        params = []
        
        if timing_partner_id and timing_partner_id != 'all':
            filter_clause = "WHERE timing_partner_id = %s"
            params = [timing_partner_id]
        
        # Get monthly growth trends
        monthly_trends = db.execute_query(f"""
            SELECT 
                DATE_TRUNC('month', created_at) as month,
                COUNT(*) as events,
                'events' as metric_type
            FROM (
                SELECT created_at FROM runsignup_events {filter_clause}
                UNION ALL
                SELECT created_at FROM ct_events {filter_clause}
            ) as all_events
            WHERE created_at >= NOW() - INTERVAL '12 months'
            GROUP BY DATE_TRUNC('month', created_at)
            ORDER BY month
        """, params)
        
        # Get geographic distribution
        geographic_data = db.execute_query(f"""
            SELECT 
                COALESCE(address->>'state', location->>'region', 'Unknown') as region,
                COUNT(*) as events
            FROM (
                SELECT address FROM runsignup_events {filter_clause}
                UNION ALL
                SELECT location as address FROM ct_events {filter_clause}
            ) as all_events
            GROUP BY region
            ORDER BY events DESC
            LIMIT 20
        """, params)
        
        # Get event size distribution
        event_sizes = db.execute_query(f"""
            SELECT 
                CASE 
                    WHEN participant_count < 50 THEN 'Small (< 50)'
                    WHEN participant_count < 200 THEN 'Medium (50-200)'
                    WHEN participant_count < 500 THEN 'Large (200-500)'
                    ELSE 'Very Large (500+)'
                END as size_category,
                COUNT(*) as events
            FROM (
                SELECT 
                    event_id,
                    COUNT(*) as participant_count
                FROM runsignup_participants
                {filter_clause}
                GROUP BY event_id
            ) as event_participant_counts
            GROUP BY size_category
            ORDER BY events DESC
        """, params)
        
        return jsonify({
            'monthly_trends': monthly_trends,
            'geographic_data': geographic_data,
            'event_sizes': event_sizes,
            'last_updated': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Analytics endpoint failed: {e}")
        return jsonify({'error': str(e)}), 500

# Static files
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('../static', filename)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5004))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Project88 Dashboard on port {port}")
    logger.info(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 