"""
Flask Application with Enhanced Authentication Backend
Integrates with Project88hub landing page and authentication system
"""

from flask import Flask, request, jsonify, render_template, redirect, url_for, session, Response
from flask_cors import CORS
import os
import secrets
from datetime import datetime, timedelta
import logging
from enhanced_auth_system import Project88AuthManager, SubdomainAccessMiddleware, StripeWebhookHandler
import stripe
from functools import wraps
import jwt
import asyncio
import ssl
import redis
import psycopg2.extras
from flask import stream_template
import queue
import threading
import time
import json

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configure CORS for subdomain access
CORS(app, origins=[
    'https://www.project88hub.com',
    'https://display.project88hub.com',
    'https://analytics.project88hub.com',
    'https://ai.project88hub.com',
    'https://admin.project88hub.com'
])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize authentication system
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/project88hub')
auth_manager = Project88AuthManager(DATABASE_URL, app.secret_key)
subdomain_middleware = SubdomainAccessMiddleware(auth_manager)

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
stripe_webhook_handler = StripeWebhookHandler(auth_manager)

# Add ChronoTrack connection management after existing configuration
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_client = redis.from_url(REDIS_URL)

# ChronoTrack connection pool and session management
class ChronoTrackSessionManager:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.active_connections = {}
        self.preview_queues = {}
        
    def store_connection_test(self, user_id, credential_name, connection_data):
        """Store connection test results"""
        key = f"chronotrack:test:{user_id}:{credential_name}"
        self.redis.setex(key, 300, json.dumps(connection_data))  # 5 min expiry
        
    def get_connection_test(self, user_id, credential_name):
        """Get connection test results"""
        key = f"chronotrack:test:{user_id}:{credential_name}"
        data = self.redis.get(key)
        return json.loads(data) if data else None
        
    def start_preview_session(self, user_id, credential_name):
        """Start a data preview session"""
        session_key = f"preview:{user_id}:{credential_name}"
        self.preview_queues[session_key] = queue.Queue(maxsize=100)
        return session_key
        
    def stop_preview_session(self, session_key):
        """Stop a data preview session"""
        if session_key in self.preview_queues:
            del self.preview_queues[session_key]
            
    def add_preview_data(self, session_key, data):
        """Add data to preview queue"""
        if session_key in self.preview_queues:
            try:
                self.preview_queues[session_key].put_nowait(data)
            except queue.Full:
                # Remove oldest item and add new one
                try:
                    self.preview_queues[session_key].get_nowait()
                    self.preview_queues[session_key].put_nowait(data)
                except queue.Empty:
                    pass

chronotrack_manager = ChronoTrackSessionManager(redis_client)

# Subscription tier limits
SUBSCRIPTION_LIMITS = {
    'free': {
        'api_calls_per_day': 100,
        'storage_mb': 50,
        'events_per_month': 2,
        'templates': 3
    },
    'basic': {
        'api_calls_per_day': 1000,
        'storage_mb': 500,
        'events_per_month': 10,
        'templates': 20
    },
    'professional': {
        'api_calls_per_day': 10000,
        'storage_mb': 2000,
        'events_per_month': 50,
        'templates': 100
    },
    'enterprise': {
        'api_calls_per_day': 100000,
        'storage_mb': 10000,
        'events_per_month': 1000,
        'templates': 1000
    }
}

# Auth decorator
def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if token and token.startswith('Bearer '):
            token = token[7:]
        else:
            token = request.args.get('token') or session.get('auth_token')
        
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_payload = auth_manager.verify_jwt_token(token)
        if not user_payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Check subdomain access
        if not subdomain_middleware.check_subdomain_access(request, user_payload):
            return jsonify({'error': 'Access denied to this subdomain'}), 403
        
        request.user = user_payload
        return f(*args, **kwargs)
    
    return decorated_function

def require_subscription_limit(resource_type):
    """Decorator to check subscription limits"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user_id = request.user['user_id']
            subscription_tier = request.user['subscription_tier']
            
            # Get limit for this tier
            limits = SUBSCRIPTION_LIMITS.get(subscription_tier, SUBSCRIPTION_LIMITS['free'])
            limit = limits.get(resource_type, 0)
            
            # Check current usage
            if not auth_manager._check_subscription_limit(user_id, resource_type, limit):
                return jsonify({
                    'error': f'Subscription limit exceeded for {resource_type}',
                    'current_tier': subscription_tier,
                    'upgrade_url': '/upgrade'
                }), 402  # Payment Required
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

# Landing page routes
@app.route('/')
def landing_page():
    """Serve the landing page"""
    return render_template('landing/index.html')

# Authentication API routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field.replace("_", " ").title()} is required'
                }), 400
        
        # Create user
        user_id = auth_manager.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            company_name=data.get('company_name'),
            subscription_tier='free'
        )
        
        if not user_id:
            return jsonify({
                'success': False,
                'message': 'User already exists or registration failed'
            }), 400
        
        # Track registration
        auth_manager._track_resource_usage(user_id, 'registrations', 1)
        
        logger.info(f"New user registered: {data['email']} (ID: {user_id})")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user_id': user_id
        })
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Registration failed. Please try again.'
        }), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'message': 'Email and password are required'
            }), 400
        
        # Authenticate user
        user = auth_manager.authenticate_user(email, password)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401
        
        # Generate JWT token
        token = auth_manager.generate_jwt_token(
            user_id=user['id'],
            email=user['email'],
            access_level=user['access_level'],
            subscription_tier=user['subscription_tier']
        )
        
        # Store in session as backup
        session['auth_token'] = token
        session['user_id'] = user['id']
        
        # Track login
        auth_manager._track_resource_usage(user['id'], 'logins', 1)
        
        logger.info(f"User logged in: {email} (ID: {user['id']})")
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'first_name': user['first_name'],
                'last_name': user['last_name'],
                'company_name': user['company_name'],
                'subscription_tier': user['subscription_tier'],
                'subscription_active': user['subscription_active'],
                'is_trial_active': user['is_trial_active']
            }
        })
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Login failed. Please try again.'
        }), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth
def logout():
    """User logout endpoint"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# User profile and settings
@app.route('/api/user/profile', methods=['GET'])
@require_auth
def get_user_profile():
    """Get user profile information"""
    user_id = request.user['user_id']
    
    # Get detailed user info with subscription details
    with auth_manager.get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.*, us.payment_status, us.current_period_end,
                       COUNT(DISTINCT ut.id) as template_count,
                       COUNT(DISTINCT usc.id) as credential_count
                FROM users u
                LEFT JOIN user_subscriptions us ON u.id = us.user_id
                LEFT JOIN user_templates ut ON u.id = ut.user_id
                LEFT JOIN user_system_credentials usc ON u.id = usc.user_id AND usc.is_active = true
                WHERE u.id = %s
                GROUP BY u.id, us.payment_status, us.current_period_end
            """, (user_id,))
            
            user_data = cur.fetchone()
            
            if user_data:
                return jsonify({
                    'success': True,
                    'user': dict(user_data)
                })
            else:
                return jsonify({'success': False, 'message': 'User not found'}), 404

@app.route('/api/user/templates', methods=['GET'])
@require_auth
def get_user_templates():
    """Get user's display templates"""
    user_id = request.user['user_id']
    include_public = request.args.get('include_public', 'true').lower() == 'true'
    
    templates = auth_manager.get_user_templates(user_id, include_public)
    
    return jsonify({
        'success': True,
        'templates': templates
    })

@app.route('/api/user/templates', methods=['POST'])
@require_auth
@require_subscription_limit('templates')
def save_user_template():
    """Save user display template"""
    user_id = request.user['user_id']
    data = request.get_json()
    
    template_name = data.get('template_name')
    template_data = data.get('template_data')
    is_public = data.get('is_public', False)
    
    if not template_name or not template_data:
        return jsonify({
            'success': False,
            'message': 'Template name and data are required'
        }), 400
    
    success = auth_manager.store_user_template(
        user_id, template_name, template_data, is_public
    )
    
    if success:
        # Track template creation
        auth_manager._track_resource_usage(user_id, 'templates', 1)
        
        return jsonify({
            'success': True,
            'message': 'Template saved successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to save template'
        }), 500

@app.route('/api/user/credentials', methods=['POST'])
@require_auth
def save_system_credentials():
    """Save encrypted system credentials"""
    user_id = request.user['user_id']
    data = request.get_json()
    
    system_name = data.get('system_name')
    credentials = data.get('credentials')
    
    if not system_name or not credentials:
        return jsonify({
            'success': False,
            'message': 'System name and credentials are required'
        }), 400
    
    success = auth_manager.store_system_credentials(
        user_id, system_name, credentials
    )
    
    if success:
        return jsonify({
            'success': True,
            'message': 'Credentials saved successfully'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Failed to save credentials'
        }), 500

@app.route('/api/user/credentials/<system_name>', methods=['GET'])
@require_auth
def get_system_credentials(system_name):
    """Get decrypted system credentials"""
    user_id = request.user['user_id']
    
    credentials = auth_manager.get_system_credentials(user_id, system_name)
    
    if credentials:
        return jsonify({
            'success': True,
            'credentials': credentials
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Credentials not found'
        }), 404

# Subscription management
@app.route('/api/subscription/usage', methods=['GET'])
@require_auth
def get_subscription_usage():
    """Get current subscription usage"""
    user_id = request.user['user_id']
    subscription_tier = request.user['subscription_tier']
    
    # Get current usage
    with auth_manager.get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT resource_type, resource_count
                FROM usage_tracking
                WHERE user_id = %s AND tracking_period = CURRENT_DATE
            """, (user_id,))
            
            usage_data = dict(cur.fetchall())
    
    # Get limits
    limits = SUBSCRIPTION_LIMITS.get(subscription_tier, SUBSCRIPTION_LIMITS['free'])
    
    return jsonify({
        'success': True,
        'subscription_tier': subscription_tier,
        'usage': usage_data,
        'limits': limits
    })

@app.route('/api/subscription/upgrade', methods=['POST'])
@require_auth
def create_subscription():
    """Create Stripe subscription for user"""
    user_id = request.user['user_id']
    data = request.get_json()
    
    price_id = data.get('price_id')
    if not price_id:
        return jsonify({
            'success': False,
            'message': 'Price ID is required'
        }), 400
    
    try:
        # Create or get Stripe customer
        customer = stripe.Customer.create(
            email=request.user['email'],
            metadata={'user_id': user_id}
        )
        
        # Create subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{'price': price_id}],
            payment_behavior='default_incomplete',
            expand=['latest_invoice.payment_intent']
        )
        
        return jsonify({
            'success': True,
            'subscription_id': subscription.id,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret
        })
        
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Payment processing error'
        }), 500

# Stripe webhooks
@app.route('/api/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.environ.get('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'customer.subscription.updated':
        stripe_webhook_handler.handle_subscription_updated(event)
    elif event['type'] == 'customer.subscription.deleted':
        # Handle subscription cancellation
        pass
    elif event['type'] == 'invoice.payment_succeeded':
        # Handle successful payment
        pass
    
    return jsonify({'success': True})

# Admin routes
@app.route('/api/admin/users', methods=['GET'])
@require_auth
def admin_get_users():
    """Admin endpoint to get all users"""
    if request.user['access_level'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    with auth_manager.get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM user_subscription_summary ORDER BY created_at DESC")
            users = [dict(row) for row in cur.fetchall()]
    
    return jsonify({
        'success': True,
        'users': users
    })

@app.route('/api/admin/analytics', methods=['GET'])
@require_auth
def admin_analytics():
    """Admin analytics endpoint"""
    if request.user['access_level'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    with auth_manager.get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get revenue summary
            cur.execute("SELECT * FROM monthly_revenue_summary LIMIT 12")
            revenue_data = [dict(row) for row in cur.fetchall()]
            
            # Get user stats
            cur.execute("""
                SELECT 
                    subscription_tier,
                    COUNT(*) as user_count,
                    AVG(template_count) as avg_templates
                FROM user_subscription_summary
                GROUP BY subscription_tier
            """)
            user_stats = [dict(row) for row in cur.fetchall()]
    
    return jsonify({
        'success': True,
        'revenue_data': revenue_data,
        'user_stats': user_stats
    })

# Add these new API endpoints before the error handlers

@app.route('/api/chronotrack/credentials', methods=['GET'])
@require_auth
def get_chronotrack_credentials():
    """Get user's ChronoTrack credentials"""
    try:
        user_id = request.user['user_id']
        
        # Get all ChronoTrack credentials for user
        with auth_manager.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT id, system_name, created_at, updated_at
                    FROM user_system_credentials 
                    WHERE user_id = %s AND system_name LIKE 'chronotrack%'
                    ORDER BY updated_at DESC
                """, (user_id,))
                
                credentials = []
                for row in cur.fetchall():
                    try:
                        # Get decrypted data
                        cred_data = auth_manager.get_system_credentials(user_id, row['system_name'])
                        if cred_data:
                            credentials.append({
                                'id': row['id'],
                                'name': cred_data.get('name', row['system_name']),
                                'host': cred_data.get('host'),
                                'port': cred_data.get('port', 61611),
                                'user_id': cred_data.get('user_id'),
                                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                            })
                    except Exception as e:
                        logger.error(f"Error processing credential {row['system_name']}: {str(e)}")
                        continue
                
                return jsonify({
                    'success': True,
                    'credentials': credentials
                })
                
    except Exception as e:
        logger.error(f"Error getting ChronoTrack credentials: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve credentials'
        }), 500

@app.route('/api/chronotrack/credentials', methods=['POST'])
@require_auth
@require_subscription_limit('credentials')
def save_chronotrack_credentials():
    """Save ChronoTrack credentials for user"""
    try:
        user_id = request.user['user_id']
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'host', 'port', 'user_id', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field.replace("_", " ").title()} is required'
                }), 400
        
        # Create system name from credential name
        system_name = f"chronotrack_{data['name'].lower().replace(' ', '_')}"
        
        # Store credentials
        credential_data = {
            'name': data['name'],
            'host': data['host'],
            'port': int(data['port']),
            'user_id': data['user_id'],
            'password': data['password']
        }
        
        success = auth_manager.store_system_credentials(
            user_id, system_name, credential_data
        )
        
        if success:
            # Track credential usage
            auth_manager._track_resource_usage(user_id, 'credentials', 1)
            
            logger.info(f"ChronoTrack credentials saved for user {user_id}: {data['name']}")
            return jsonify({
                'success': True,
                'message': 'Credentials saved successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to save credentials'
            }), 500
            
    except Exception as e:
        logger.error(f"Error saving ChronoTrack credentials: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to save credentials'
        }), 500

@app.route('/api/chronotrack/test-connection', methods=['POST'])
@require_auth
@require_subscription_limit('api_calls_per_day')
def test_chronotrack_connection():
    """Test ChronoTrack server connection"""
    try:
        user_id = request.user['user_id']
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['host', 'port', 'user_id', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field.replace("_", " ").title()} is required'
                }), 400
        
        # Test connection (simplified implementation)
        connection_result = test_chronotrack_server_connection(
            data['host'],
            int(data['port']),
            data['user_id'],
            data['password']
        )
        
        if connection_result['success']:
            # Store successful connection test
            chronotrack_manager.store_connection_test(
                user_id, 
                data.get('credential_name', 'test_connection'),
                connection_result
            )
            
            # Track API usage
            auth_manager._track_resource_usage(user_id, 'api_calls_per_day', 1)
            
            return jsonify({
                'success': True,
                'event_info': connection_result.get('event_info', {}),
                'locations': connection_result.get('locations', []),
                'message': 'Connection successful'
            })
        else:
            return jsonify({
                'success': False,
                'message': connection_result.get('error', 'Connection failed')
            }), 400
            
    except Exception as e:
        logger.error(f"Error testing ChronoTrack connection: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Connection test failed'
        }), 500

@app.route('/api/chronotrack/start-preview', methods=['POST'])
@require_auth
@require_subscription_limit('api_calls_per_day')
def start_chronotrack_preview():
    """Start ChronoTrack data preview session"""
    try:
        user_id = request.user['user_id']
        data = request.get_json()
        
        credential_name = data.get('credential_name')
        if not credential_name:
            return jsonify({
                'success': False,
                'message': 'Credential name is required'
            }), 400
        
        # Get stored credentials
        system_name = f"chronotrack_{credential_name.lower().replace(' ', '_')}"
        credentials = auth_manager.get_system_credentials(user_id, system_name)
        
        if not credentials:
            return jsonify({
                'success': False,
                'message': 'Credentials not found'
            }), 404
        
        # Start preview session
        session_key = chronotrack_manager.start_preview_session(user_id, credential_name)
        
        # Start background preview thread
        start_chronotrack_preview_thread(session_key, credentials)
        
        # Track API usage
        auth_manager._track_resource_usage(user_id, 'api_calls_per_day', 1)
        
        return jsonify({
            'success': True,
            'session_key': session_key,
            'message': 'Preview session started'
        })
        
    except Exception as e:
        logger.error(f"Error starting ChronoTrack preview: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to start preview'
        }), 500

@app.route('/api/chronotrack/preview-stream')
@require_auth
def chronotrack_preview_stream():
    """Server-Sent Events stream for ChronoTrack preview data"""
    user_id = request.user['user_id']
    credential_name = request.args.get('credential')
    
    if not credential_name:
        return jsonify({'error': 'Credential name required'}), 400
    
    session_key = f"preview:{user_id}:{credential_name}"
    
    def generate():
        while session_key in chronotrack_manager.preview_queues:
            try:
                # Get data from queue with timeout
                preview_queue = chronotrack_manager.preview_queues[session_key]
                data = preview_queue.get(timeout=30)
                yield f"data: {json.dumps(data)}\n\n"
            except queue.Empty:
                # Send heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': time.time()})}\n\n"
            except Exception as e:
                logger.error(f"Error in preview stream: {str(e)}")
                break
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )

@app.route('/api/sessions/create', methods=['POST'])
@require_auth
@require_subscription_limit('events_per_month')
def create_timing_session():
    """Create a new timing session"""
    try:
        user_id = request.user['user_id']
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['session_name', 'event_name', 'controller_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'message': f'{field.replace("_", " ").title()} is required'
                }), 400
        
        # Create timing session in database
        with auth_manager.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO timing_sessions 
                    (user_id, session_name, event_name, controller_name, status, created_at)
                    VALUES (%s, %s, %s, %s, 'active', CURRENT_TIMESTAMP)
                    RETURNING id
                """, (
                    user_id,
                    data['session_name'],
                    data['event_name'],
                    data['controller_name']
                ))
                
                session_id = cur.fetchone()[0]
                conn.commit()
        
        # Track event usage
        auth_manager._track_resource_usage(user_id, 'events_per_month', 1)
        
        logger.info(f"Created timing session {session_id} for user {user_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Timing session created successfully'
        })
        
    except Exception as e:
        logger.error(f"Error creating timing session: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to create timing session'
        }), 500

@app.route('/api/sessions', methods=['GET'])
@require_auth
def get_user_sessions():
    """Get user's timing sessions"""
    try:
        user_id = request.user['user_id']
        
        with auth_manager.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT id, session_name, event_name, controller_name, status, 
                           created_at, updated_at
                    FROM timing_sessions 
                    WHERE user_id = %s 
                    ORDER BY created_at DESC
                    LIMIT 50
                """, (user_id,))
                
                sessions = []
                for row in cur.fetchall():
                    sessions.append({
                        'id': row['id'],
                        'session_name': row['session_name'],
                        'event_name': row['event_name'],
                        'controller_name': row['controller_name'],
                        'status': row['status'],
                        'created_at': row['created_at'].isoformat(),
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                    })
                
                return jsonify({
                    'success': True,
                    'sessions': sessions
                })
                
    except Exception as e:
        logger.error(f"Error getting user sessions: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to retrieve sessions'
        }), 500

# Helper functions for ChronoTrack functionality

def test_chronotrack_server_connection(host, port, user_id, password):
    """Test connection to ChronoTrack server"""
    try:
        # Simplified connection test (replace with actual ChronoTrack protocol)
        import socket
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            return {
                'success': True,
                'event_info': {
                    'event_id': '12345',
                    'event_name': 'Test Event',
                    'status': 'active'
                },
                'locations': [
                    {'id': 1, 'name': 'Start/Finish', 'active': True},
                    {'id': 2, 'name': 'Mile 1', 'active': False}
                ]
            }
        else:
            return {
                'success': False,
                'error': f'Cannot connect to {host}:{port}'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Connection test failed: {str(e)}'
        }

def start_chronotrack_preview_thread(session_key, credentials):
    """Start background thread for ChronoTrack data preview"""
    def preview_worker():
        try:
            # Simulate timing data for preview
            import random
            
            for i in range(50):  # Generate 50 sample data points
                if session_key not in chronotrack_manager.preview_queues:
                    break
                    
                sample_data = {
                    'type': 'timing_read',
                    'bib': random.randint(1, 999),
                    'time': f"{random.randint(0, 2):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}.{random.randint(0, 99):02d}",
                    'location': random.choice(['Start/Finish', 'Mile 1', 'Mile 2']),
                    'timestamp': time.time()
                }
                
                chronotrack_manager.add_preview_data(session_key, sample_data)
                time.sleep(random.uniform(1, 5))  # Random delay between reads
                
        except Exception as e:
            logger.error(f"Error in preview worker: {str(e)}")
    
    thread = threading.Thread(target=preview_worker, daemon=True)
    thread.start()

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# Health check
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    # Ensure required environment variables
    required_env_vars = ['DATABASE_URL', 'SECRET_KEY']
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        exit(1)
    
    # Run the app
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=debug) 