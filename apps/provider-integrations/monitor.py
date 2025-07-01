#!/usr/bin/env python3
"""
Project88Hub Provider Integration Monitoring Script
Checks system health and alerts on issues
"""

import os
import sys
import psycopg2
import psycopg2.extras
import json
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from typing import Dict, List, Optional

def get_db_connection():
    """Get database connection"""
    connection_string = (
        f"host={os.getenv('DB_HOST', 'localhost')} "
        f"port={os.getenv('DB_PORT', '5432')} "
        f"dbname={os.getenv('DB_NAME', 'project88_myappdb')} "
        f"user={os.getenv('DB_USER', 'project88_myappuser')} "
        f"password={os.getenv('DB_PASSWORD', '')}"
    )
    
    return psycopg2.connect(connection_string, cursor_factory=psycopg2.extras.RealDictCursor)

def check_sync_queue_health() -> Dict:
    """Check sync queue for stuck or failed jobs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check for stuck jobs (running for more than 1 hour)
    cursor.execute("""
        SELECT 
            COUNT(*) as stuck_jobs,
            MIN(started_at) as oldest_started
        FROM sync_queue 
        WHERE status = 'running' 
            AND started_at < NOW() - INTERVAL '1 hour'
    """)
    stuck_result = cursor.fetchone()
    
    # Check for failed jobs in last 24 hours
    cursor.execute("""
        SELECT 
            p.name as provider,
            COUNT(*) as failed_count
        FROM sync_queue sq
        JOIN providers p ON p.provider_id = sq.provider_id
        WHERE sq.status = 'failed' 
            AND sq.completed_at > NOW() - INTERVAL '24 hours'
        GROUP BY p.name
    """)
    failed_jobs = cursor.fetchall()
    
    # Check pending jobs count
    cursor.execute("""
        SELECT 
            p.name as provider,
            sq.operation_type,
            COUNT(*) as pending_count
        FROM sync_queue sq
        JOIN providers p ON p.provider_id = sq.provider_id
        WHERE sq.status = 'pending'
        GROUP BY p.name, sq.operation_type
    """)
    pending_jobs = cursor.fetchall()
    
    conn.close()
    
    return {
        'stuck_jobs': stuck_result['stuck_jobs'],
        'oldest_stuck': stuck_result['oldest_started'],
        'failed_jobs': [dict(row) for row in failed_jobs],
        'pending_jobs': [dict(row) for row in pending_jobs]
    }

def check_sync_history() -> Dict:
    """Check recent sync performance"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check sync success rate in last 24 hours
    cursor.execute("""
        SELECT 
            p.name as provider,
            COUNT(*) as total_syncs,
            COUNT(*) FILTER (WHERE status = 'success') as successful_syncs,
            AVG(duration_seconds) as avg_duration,
            MAX(sync_time) as last_sync
        FROM sync_history sh
        JOIN providers p ON p.provider_id = sh.provider_id
        WHERE sh.sync_time > NOW() - INTERVAL '24 hours'
        GROUP BY p.name
    """)
    sync_stats = cursor.fetchall()
    
    # Check for events that should be syncing but aren't
    cursor.execute("""
        SELECT 
            ue.timing_partner_id,
            ue.event_id,
            ue.event_name,
            ue.event_date,
            ue.source_provider,
            MAX(sh.sync_time) as last_sync
        FROM unified_events ue
        LEFT JOIN sync_history sh ON sh.event_id = ue.event_id 
            AND sh.timing_partner_id = ue.timing_partner_id
        WHERE ue.event_date > NOW() - INTERVAL '1 hour'  -- Events within sync window
            AND ue.event_date < NOW() + INTERVAL '7 days'
            AND (sh.sync_time IS NULL OR sh.sync_time < NOW() - INTERVAL '2 hours')
        GROUP BY ue.timing_partner_id, ue.event_id, ue.event_name, 
                 ue.event_date, ue.source_provider
        ORDER BY ue.event_date ASC
        LIMIT 10
    """)
    missing_syncs = cursor.fetchall()
    
    conn.close()
    
    return {
        'provider_stats': [dict(row) for row in sync_stats],
        'missing_syncs': [dict(row) for row in missing_syncs]
    }

def check_database_health() -> Dict:
    """Check database connectivity and basic health"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check table sizes
        cursor.execute("""
            SELECT 
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
            FROM pg_tables 
            WHERE tablename IN ('sync_queue', 'sync_history', 'runsignup_participants', 
                               'raceroster_participants', 'haku_participants')
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """)
        table_sizes = cursor.fetchall()
        
        # Check active connections
        cursor.execute("""
            SELECT 
                COUNT(*) as total_connections,
                COUNT(*) FILTER (WHERE state = 'active') as active_connections
            FROM pg_stat_activity 
            WHERE datname = current_database()
        """)
        connections = cursor.fetchone()
        
        conn.close()
        
        return {
            'connection_status': 'healthy',
            'table_sizes': [dict(row) for row in table_sizes],
            'connections': dict(connections)
        }
        
    except Exception as e:
        return {
            'connection_status': 'failed',
            'error': str(e)
        }

def check_upcoming_events() -> Dict:
    """Check for upcoming events that need attention"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Events starting within 4 hours (critical sync window)
    cursor.execute("""
        SELECT 
            ue.timing_partner_id,
            ue.event_id,
            ue.event_name,
            ue.event_date,
            ue.source_provider,
            COUNT(CASE WHEN p.timing_partner_id IS NOT NULL THEN 1 END) as participant_count,
            MAX(sh.sync_time) as last_sync
        FROM unified_events ue
        LEFT JOIN unified_participants p ON p.event_id = ue.event_id 
            AND p.timing_partner_id = ue.timing_partner_id
        LEFT JOIN sync_history sh ON sh.event_id = ue.event_id 
            AND sh.timing_partner_id = ue.timing_partner_id
            AND sh.operation_type = 'participants'
            AND sh.status = 'success'
        WHERE ue.event_date > NOW() 
            AND ue.event_date < NOW() + INTERVAL '4 hours'
        GROUP BY ue.timing_partner_id, ue.event_id, ue.event_name, 
                 ue.event_date, ue.source_provider
        ORDER BY ue.event_date ASC
    """)
    critical_events = cursor.fetchall()
    
    # Events starting within 24 hours (important sync window)
    cursor.execute("""
        SELECT 
            COUNT(*) as count,
            MIN(event_date) as next_event
        FROM unified_events
        WHERE event_date > NOW() 
            AND event_date < NOW() + INTERVAL '24 hours'
    """)
    upcoming_count = cursor.fetchone()
    
    conn.close()
    
    return {
        'critical_events': [dict(row) for row in critical_events],
        'upcoming_24h': dict(upcoming_count)
    }

def generate_health_report() -> Dict:
    """Generate comprehensive health report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',
        'issues': [],
        'warnings': []
    }
    
    try:
        # Check sync queue
        queue_health = check_sync_queue_health()
        report['sync_queue'] = queue_health
        
        if queue_health['stuck_jobs'] > 0:
            report['issues'].append(f"{queue_health['stuck_jobs']} stuck jobs found")
            report['status'] = 'unhealthy'
        
        if queue_health['failed_jobs']:
            total_failed = sum(job['failed_count'] for job in queue_health['failed_jobs'])
            report['warnings'].append(f"{total_failed} failed jobs in last 24 hours")
        
        # Check sync history
        sync_health = check_sync_history()
        report['sync_history'] = sync_health
        
        if sync_health['missing_syncs']:
            report['warnings'].append(f"{len(sync_health['missing_syncs'])} events missing recent syncs")
        
        # Check database
        db_health = check_database_health()
        report['database'] = db_health
        
        if db_health['connection_status'] != 'healthy':
            report['issues'].append(f"Database connection failed: {db_health.get('error', 'Unknown error')}")
            report['status'] = 'unhealthy'
        
        # Check upcoming events
        events_health = check_upcoming_events()
        report['upcoming_events'] = events_health
        
        if events_health['critical_events']:
            critical_count = len(events_health['critical_events'])
            report['warnings'].append(f"{critical_count} events starting within 4 hours")
        
        # Determine overall status
        if report['issues']:
            report['status'] = 'unhealthy'
        elif report['warnings']:
            report['status'] = 'warning'
            
    except Exception as e:
        report['status'] = 'error'
        report['issues'].append(f"Health check failed: {str(e)}")
    
    return report

def send_alert_email(report: Dict, email_config: Dict):
    """Send alert email if issues found"""
    if report['status'] == 'healthy':
        return
    
    subject = f"Project88Hub Provider Sync Alert - {report['status'].upper()}"
    
    # Build email content
    content = f"""
Provider Integration System Health Report
Generated: {report['timestamp']}
Status: {report['status'].upper()}

"""
    
    if report['issues']:
        content += "CRITICAL ISSUES:\n"
        for issue in report['issues']:
            content += f"- {issue}\n"
        content += "\n"
    
    if report['warnings']:
        content += "WARNINGS:\n"
        for warning in report['warnings']:
            content += f"- {warning}\n"
        content += "\n"
    
    # Add details
    if 'sync_queue' in report:
        sq = report['sync_queue']
        content += f"Sync Queue Status:\n"
        content += f"- Stuck jobs: {sq['stuck_jobs']}\n"
        content += f"- Failed jobs (24h): {len(sq['failed_jobs'])}\n"
        content += f"- Pending jobs: {len(sq['pending_jobs'])}\n\n"
    
    # Send email
    try:
        msg = MimeMultipart()
        msg['From'] = email_config['from_email']
        msg['To'] = email_config['to_email']
        msg['Subject'] = subject
        
        msg.attach(MimeText(content, 'plain'))
        
        server = smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port'])
        if email_config.get('use_tls', True):
            server.starttls()
        if email_config.get('username'):
            server.login(email_config['username'], email_config['password'])
        
        server.send_message(msg)
        server.quit()
        
        print(f"Alert email sent to {email_config['to_email']}")
        
    except Exception as e:
        print(f"Failed to send alert email: {e}")

def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Project88Hub Provider Integration Monitor')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--email-alerts', action='store_true', help='Send email alerts for issues')
    parser.add_argument('--quiet', action='store_true', help='Only output if issues found')
    
    args = parser.parse_args()
    
    try:
        report = generate_health_report()
        
        if args.json:
            print(json.dumps(report, indent=2, default=str))
        else:
            # Human readable output
            if not args.quiet or report['status'] != 'healthy':
                print(f"Provider Integration Health: {report['status'].upper()}")
                print(f"Timestamp: {report['timestamp']}")
                
                if report['issues']:
                    print("\nCRITICAL ISSUES:")
                    for issue in report['issues']:
                        print(f"  ❌ {issue}")
                
                if report['warnings']:
                    print("\nWARNINGS:")
                    for warning in report['warnings']:
                        print(f"  ⚠️  {warning}")
                
                if report['status'] == 'healthy':
                    print("\n✅ All systems healthy")
        
        # Send email alerts if configured
        if args.email_alerts:
            email_config = {
                'smtp_server': os.getenv('SMTP_SERVER', 'localhost'),
                'smtp_port': int(os.getenv('SMTP_PORT', '587')),
                'from_email': os.getenv('ALERT_FROM_EMAIL', 'alerts@project88.com'),
                'to_email': os.getenv('ALERT_TO_EMAIL', 'admin@project88.com'),
                'username': os.getenv('SMTP_USERNAME'),
                'password': os.getenv('SMTP_PASSWORD'),
                'use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
            }
            
            send_alert_email(report, email_config)
        
        # Exit with appropriate code
        if report['status'] == 'unhealthy':
            sys.exit(2)
        elif report['status'] == 'warning':
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"Monitoring failed: {e}")
        sys.exit(3)

if __name__ == "__main__":
    main() 