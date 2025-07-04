# Multi-Tenant Race Timing API Architecture Design

## 🏗️ **Architecture Overview**

Based on your production database analysis (13 timing partners, 10.6M records), we need a scalable multi-tenant API that supports:

- **13 Timing Partners** (Big River Race Management, Mid-Hudson Road Runners, etc.)
- **Natural Language Queries** ("Show me Boston Marathon finishers under 3 hours")
- **Performance at Scale** (8M+ race results, 1.7M+ participants)
- **External Integrations** (RunSignUp, ChronoTrack, Race Roster)

## 🏢 **Multi-Tenant Endpoint Structure**

### **Option A: Path-Based Tenancy** (Recommended)
```
/api/v1/partners/{timing_partner_id}/events
/api/v1/partners/{timing_partner_id}/races  
/api/v1/partners/{timing_partner_id}/participants
/api/v1/partners/{timing_partner_id}/results
/api/v1/partners/{timing_partner_id}/analytics
/api/v1/partners/{timing_partner_id}/nl-query    # Natural language
```

### **Option B: Header-Based Tenancy**
```
Headers: X-Timing-Partner-ID: 1
/api/v1/events
/api/v1/races
/api/v1/participants  
/api/v1/results
/api/v1/analytics
/api/v1/nl-query
```

### **Option C: Domain-Based Tenancy**
```
bigriver-api.project88hub.com/api/v1/events
midhudson-api.project88hub.com/api/v1/events
raceplace-api.project88hub.com/api/v1/events
```

## 🔐 **Authentication Strategy**

### **Natural Language Authentication**
```python
# Example: "I'm Josh from Big River Race Management, show me our events"
POST /api/v1/auth/natural-language
{
  "message": "I'm Josh from Big River Race Management, show me our events"
}

# Response:
{
  "authenticated": true,
  "timing_partner_id": 1,
  "user_id": 1,
  "permissions": ["read:events", "read:participants", "write:results"],
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### **Traditional API Key Authentication**
```python
# For programmatic access
Headers: 
  Authorization: Bearer {jwt_token}
  X-API-Key: {partner_api_key}
```

## 📊 **Core API Endpoints**

### **Events Management**
```python
GET    /api/v1/partners/{partner_id}/events
POST   /api/v1/partners/{partner_id}/events
GET    /api/v1/partners/{partner_id}/events/{event_id}
PUT    /api/v1/partners/{partner_id}/events/{event_id}
DELETE /api/v1/partners/{partner_id}/events/{event_id}

# Advanced queries
GET    /api/v1/partners/{partner_id}/events?status=active&year=2024
GET    /api/v1/partners/{partner_id}/events/{event_id}/races
GET    /api/v1/partners/{partner_id}/events/{event_id}/participants
GET    /api/v1/partners/{partner_id}/events/{event_id}/results
```

### **Natural Language Query Engine**
```python
POST /api/v1/partners/{partner_id}/nl-query
{
  "query": "How many runners finished the Boston Marathon under 3 hours?",
  "format": "json|csv|summary",
  "context": {
    "event_name": "Boston Marathon",
    "year": 2024
  }
}

# Response:
{
  "query": "How many runners finished the Boston Marathon under 3 hours?",
  "sql_generated": "SELECT COUNT(*) FROM ct_results WHERE...",
  "results": [{"count": 156}],
  "summary": "156 runners finished the Boston Marathon under 3 hours",
  "execution_time_ms": 234
}
```

### **Analytics & Reporting**
```python
GET /api/v1/partners/{partner_id}/analytics/performance
GET /api/v1/partners/{partner_id}/analytics/demographics  
GET /api/v1/partners/{partner_id}/analytics/trends
GET /api/v1/partners/{partner_id}/reports/finishers
GET /api/v1/partners/{partner_id}/reports/awards
```

### **Integration Management**
```python
GET    /api/v1/partners/{partner_id}/integrations
POST   /api/v1/partners/{partner_id}/integrations/runsignup/sync
POST   /api/v1/partners/{partner_id}/integrations/chronotrack/sync
GET    /api/v1/partners/{partner_id}/sync-history
```

## 🛡️ **Security & Isolation**

### **Row-Level Security (PostgreSQL)**
```sql
-- Enable RLS on all tables
ALTER TABLE ct_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE ct_races ENABLE ROW LEVEL SECURITY;
ALTER TABLE ct_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE ct_results ENABLE ROW LEVEL SECURITY;

-- Create policies for timing partner isolation
CREATE POLICY partner_isolation_events ON ct_events
  FOR ALL TO api_user
  USING (timing_partner_id = current_setting('app.current_partner_id')::int);

CREATE POLICY partner_isolation_races ON ct_races  
  FOR ALL TO api_user
  USING (timing_partner_id = current_setting('app.current_partner_id')::int);
```

### **API Security Layers**
1. **TLS 1.3** (Let's Encrypt certificates ✅)
2. **JWT Authentication** with timing partner claims
3. **Rate Limiting** (per partner, per endpoint)
4. **Input Validation** (Pydantic models)
5. **SQL Injection Prevention** (SQLAlchemy ORM)
6. **Audit Logging** (all API calls logged)

## ⚡ **Performance Optimization**

### **Database Query Optimization**
```python
# Use connection pooling
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://..."
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)

# Optimized queries with indexes
# Index on timing_partner_id for all tables ✅
# Composite indexes for common query patterns
CREATE INDEX idx_results_partner_time ON ct_results(timing_partner_id, results_time);
CREATE INDEX idx_participants_partner_event ON ct_participants(timing_partner_id, event_id);
```

### **Caching Strategy**
```python
# Redis caching for frequent queries
@cache(expire=300)  # 5 minute cache
async def get_partner_events(partner_id: int):
    return query_partner_events(partner_id)

# Cache natural language query results
@cache(expire=3600)  # 1 hour cache
async def nl_query_cache(partner_id: int, query_hash: str):
    return cached_results
```

## 🧠 **Natural Language Processing Pipeline**

### **Query Processing Flow**
```
1. Natural Language Input
   ↓
2. Intent Recognition (spaCy/NLTK)
   ↓  
3. Entity Extraction (Event names, dates, metrics)
   ↓
4. SQL Query Generation (Template-based + AI)
   ↓
5. Security Validation (Partner isolation)
   ↓
6. Query Execution (PostgreSQL)
   ↓
7. Result Formatting (JSON, CSV, natural language summary)
```

### **Example Query Patterns**
```python
query_patterns = {
    "participant_count": {
        "patterns": ["how many", "count", "number of participants"],
        "sql_template": "SELECT COUNT(*) FROM ct_participants WHERE timing_partner_id = {partner_id}"
    },
    "finish_times": {
        "patterns": ["finish time", "results", "who finished"],
        "sql_template": "SELECT * FROM ct_results WHERE timing_partner_id = {partner_id}"
    },
    "event_analysis": {
        "patterns": ["event", "race", "marathon", "5k"],
        "sql_template": "SELECT * FROM ct_events WHERE timing_partner_id = {partner_id}"
    }
}
```

## 📱 **API Versioning & Documentation**

### **Versioning Strategy**
- **URL Versioning**: `/api/v1/`, `/api/v2/`
- **Backward Compatibility**: v1 maintained for 12 months
- **Feature Flags**: New features behind flags

### **Auto-Generated Documentation**
- **OpenAPI/Swagger**: Auto-generated from FastAPI
- **Interactive Docs**: Available at `/docs`
- **Examples**: Real query examples for each partner

## 🚀 **Deployment Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (Nginx)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐     ┌─────────────────────────────┐  │
│  │   OpenWebUI     │────▶│    FastAPI (Multi-Tenant)  │  │
│  │  (NL Interface) │     │   Port 8000 (localhost)    │  │
│  └─────────────────┘     └──────────┬──────────────────┘  │
│                                     │                      │
│  ┌─────────────────┐     ┌─────────▼──────────────────┐  │
│  │  Mobile Apps    │────▶│   PostgreSQL (Optimized)   │  │
│  │  External APIs  │     │   8GB Shared Buffers       │  │
│  └─────────────────┘     └──────────┬──────────────────┘  │
│                                     │                      │
│  ┌─────────────────────────────────▼──────────────────┐  │
│  │                Redis Cache                          │  │
│  │         (Query Results & Sessions)                  │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## 📋 **Implementation Priority**

### **Phase 1: Core Structure (Today)**
1. ✅ Multi-tenant endpoint structure  
2. ✅ Authentication framework
3. ✅ Basic CRUD operations
4. ✅ Row-level security setup

### **Phase 2: Natural Language (Tomorrow)**
1. ✅ Query parsing engine
2. ✅ SQL generation templates
3. ✅ Result formatting
4. ✅ OpenWebUI integration

### **Phase 3: Production Features**
1. ✅ Caching layer
2. ✅ Rate limiting
3. ✅ Audit logging
4. ✅ Comprehensive testing

---

**Ready to implement this architecture?** 🚀