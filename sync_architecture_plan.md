# 🔄 Sync Architecture & Implementation Plan

## 📋 **Current State Analysis**

Based on your schema, you already have:
- ✅ **Working sync infrastructure** (`sync_queue`, `sync_history`)
- ✅ **Multi-tenant provider credentials** (`partner_provider_credentials`)
- ✅ **RunSignUp integration** (complete with events, participants, counts)
- ✅ **ChronoTrack integration** (events, races, participants, results)
- ✅ **Haku foundation** (`timing_partner_haku_orgs`)

## 🎯 **New Integrations Needed**

1. **Race Roster** - Registration provider (events + participants)
2. **Complete Haku** - Registration provider (events + participants)  
3. **Copernico** - Scoring provider (events + participants + **results**)

## 🔄 **Sync Flow Architecture**

### **Data Flow Overview**
```
Registration Providers → Your Database → Scoring Providers
(RunSignUp, Race Roster, Haku) → (Unified Views) → (Copernico, ChronoTrack)

Results Flow:
Scoring Providers → Your Database → Registration Providers (when requested)
(Copernico, ChronoTrack) → (Results Tables) → (RunSignUp, etc.)
```

### **Sync Types & Priorities**

| Sync Type | Direction | Frequency | Trigger | Priority |
|-----------|-----------|-----------|---------|----------|
| **Event Discovery** | Registration → Database | Daily | Scheduled | High |
| **Participant Sync** | Registration → Scoring | 4 hours | Scheduled + Manual | High |
| **Results Retrieval** | Scoring → Database | 30 minutes | Scheduled | Medium |
| **Results Publication** | Database → Registration | On-demand | Manual | Low |

---

## 🕒 **Sync Scheduling Strategy**

### **Option 1: Enhanced Current System (Recommended)**
Build on your existing `sync_queue` and `sync_history` tables.

```python
# Enhanced sync job scheduler
class SyncScheduler:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        
    def schedule_provider_syncs(self):
        """Schedule syncs for all active provider connections"""
        
        # Get all timing partners with active provider connections
        timing_partners = self.get_active_timing_partners()
        
        for partner in timing_partners:
            # Schedule event discovery (daily)
            self.schedule_sync(
                timing_partner_id=partner['timing_partner_id'],
                sync_type='event_discovery',
                provider_name='runsignup',
                frequency='daily',
                next_run=self.get_next_daily_run()
            )
            
            # Schedule participant sync (every 4 hours)
            self.schedule_sync(
                timing_partner_id=partner['timing_partner_id'],
                sync_type='participant_sync',
                provider_name='runsignup',
                frequency='4hours',
                next_run=self.get_next_4hour_run()
            )
```

### **Option 2: External Cron Jobs**
```bash
# /etc/crontab entries
# Event discovery - daily at 2 AM
0 2 * * * project88 /usr/bin/python3 /path/to/sync_events.py

# Participant sync - every 4 hours
0 */4 * * * project88 /usr/bin/python3 /path/to/sync_participants.py

# Results retrieval - every 30 minutes
*/30 * * * * project88 /usr/bin/python3 /path/to/sync_results.py
```

### **Option 3: Systemd Timers (Most Robust)**
```ini
# /etc/systemd/system/project88-participant-sync.timer
[Unit]
Description=Run Project88 participant sync every 4 hours
Requires=project88-participant-sync.service

[Timer]
OnCalendar=*-*-* 00,04,08,12,16,20:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

---

## 🔧 **Enhanced Sync Queue Implementation**

### **Extend Current sync_queue Table**
Your enhanced schema already adds these columns:
```sql
ALTER TABLE sync_queue ADD COLUMN provider_name TEXT;
ALTER TABLE sync_queue ADD COLUMN operation_type TEXT; -- 'events', 'participants', 'results'
ALTER TABLE sync_queue ADD COLUMN sync_direction TEXT; -- 'pull', 'push'
ALTER TABLE sync_queue ADD COLUMN priority INTEGER DEFAULT 5;
ALTER TABLE sync_queue ADD COLUMN scheduled_time TEXT;
```

### **Sync Queue Management**
```python
class SyncQueueManager:
    def add_sync_job(self, timing_partner_id, provider_name, operation_type, 
                     sync_direction='pull', priority=5, scheduled_time=None):
        """Add a sync job to the queue"""
        
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT INTO sync_queue 
            (event_id, provider_name, operation_type, sync_direction, 
             priority, scheduled_time, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (timing_partner_id, provider_name, operation_type, 
              sync_direction, priority, scheduled_time or datetime.now()))
        
    def get_pending_jobs(self, limit=10):
        """Get pending sync jobs ordered by priority and scheduled time"""
        
        cursor = self.db.cursor()
        return cursor.execute("""
            SELECT * FROM sync_queue 
            WHERE status = 'pending' 
            AND (scheduled_time IS NULL OR scheduled_time <= datetime('now'))
            ORDER BY priority ASC, scheduled_time ASC
            LIMIT ?
        """, (limit,)).fetchall()
        
    def process_sync_job(self, job):
        """Process a single sync job"""
        
        # Update status to 'running'
        self.update_job_status(job['sync_queue_id'], 'running')
        
        try:
            # Execute sync based on job type
            if job['operation_type'] == 'events':
                result = self.sync_events(job)
            elif job['operation_type'] == 'participants':
                result = self.sync_participants(job)
            elif job['operation_type'] == 'results':
                result = self.sync_results(job)
                
            # Record success in sync_history
            self.record_sync_history(job, 'success', result)
            self.update_job_status(job['sync_queue_id'], 'completed')
            
        except Exception as e:
            # Record failure
            self.record_sync_history(job, 'failed', str(e))
            self.update_job_status(job['sync_queue_id'], 'failed')
```

---

## 🔄 **Provider-Specific Sync Workflows**

### **Race Roster Integration**
```python
class RaceRosterSync:
    def sync_events(self, timing_partner_id):
        """Sync events from Race Roster"""
        
        # Get credentials
        credentials = self.get_credentials(timing_partner_id, 'Race Roster')
        
        # Fetch events from Race Roster API
        events = self.raceroster_api.get_events(credentials)
        
        # Insert/update in raceroster_events table
        for event in events:
            self.db.execute("""
                INSERT OR REPLACE INTO raceroster_events 
                (event_id, name, start_date, city, state, timing_partner_id, fetched_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event.id, event.name, event.start_date, event.city, 
                  event.state, timing_partner_id, datetime.now()))
                  
    def sync_participants(self, timing_partner_id, event_id):
        """Sync participants for a specific event"""
        
        credentials = self.get_credentials(timing_partner_id, 'Race Roster')
        participants = self.raceroster_api.get_participants(event_id, credentials)
        
        for participant in participants:
            self.db.execute("""
                INSERT OR REPLACE INTO raceroster_participants 
                (event_id, first_name, last_name, email, bib_number, 
                 timing_partner_id, fetched_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (event_id, participant.first_name, participant.last_name,
                  participant.email, participant.bib_number, 
                  timing_partner_id, datetime.now()))
```

### **Copernico Results Sync**
```python
class CopernicoSync:
    def push_participants_to_copernico(self, timing_partner_id, event_id):
        """Push participants from registration providers to Copernico"""
        
        # Get unified participants for this event
        participants = self.db.execute("""
            SELECT * FROM unified_participants 
            WHERE timing_partner_id = ? AND event_id = ?
        """, (timing_partner_id, event_id)).fetchall()
        
        # Transform to Copernico format
        copernico_participants = []
        for p in participants:
            copernico_participants.append({
                'firstName': p['first_name'],
                'lastName': p['last_name'],
                'bibNumber': p['bib_number'],
                'dateOfBirth': p.get('date_of_birth'),
                'gender': p['gender']
            })
            
        # Push to Copernico via API
        credentials = self.get_credentials(timing_partner_id, 'Copernico')
        result = self.copernico_api.create_participants(
            event_id, copernico_participants, credentials
        )
        
        return result
        
    def pull_results_from_copernico(self, timing_partner_id, event_id):
        """Pull results from Copernico"""
        
        credentials = self.get_credentials(timing_partner_id, 'Copernico')
        results = self.copernico_api.get_results(event_id, credentials)
        
        # Store in copernico_results table
        for result in results:
            self.db.execute("""
                INSERT OR REPLACE INTO copernico_results 
                (event_id, bib_number, first_name, last_name, 
                 finish_time, overall_position, timing_partner_id, fetched_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_id, result.bib_number, result.first_name,
                  result.last_name, result.finish_time, result.overall_position,
                  timing_partner_id, datetime.now()))
```

---

## 📊 **Manual Sync API Endpoints**

### **REST API for Manual Triggers**
```python
from flask import Blueprint, request, jsonify

sync_api = Blueprint('sync_api', __name__)

@sync_api.route('/api/sync/manual', methods=['POST'])
def trigger_manual_sync():
    """Trigger manual sync for specific timing partner/provider"""
    
    data = request.get_json()
    timing_partner_id = data.get('timing_partner_id')
    provider_name = data.get('provider_name')
    operation_type = data.get('operation_type', 'participants')
    
    # Add high-priority job to sync queue
    sync_queue.add_sync_job(
        timing_partner_id=timing_partner_id,
        provider_name=provider_name,
        operation_type=operation_type,
        priority=1,  # High priority for manual syncs
        scheduled_time=datetime.now()
    )
    
    return jsonify({
        'success': True,
        'message': f'Manual {operation_type} sync queued for {provider_name}'
    })

@sync_api.route('/api/sync/status/<int:timing_partner_id>')
def get_sync_status(timing_partner_id):
    """Get sync status for a timing partner"""
    
    recent_syncs = db.execute("""
        SELECT sh.*, sq.provider_name, sq.operation_type
        FROM sync_history sh
        LEFT JOIN sync_queue sq ON sh.event_id = sq.event_id
        WHERE sh.event_id = ?
        ORDER BY sh.sync_time DESC
        LIMIT 20
    """, (timing_partner_id,)).fetchall()
    
    return jsonify({
        'timing_partner_id': timing_partner_id,
        'recent_syncs': [dict(sync) for sync in recent_syncs],
        'last_successful_sync': get_last_successful_sync(timing_partner_id),
        'pending_jobs': get_pending_jobs_count(timing_partner_id)
    })
```

---

## 🚨 **Error Handling & Retry Logic**

### **Sync Failure Management**
```python
class SyncErrorHandler:
    def handle_sync_failure(self, job, error, retry_count=0):
        """Handle sync failures with exponential backoff"""
        
        max_retries = 3
        
        if retry_count < max_retries:
            # Calculate exponential backoff delay
            delay_minutes = 2 ** retry_count  # 2, 4, 8 minutes
            retry_time = datetime.now() + timedelta(minutes=delay_minutes)
            
            # Reschedule job
            self.sync_queue.add_sync_job(
                timing_partner_id=job['event_id'],
                provider_name=job['provider_name'],
                operation_type=job['operation_type'],
                priority=job['priority'] + 1,  # Lower priority for retries
                scheduled_time=retry_time
            )
            
        else:
            # Max retries exceeded - send alert
            self.send_sync_failure_alert(job, error)
            
    def send_sync_failure_alert(self, job, error):
        """Send alert when sync fails permanently"""
        
        # Log to sync_history with detailed error
        self.db.execute("""
            INSERT INTO sync_history 
            (event_id, sync_time, status, reason, error_details)
            VALUES (?, ?, 'failed_permanent', ?, ?)
        """, (job['event_id'], datetime.now(), 
              f"Max retries exceeded for {job['provider_name']}", str(error)))
        
        # Send email/slack notification (implement based on your setup)
        self.notification_service.send_alert(
            f"Sync Failure: {job['provider_name']} for timing partner {job['event_id']}",
            error
        )
```

---

## 🎯 **Recommended Implementation Steps**

### **Week 1: Database + Basic Sync**
1. **Execute enhanced database script** on staging environment
2. **Test unified views** with existing RunSignUp data
3. **Build basic sync worker** that processes your existing sync_queue

### **Week 2: Race Roster Integration**
1. **Build Race Roster API adapter**
2. **Implement events and participants sync**
3. **Test end-to-end with one timing partner**

### **Week 3: Copernico Integration**
1. **Build Copernico API adapter**
2. **Implement participant push and results pull**
3. **Test bidirectional sync workflow**

### **Week 4: Complete Haku + Manual Triggers**
1. **Complete Haku events/participants tables**
2. **Build manual sync API endpoints**
3. **Create sync monitoring dashboard**

### **Week 5: Error Handling + Scheduling**
1. **Implement retry logic and error handling**
2. **Set up scheduled sync jobs (cron/systemd)**
3. **Add sync failure alerting**

### **Week 6: Production Deployment**
1. **Deploy to production with 1-2 pilot timing partners**
2. **Monitor sync performance and reliability**
3. **Gradual rollout to all timing partners**

---

## 🤔 **Key Decision Points**

1. **Sync Triggering**: Do you prefer cron jobs, systemd timers, or a Python scheduler service?

2. **Error Alerting**: How do you want to be notified of sync failures? Email, Slack, dashboard?

3. **Results Publishing**: Should results automatically publish to registration providers, or require manual approval?

4. **Rate Limiting**: What are the API rate limits for each provider, and how should we handle them?

5. **Data Retention**: How long should we keep sync history and queue entries?

What's your preference for sync triggering and error handling? And should we start with Race Roster or Copernico as the first new integration? 