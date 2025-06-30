"""
Enhanced Authentication System for Project88hub
Supports subscription management, subdomain access control, and user-specific storage
"""

import hashlib
import secrets
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from cryptography.fernet import Fernet
import psycopg2
import psycopg2.extras
import os
import json
from enum import Enum

class SubscriptionTier(Enum):
    FREE = "free"
    BASIC = "basic"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class PaymentStatus(Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"

class Project88AuthManager:
    def __init__(self, database_url: str, secret_key: str):
        self.database_url = database_url
        self.secret_key = secret_key
        self.encryption_key = Fernet.generate_key()  # In production, load from secure storage
        self.cipher = Fernet(self.encryption_key)
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, hash: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hash.encode('utf-8'))
    
    def encrypt_credential(self, credential: str) -> str:
        """Encrypt sensitive credential"""
        return self.cipher.encrypt(credential.encode()).decode()
    
    def decrypt_credential(self, encrypted_credential: str) -> str:
        """Decrypt sensitive credential"""
        return self.cipher.decrypt(encrypted_credential.encode()).decode()
    
    def generate_jwt_token(self, user_id: int, email: str, access_level: str, 
                          subscription_tier: str = "free") -> str:
        """Generate JWT token for user session"""
        payload = {
            'user_id': user_id,
            'email': email,
            'access_level': access_level,
            'subscription_tier': subscription_tier,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Optional[Dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def create_user(self, email: str, password: str, first_name: str, 
                   last_name: str, company_name: str = None,
                   subscription_tier: str = "free") -> Optional[int]:
        """Create new user account with subscription management"""
        password_hash = self.hash_password(password)
        
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # Create user
                    cur.execute("""
                        INSERT INTO users (email, password_hash, first_name, last_name, 
                                         company_name, subscription_tier, trial_ends_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (email, password_hash, first_name, last_name, company_name,
                         subscription_tier, datetime.utcnow() + timedelta(days=14)))
                    
                    user_id = cur.fetchone()[0]
                    
                    # Create default subdomain access
                    default_domains = self._get_default_domains_for_tier(subscription_tier)
                    for domain in default_domains:
                        cur.execute("""
                            INSERT INTO user_subdomain_access (user_id, subdomain, access_granted_at)
                            VALUES (%s, %s, CURRENT_TIMESTAMP)
                        """, (user_id, domain))
                    
                    conn.commit()
                    return user_id
                except psycopg2.IntegrityError:
                    return None  # User already exists
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user info with subscription details"""
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute("""
                    SELECT u.*, us.payment_status, us.current_period_end, 
                           CASE WHEN u.trial_ends_at > CURRENT_TIMESTAMP THEN true ELSE false END as is_trial_active
                    FROM users u
                    LEFT JOIN user_subscriptions us ON u.id = us.user_id AND us.status = 'active'
                    WHERE u.email = %s AND u.active = true
                """, (email,))
                
                user = cur.fetchone()
                if not user:
                    return None
                
                if not self.verify_password(password, user['password_hash']):
                    return None
                
                # Check subscription status
                subscription_active = self._check_subscription_active(user)
                
                # Update last login
                cur.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE id = %s
                """, (user['id'],))
                conn.commit()
                
                return {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'company_name': user['company_name'],
                    'subscription_tier': user['subscription_tier'],
                    'subscription_active': subscription_active,
                    'is_trial_active': user['is_trial_active'],
                    'access_level': user['access_level']
                }
    
    def check_subdomain_access(self, user_id: int, subdomain: str) -> bool:
        """Check if user has access to specific subdomain"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                # Check direct subdomain access
                cur.execute("""
                    SELECT 1 FROM user_subdomain_access 
                    WHERE user_id = %s AND subdomain = %s
                """, (user_id, subdomain))
                
                if cur.fetchone():
                    return True
                
                # Check subscription tier access
                cur.execute("""
                    SELECT subscription_tier FROM users WHERE id = %s
                """, (user_id,))
                
                result = cur.fetchone()
                if result:
                    tier = result[0]
                    return self._check_tier_subdomain_access(tier, subdomain)
                
                return False
    
    def store_user_template(self, user_id: int, template_name: str, 
                           template_data: Dict, is_public: bool = False) -> bool:
        """Store user-specific display template"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        INSERT INTO user_templates (user_id, template_name, template_data, 
                                                   is_public, created_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, template_name) 
                        DO UPDATE SET 
                            template_data = EXCLUDED.template_data,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, template_name, json.dumps(template_data), is_public))
                    
                    conn.commit()
                    return True
                except Exception:
                    return False
    
    def get_user_templates(self, user_id: int, include_public: bool = True) -> List[Dict]:
        """Get user's templates and optionally public templates"""
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                if include_public:
                    cur.execute("""
                        SELECT ut.*, u.first_name, u.last_name 
                        FROM user_templates ut
                        JOIN users u ON ut.user_id = u.id
                        WHERE ut.user_id = %s OR ut.is_public = true
                        ORDER BY ut.user_id = %s DESC, ut.updated_at DESC
                    """, (user_id, user_id))
                else:
                    cur.execute("""
                        SELECT ut.*, u.first_name, u.last_name 
                        FROM user_templates ut
                        JOIN users u ON ut.user_id = u.id
                        WHERE ut.user_id = %s
                        ORDER BY ut.updated_at DESC
                    """, (user_id,))
                
                templates = []
                for row in cur.fetchall():
                    template = dict(row)
                    template['template_data'] = json.loads(template['template_data'])
                    templates.append(template)
                
                return templates
    
    def store_system_credentials(self, user_id: int, system_name: str, 
                               credential_data: Dict) -> bool:
        """Store encrypted credentials for various systems (ChronoTrack, etc.)"""
        encrypted_data = self.encrypt_credential(json.dumps(credential_data))
        
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        INSERT INTO user_system_credentials 
                        (user_id, system_name, encrypted_credentials, created_at)
                        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, system_name) 
                        DO UPDATE SET 
                            encrypted_credentials = EXCLUDED.encrypted_credentials,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, system_name, encrypted_data))
                    
                    conn.commit()
                    return True
                except Exception:
                    return False
    
    def get_system_credentials(self, user_id: int, system_name: str) -> Optional[Dict]:
        """Get decrypted credentials for a system"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT encrypted_credentials FROM user_system_credentials 
                    WHERE user_id = %s AND system_name = %s
                """, (user_id, system_name))
                
                result = cur.fetchone()
                if result:
                    decrypted_data = self.decrypt_credential(result[0])
                    return json.loads(decrypted_data)
                return None
    
    def update_subscription(self, user_id: int, subscription_tier: str, 
                          payment_status: str, stripe_subscription_id: str = None) -> bool:
        """Update user subscription (for Stripe integration)"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # Update user tier
                    cur.execute("""
                        UPDATE users SET subscription_tier = %s WHERE id = %s
                    """, (subscription_tier, user_id))
                    
                    # Update or create subscription record
                    cur.execute("""
                        INSERT INTO user_subscriptions 
                        (user_id, stripe_subscription_id, payment_status, current_period_end, status)
                        VALUES (%s, %s, %s, %s, 'active')
                        ON CONFLICT (user_id) 
                        DO UPDATE SET 
                            stripe_subscription_id = EXCLUDED.stripe_subscription_id,
                            payment_status = EXCLUDED.payment_status,
                            current_period_end = EXCLUDED.current_period_end,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, stripe_subscription_id, payment_status, 
                         datetime.utcnow() + timedelta(days=30)))
                    
                    # Update subdomain access based on new tier
                    self._update_subdomain_access_for_tier(user_id, subscription_tier)
                    
                    conn.commit()
                    return True
                except Exception:
                    return False
    
    def _get_default_domains_for_tier(self, tier: str) -> List[str]:
        """Get default subdomain access for subscription tier"""
        tier_domains = {
            "free": ["display.project88hub.com"],
            "basic": ["display.project88hub.com", "analytics.project88hub.com"],
            "professional": ["display.project88hub.com", "analytics.project88hub.com", 
                           "ai.project88hub.com"],
            "enterprise": ["*"]  # All subdomains
        }
        return tier_domains.get(tier, ["display.project88hub.com"])
    
    def _check_tier_subdomain_access(self, tier: str, subdomain: str) -> bool:
        """Check if subscription tier allows access to subdomain"""
        allowed_domains = self._get_default_domains_for_tier(tier)
        return "*" in allowed_domains or subdomain in allowed_domains
    
    def _check_subscription_active(self, user_data: Dict) -> bool:
        """Check if user's subscription is active"""
        # Check trial period
        if user_data.get('is_trial_active'):
            return True
        
        # Check paid subscription
        payment_status = user_data.get('payment_status')
        if payment_status in ['active', 'trialing']:
            return True
        
        # Free tier is always "active"
        if user_data.get('subscription_tier') == 'free':
            return True
        
        return False
    
    def _update_subdomain_access_for_tier(self, user_id: int, tier: str):
        """Update user's subdomain access based on subscription tier"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                # Remove existing access
                cur.execute("DELETE FROM user_subdomain_access WHERE user_id = %s", (user_id,))
                
                # Add new access based on tier
                allowed_domains = self._get_default_domains_for_tier(tier)
                for domain in allowed_domains:
                    if domain != "*":  # Don't insert wildcard
                        cur.execute("""
                            INSERT INTO user_subdomain_access (user_id, subdomain, access_granted_at)
                            VALUES (%s, %s, CURRENT_TIMESTAMP)
                        """, (user_id, domain))

    def _track_resource_usage(self, user_id: int, resource_type: str, amount: int = 1):
        """Track user resource usage for subscription limits"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # Determine the time period based on resource type
                    if resource_type == 'api_calls_per_day':
                        period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                        period_end = period_start + timedelta(days=1)
                    elif resource_type == 'events_per_month':
                        period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                        next_month = period_start.month + 1 if period_start.month < 12 else 1
                        next_year = period_start.year + (1 if next_month == 1 else 0)
                        period_end = period_start.replace(month=next_month, year=next_year)
                    else:
                        # Default to daily tracking
                        period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                        period_end = period_start + timedelta(days=1)
                    
                    # Insert or update usage tracking
                    cur.execute("""
                        INSERT INTO usage_tracking 
                        (user_id, resource_type, usage_count, period_start, period_end, created_at)
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, resource_type, period_start)
                        DO UPDATE SET 
                            usage_count = usage_tracking.usage_count + EXCLUDED.usage_count,
                            updated_at = CURRENT_TIMESTAMP
                    """, (user_id, resource_type, amount, period_start, period_end))
                    
                    conn.commit()
                    return True
                except Exception as e:
                    print(f"Error tracking usage: {e}")
                    return False

    def _check_subscription_limit(self, user_id: int, resource_type: str, limit: int) -> bool:
        """Check if user is within subscription limits for a resource"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # Determine the time period based on resource type
                    if resource_type == 'api_calls_per_day':
                        period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                    elif resource_type == 'events_per_month':
                        period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    else:
                        # Default to daily tracking
                        period_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    # Get current usage
                    cur.execute("""
                        SELECT COALESCE(usage_count, 0) as current_usage
                        FROM usage_tracking 
                        WHERE user_id = %s AND resource_type = %s AND period_start = %s
                    """, (user_id, resource_type, period_start))
                    
                    result = cur.fetchone()
                    current_usage = result[0] if result else 0
                    
                    # Check if under limit
                    return current_usage < limit
                    
                except Exception as e:
                    print(f"Error checking subscription limit: {e}")
                    return True  # Allow on error to avoid blocking users

    def get_user_usage_stats(self, user_id: int) -> Dict:
        """Get user's current usage statistics"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get current day usage
                today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                
                # Get current month usage
                month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
                stats = {}
                
                # API calls today
                cur.execute("""
                    SELECT COALESCE(usage_count, 0) 
                    FROM usage_tracking 
                    WHERE user_id = %s AND resource_type = 'api_calls_per_day' AND period_start = %s
                """, (user_id, today))
                result = cur.fetchone()
                stats['api_calls_today'] = result[0] if result else 0
                
                # Events this month
                cur.execute("""
                    SELECT COALESCE(usage_count, 0) 
                    FROM usage_tracking 
                    WHERE user_id = %s AND resource_type = 'events_per_month' AND period_start = %s
                """, (user_id, month_start))
                result = cur.fetchone()
                stats['events_this_month'] = result[0] if result else 0
                
                # Template count
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM user_templates 
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                stats['template_count'] = result[0] if result else 0
                
                # Credential count
                cur.execute("""
                    SELECT COUNT(*) 
                    FROM user_system_credentials 
                    WHERE user_id = %s
                """, (user_id,))
                result = cur.fetchone()
                stats['credential_count'] = result[0] if result else 0
                
                return stats

# Middleware for subdomain access control
class SubdomainAccessMiddleware:
    def __init__(self, auth_manager: Project88AuthManager):
        self.auth_manager = auth_manager
    
    def check_subdomain_access(self, request, user_payload: Dict) -> bool:
        """Check if user has access to current subdomain"""
        host = request.headers.get('Host', '')
        
        # Extract subdomain
        if '.' in host:
            subdomain = host.split('.')[0]
            subdomain_full = host
        else:
            return False  # Invalid host
        
        # Check access
        return self.auth_manager.check_subdomain_access(
            user_payload['user_id'], 
            subdomain_full
        )

# Stripe webhook handler for subscription management
class StripeWebhookHandler:
    def __init__(self, auth_manager: Project88AuthManager):
        self.auth_manager = auth_manager
    
    def handle_subscription_updated(self, stripe_event: Dict):
        """Handle Stripe subscription update webhook"""
        subscription = stripe_event['data']['object']
        customer_id = subscription['customer']
        
        # Find user by Stripe customer ID
        with self.auth_manager.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT user_id FROM user_subscriptions 
                    WHERE stripe_customer_id = %s
                """, (customer_id,))
                
                result = cur.fetchone()
                if result:
                    user_id = result[0]
                    
                    # Update subscription
                    tier = self._map_stripe_price_to_tier(subscription['items']['data'][0]['price']['id'])
                    self.auth_manager.update_subscription(
                        user_id, tier, subscription['status'], subscription['id']
                    )
    
    def _map_stripe_price_to_tier(self, price_id: str) -> str:
        """Map Stripe price ID to subscription tier"""
        price_mapping = {
            'price_basic_monthly': 'basic',
            'price_professional_monthly': 'professional',
            'price_enterprise_monthly': 'enterprise'
        }
        return price_mapping.get(price_id, 'free') 