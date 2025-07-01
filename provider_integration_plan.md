# 🔄 Provider Integration Implementation Plan

## 📋 **Overview**

Complete 6-week implementation plan for integrating **Race Roster**, **Haku**, **Copernico**, and **CTLive** with the existing Project88Hub platform.

**Architecture**: Unidirectional sync (registration → scoring) with scheduled + manual triggers  
**Data Strategy**: Full normalization for unified queries across all providers  
**Isolation**: Granular timing partner data segmentation with admin override  

---

## 🏗️ **Phase 1: Database Foundation (Week 1)**

### **1.1 Database Migration**
**Timeline**: 2 days  
**File**: `database_migration_v1.sql`

```bash
# Execute migration on production
psql -h localhost -U project88_myappuser -d project88_myappdb -f database_migration_v1.sql

# Verify migration
psql -h localhost -U project88_myappuser -d project88_myappdb -c "
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE 'normalized_%' OR table_name LIKE 'provider_%';
"
```

### **1.2 Data Migration from Existing Systems**
**Timeline**: 3 days

Migrate existing RunSignUp data to normalized tables:

```sql
-- Migrate all existing RunSignUp data
SELECT migrate_runsignup_data(tp.id) as migrated_events
FROM timing_partners tp;

-- Verify migration
SELECT 
    tp.name as timing_partner,
    COUNT(ne.id) as normalized_events,
    COUNT(np.id) as normalized_participants
FROM timing_partners tp
LEFT JOIN normalized_events ne ON tp.id = ne.timing_partner_id
LEFT JOIN normalized_participants np ON tp.id = np.timing_partner_id
GROUP BY tp.id, tp.name;
```

---

## 🔌 **Phase 2: Provider Adapter Architecture (Week 2)**

### **2.1 Base Provider Adapter Class**

```python
# providers/base_adapter.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging

@dataclass
class ProviderEvent:
    provider_event_id: str
    event_name: str
    event_date: datetime
    location_city: str
    location_state: str
    race_distance: float
    max_participants: int
    raw_data: Dict

@dataclass
class ProviderParticipant:
    provider_participant_id: str
    bib_number: str
    first_name: str
    last_name: str
    email: str
    gender: str
    age: int
    city: str
    state: str
    raw_data: Dict

@dataclass
class ProviderResult:
    provider_result_id: str
    bib_number: str
    overall_place: int
    finish_time: datetime
    total_time_seconds: int
    raw_data: Dict

@dataclass
class SyncResult:
    success: bool
    processed_count: int
    error_count: int
    errors: List[str]
    sync_id: str

class BaseProviderAdapter(ABC):
    def __init__(self, credentials: Dict[str, str]):
        self.credentials = credentials
        self.logger = logging.getLogger(f"provider.{self.__class__.__name__}")
        
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with provider API"""
        pass
        
    @abstractmethod
    def get_events(self, filters: Optional[Dict] = None) -> List[ProviderEvent]:
        """Get events from provider"""
        pass
        
    @abstractmethod
    def get_participants(self, event_id: str) -> List[ProviderParticipant]:
        """Get participants for an event"""
        pass
        
    @abstractmethod
    def create_event(self, event_data: ProviderEvent) -> str:
        """Create event in provider system"""
        pass
        
    @abstractmethod
    def sync_participants(self, event_id: str, participants: List[ProviderParticipant]) -> SyncResult:
        """Sync participants to provider system"""
        pass
        
    @abstractmethod
    def get_results(self, event_id: str) -> List[ProviderResult]:
        """Get results from provider system"""
        pass
        
    @abstractmethod
    def post_results(self, event_id: str, results: List[ProviderResult]) -> SyncResult:
        """Post results to provider system"""
        pass
        
    def normalize_field_names(self, data: Dict) -> Dict:
        """Normalize field names to our standard schema"""
        field_mappings = self.get_field_mappings()
        normalized = {}
        for our_field, provider_field in field_mappings.items():
            if provider_field in data:
                normalized[our_field] = data[provider_field]
        return normalized
        
    @abstractmethod
    def get_field_mappings(self) -> Dict[str, str]:
        """Return mapping of our fields to provider fields"""
        pass
```

### **2.2 Provider-Specific Adapters**

#### **Race Roster Adapter**
```python
# providers/race_roster_adapter.py
import requests
from .base_adapter import BaseProviderAdapter, ProviderEvent, ProviderParticipant

class RaceRosterAdapter(BaseProviderAdapter):
    BASE_URL = "https://raceroster.com/api/v1"
    
    def authenticate(self) -> bool:
        try:
            response = requests.get(
                f"{self.BASE_URL}/auth/validate",
                headers={"Authorization": f"Bearer {self.credentials['api_key']}"}
            )
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
            
    def get_events(self, filters: Optional[Dict] = None) -> List[ProviderEvent]:
        # Implementation using Race Roster API
        # https://racerosterv1.docs.apiary.io/#
        pass
        
    def get_field_mappings(self) -> Dict[str, str]:
        return {
            'first_name': 'firstName',
            'last_name': 'lastName', 
            'email': 'emailAddress',
            'bib_number': 'bibNumber',
            'gender': 'gender',
            'age': 'age',
            'city': 'city',
            'state': 'provinceState'
        }
```

#### **Haku Adapter**
```python
# providers/haku_adapter.py
import requests
from .base_adapter import BaseProviderAdapter

class HakuAdapter(BaseProviderAdapter):
    BASE_URL = "https://api.hakuapp.com/v1"
    
    def authenticate(self) -> bool:
        # Implementation using Haku API
        # https://stg-developer.hakuapp.com
        pass
        
    def get_field_mappings(self) -> Dict[str, str]:
        return {
            'first_name': 'first_name',
            'last_name': 'last_name',
            'email': 'email',
            'bib_number': 'bib',
            # Add Haku-specific mappings
        }
```

#### **Copernico Adapter**
```python
# providers/copernico_adapter.py
import requests
from .base_adapter import BaseProviderAdapter

class CopernicoAdapter(BaseProviderAdapter):
    BASE_URL = "https://development.timingsense.cloud"
    RANKINGS_URL = "https://development.timingsense.cloud/rankings-api"
    
    def authenticate(self) -> bool:
        # Implementation using Copernico API
        # https://development.timingsense.cloud/brrm-api/swagger/index.html
        pass
        
    def post_results(self, event_id: str, results: List[ProviderResult]) -> SyncResult:
        # Use rankings API for posting results
        # https://development.timingsense.cloud/rankings-api/swagger/index.html
        pass
```

#### **CTLive Adapter**  
```python
# providers/ctlive_adapter.py
import requests
from .base_adapter import BaseProviderAdapter

class CTLiveAdapter(BaseProviderAdapter):
    BASE_URL = "https://api.chronotrack.com"
    
    def authenticate(self) -> bool:
        # Implementation using CTLive API
        # https://api.chronotrack.com
        pass
```

---

## 🔄 **Phase 3: Sync Engine Implementation (Week 3)**

### **3.1 Sync Manager**

```python
# sync/sync_manager.py
from typing import Dict, List
from datetime import datetime, timedelta
import asyncio
from .database import DatabaseManager
from .providers import get_provider_adapter

class SyncManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    async def run_scheduled_syncs(self):
        """Run all scheduled sync operations"""
        connections = self.db.get_pending_sync_connections()
        
        for connection in connections:
            try:
                await self.execute_sync(connection)
            except Exception as e:
                self.logger.error(f"Sync failed for connection {connection.id}: {e}")
                
    async def execute_sync(self, connection):
        """Execute a single sync operation"""
        # Create sync operation record
        sync_op = self.db.create_sync_operation(
            connection_id=connection.id,
            operation_type='participant_sync',
            sync_direction='registration_to_scoring',
            trigger_type='scheduled'
        )
        
        try:
            # Get source adapter (registration)
            source_adapter = get_provider_adapter(
                connection.source_provider_name,
                connection.source_credentials
            )
            
            # Get target adapter (scoring)
            target_adapter = get_provider_adapter(
                connection.target_provider_name, 
                connection.target_credentials
            )
            
            # Get events from source
            events = source_adapter.get_events()
            
            for event in events:
                # Get participants
                participants = source_adapter.get_participants(event.provider_event_id)
                
                # Transform data using mapping config
                transformed_participants = self.transform_participants(
                    participants, 
                    connection.mapping_config
                )
                
                # Create event in target if needed
                target_event_id = target_adapter.create_event(event)
                
                # Sync participants
                result = target_adapter.sync_participants(
                    target_event_id, 
                    transformed_participants
                )
                
                # Update sync operation
                self.db.update_sync_operation(sync_op.id, {
                    'processed_records': len(participants),
                    'success_records': result.processed_count,
                    'error_records': result.error_count
                })
                
            # Mark as completed
            self.db.complete_sync_operation(sync_op.id, 'completed')
            
        except Exception as e:
            self.db.complete_sync_operation(sync_op.id, 'failed', str(e))
            raise
```

### **3.2 Manual Sync API Endpoints**

```python
# api/sync_endpoints.py
from flask import Blueprint, request, jsonify
from .sync_manager import SyncManager

sync_bp = Blueprint('sync', __name__)

@sync_bp.route('/api/sync/manual', methods=['POST'])
@require_auth
def trigger_manual_sync():
    """Trigger manual sync for a connection"""
    data = request.get_json()
    connection_id = data.get('connection_id')
    
    # Queue manual sync
    sync_manager.queue_manual_sync(connection_id, request.user['user_id'])
    
    return jsonify({
        'success': True,
        'message': 'Manual sync queued successfully'
    })

@sync_bp.route('/api/sync/status/<connection_id>')
@require_auth  
def get_sync_status(connection_id):
    """Get sync status for a connection"""
    operations = db.get_sync_operations(connection_id, limit=10)
    
    return jsonify({
        'connection_id': connection_id,
        'recent_operations': [op.to_dict() for op in operations],
        'last_success': db.get_last_successful_sync(connection_id),
        'next_scheduled': db.get_next_sync_time(connection_id)
    })
```

---

## 🖥️ **Phase 4: Race Display Integration (Week 4)**

### **4.1 Enhanced Event Selection**

Update the race display application to show events from all providers:

```python
# race_display/enhanced_event_api.py
@app.route('/api/events/unified')
@require_auth
def get_unified_events():
    """Get events from all connected providers for timing partner"""
    timing_partner_id = request.user['timing_partner_id']
    
    # Get events from normalized_events table
    events = db.execute("""
        SELECT * FROM unified_events 
        WHERE timing_partner_id = %s 
        ORDER BY event_date DESC
        LIMIT 50
    """, (timing_partner_id,))
    
    return jsonify({
        'events': [dict(event) for event in events],
        'providers': db.get_connected_providers(timing_partner_id)
    })

@app.route('/api/events/<int:event_id>/participants')
@require_auth
def get_event_participants(event_id):
    """Get participants for an event from normalized data"""
    participants = db.execute("""
        SELECT np.*, ne.event_name, ne.source_provider
        FROM normalized_participants np
        JOIN normalized_events ne ON np.normalized_event_id = ne.id
        WHERE ne.id = %s
    """, (event_id,))
    
    return jsonify({
        'participants': [dict(p) for p in participants]
    })
```

### **4.2 Tag Data Integration**

Link timing tag data to normalized participants:

```python
# race_display/timing_integration.py
def link_timing_to_participants(timing_read, event_id):
    """Link incoming timing read to normalized participant"""
    
    # Find participant by bib number
    participant = db.execute("""
        SELECT np.*, ne.timing_partner_id
        FROM normalized_participants np
        JOIN normalized_events ne ON np.normalized_event_id = ne.id  
        WHERE ne.id = %s AND np.bib_number = %s
    """, (event_id, timing_read.bib_number))
    
    if participant:
        # Update timing_reads with participant link
        db.execute("""
            UPDATE timing_reads 
            SET normalized_event_id = %s, timing_partner_id = %s
            WHERE id = %s
        """, (event_id, participant['timing_partner_id'], timing_read.id))
        
        return participant
    return None
```

---

## ⚙️ **Phase 5: Admin Interface & Self-Service (Week 5)**

### **5.1 Provider Connection Management UI**

```javascript
// frontend/src/components/ProviderConnections.jsx
import React, { useState, useEffect } from 'react';

const ProviderConnections = () => {
    const [connections, setConnections] = useState([]);
    const [providers, setProviders] = useState([]);
    
    const createConnection = async (connectionData) => {
        const response = await fetch('/api/provider-connections', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(connectionData)
        });
        
        if (response.ok) {
            loadConnections(); // Refresh list
        }
    };
    
    return (
        <div className="provider-connections">
            <h2>Provider Integrations</h2>
            
            {/* Connection List */}
            <div className="connections-list">
                {connections.map(conn => (
                    <ConnectionCard 
                        key={conn.id} 
                        connection={conn}
                        onSync={() => triggerManualSync(conn.id)}
                        onEdit={() => editConnection(conn.id)}
                    />
                ))}
            </div>
            
            {/* Add New Connection */}
            <ConnectionForm 
                providers={providers}
                onSubmit={createConnection}
            />
        </div>
    );
};
```

### **5.2 Field Mapping Interface**

```javascript
// frontend/src/components/FieldMapping.jsx
const FieldMappingEditor = ({ sourceProvider, targetProvider, mappingConfig, onChange }) => {
    const [mappings, setMappings] = useState(mappingConfig || {});
    
    const standardFields = [
        'first_name', 'last_name', 'email', 'bib_number', 
        'gender', 'age', 'city', 'state', 'phone'
    ];
    
    return (
        <div className="field-mapping">
            <h3>Field Mappings: {sourceProvider} → {targetProvider}</h3>
            
            {standardFields.map(field => (
                <div key={field} className="mapping-row">
                    <label>{field}</label>
                    <select
                        value={mappings[field] || ''}
                        onChange={(e) => updateMapping(field, e.target.value)}
                    >
                        <option value="">-- Select Field --</option>
                        {getProviderFields(sourceProvider).map(pField => (
                            <option key={pField} value={pField}>{pField}</option>
                        ))}
                    </select>
                </div>
            ))}
        </div>
    );
};
```

---

## 📊 **Phase 6: Monitoring & Analytics (Week 6)**

### **6.1 Sync Monitoring Dashboard**

```python
# api/monitoring_endpoints.py
@app.route('/api/monitoring/sync-summary')
@require_admin
def get_sync_summary():
    """Get sync operation summary for all timing partners"""
    
    summary = db.execute("""
        SELECT 
            tp.name as timing_partner,
            COUNT(pc.id) as total_connections,
            COUNT(CASE WHEN pc.sync_status = 'active' THEN 1 END) as active_connections,
            COUNT(so.id) as total_syncs_24h,
            COUNT(CASE WHEN so.status = 'completed' THEN 1 END) as successful_syncs_24h,
            COUNT(CASE WHEN so.status = 'failed' THEN 1 END) as failed_syncs_24h
        FROM timing_partners tp
        LEFT JOIN provider_connections pc ON tp.id = pc.timing_partner_id
        LEFT JOIN sync_operations so ON pc.id = so.connection_id 
            AND so.started_at > NOW() - INTERVAL '24 hours'
        GROUP BY tp.id, tp.name
        ORDER BY tp.name
    """)
    
    return jsonify({
        'summary': [dict(row) for row in summary],
        'total_events': db.count_normalized_events(),
        'total_participants': db.count_normalized_participants()
    })

@app.route('/api/monitoring/participant-tracking')  
@require_admin
def get_participant_tracking():
    """Get participant cross-system tracking metrics"""
    
    tracking = db.execute("""
        SELECT 
            timing_partner_name,
            COUNT(DISTINCT global_participant_id) as unique_participants,
            AVG(events_participated) as avg_events_per_participant,
            COUNT(DISTINCT providers_used) as providers_used
        FROM participant_tracking
        GROUP BY timing_partner_name
    """)
    
    return jsonify({
        'tracking': [dict(row) for row in tracking]
    })
```

### **6.2 Error Handling & Alerting**

```python
# monitoring/alert_system.py
import smtplib
from email.mime.text import MIMEText

class AlertSystem:
    def __init__(self, smtp_config):
        self.smtp_config = smtp_config
        
    def check_sync_failures(self):
        """Check for sync failures and send alerts"""
        failures = db.execute("""
            SELECT 
                pc.connection_name,
                tp.name as timing_partner,
                so.error_details,
                so.started_at
            FROM sync_operations so
            JOIN provider_connections pc ON so.connection_id = pc.id
            JOIN timing_partners tp ON pc.timing_partner_id = tp.id
            WHERE so.status = 'failed' 
            AND so.started_at > NOW() - INTERVAL '1 hour'
        """)
        
        if failures:
            self.send_alert(
                subject="Provider Sync Failures Detected",
                message=self.format_failure_message(failures)
            )
            
    def check_stale_syncs(self):
        """Check for connections that haven't synced recently"""
        stale = db.execute("""
            SELECT 
                pc.connection_name,
                tp.name as timing_partner,
                pc.last_sync_at,
                pc.sync_frequency
            FROM provider_connections pc
            JOIN timing_partners tp ON pc.timing_partner_id = tp.id
            WHERE pc.auto_sync_enabled = true
            AND (pc.last_sync_at IS NULL OR 
                 pc.last_sync_at < NOW() - (pc.sync_frequency * 2))
        """)
        
        if stale:
            self.send_alert(
                subject="Stale Provider Connections Detected",
                message=self.format_stale_message(stale)
            )
```

---

## 🚀 **Implementation Timeline**

| Week | Phase | Deliverables | Success Criteria |
|------|-------|--------------|------------------|
| **Week 1** | Database Foundation | - Migration script executed<br>- Existing data migrated<br>- Views and functions tested | - All 13 timing partners have data in normalized tables<br>- Unified queries working |
| **Week 2** | Provider Adapters | - Base adapter class<br>- 4 provider-specific adapters<br>- Authentication working | - Can connect to all 4 new providers<br>- Data retrieval working |
| **Week 3** | Sync Engine | - Sync manager<br>- Scheduled sync worker<br>- Manual sync API | - Automated syncs running<br>- Manual syncs working via API |
| **Week 4** | Race Display Integration | - Enhanced event selection<br>- Tag data linking<br>- Multi-provider support | - Race display shows unified events<br>- Timing data links to participants |
| **Week 5** | Admin Interface | - Provider connection UI<br>- Field mapping editor<br>- Self-service capabilities | - Timing partners can configure connections<br>- No developer intervention needed |
| **Week 6** | Monitoring & Polish | - Monitoring dashboard<br>- Error alerting<br>- Documentation | - Full observability<br>- Production-ready system |

---

## 🔒 **Security & Compliance**

### **Data Protection**
- All provider credentials encrypted at rest using existing encryption system
- API keys rotated quarterly with automated alerts
- PII data handling follows GDPR guidelines
- Audit logging for all sync operations

### **Rate Limiting**
- Respect provider API rate limits (stored in `providers` table)
- Exponential backoff for failed requests
- Queue management to prevent API abuse

### **Access Control**
- Timing partner data isolation maintained
- Admin override for support purposes
- Role-based access to sync management features

---

## 📈 **Success Metrics**

### **Technical Metrics**
- **Sync Success Rate**: >95% of scheduled syncs complete successfully
- **Data Accuracy**: <1% data discrepancy between systems
- **Response Time**: API responses <500ms for unified queries
- **Uptime**: 99.9% availability for sync services

### **Business Metrics**
- **Provider Adoption**: 80% of timing partners using at least one new provider connection within 3 months
- **Manual Sync Usage**: <10% of total syncs (rest should be automated)
- **Support Tickets**: <5 sync-related tickets per month across all timing partners

---

## 🛠️ **Development Environment Setup**

```bash
# 1. Set up development database
createdb project88_dev
psql -d project88_dev -f database_migration_v1.sql

# 2. Install provider SDK dependencies  
pip install requests python-dateutil pydantic

# 3. Environment variables
export RACE_ROSTER_API_KEY="your_key"
export HAKU_API_KEY="your_key"  
export COPERNICO_API_KEY="your_key"
export CTLIVE_API_KEY="your_key"

# 4. Run provider tests
python -m pytest providers/tests/ -v

# 5. Start sync worker
python sync/worker.py --environment=development
```

This implementation plan provides a complete roadmap for integrating all target providers while maintaining the robust, multi-tenant architecture you already have in production. 