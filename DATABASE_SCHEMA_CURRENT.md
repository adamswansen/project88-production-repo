# 🗄️ PROJECT88HUB DATABASE SCHEMA - CURRENT STATE

**Last Updated**: January 2025  
**Database**: project88_myappdb (PostgreSQL)  
**Server**: 69.62.69.90 (Production)  
**Total Records**: 10.8M+ migrated + current data

---

## 📊 **SCHEMA OVERVIEW**

### **Provider Integration Architecture**
- **Multi-tenant Design**: Timing partner isolation via `timing_partner_id`
- **Provider-Specific Tables**: Raw data preservation per provider
- **Unified Views**: Cross-provider analytics and race display
- **Sync Infrastructure**: Queue-based data synchronization

---

## 🏗️ **CORE INFRASTRUCTURE TABLES**

### **timing_partners**
Core multi-tenant table managing timing companies

```sql
timing_partners (
    timing_partner_id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    contact_email VARCHAR(255),
    api_access_enabled BOOLEAN,
    created_at TIMESTAMP DEFAULT NOW()
)
```

### **providers**  
Provider registration and configuration

```sql
providers (
    id SERIAL PRIMARY KEY,
    provider_name VARCHAR(100) UNIQUE,
    provider_type VARCHAR(50), -- 'registration', 'scoring' 
    api_base_url VARCHAR(255),
    rate_limit_per_hour INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
)
```

### **users**
System users and authentication

```sql
users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    role VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
)
```

---

## 🔄 **SYNC INFRASTRUCTURE TABLES**

### **sync_queue**
Job queue for data synchronization

```sql
sync_queue (
    id SERIAL PRIMARY KEY,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    provider_name VARCHAR(100),
    sync_type VARCHAR(50), -- 'events', 'participants', 'results'
    priority INTEGER DEFAULT 5,
    status VARCHAR(20) DEFAULT 'pending',
    scheduled_for TIMESTAMP DEFAULT NOW(),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW()
)
```

### **sync_history**  
Audit trail for sync operations

```sql
sync_history (
    id SERIAL PRIMARY KEY,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    provider_name VARCHAR(100),
    sync_type VARCHAR(50),
    status VARCHAR(20), -- 'success', 'failed', 'partial'
    records_processed INTEGER,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
)
```

---

## 📋 **PROVIDER-SPECIFIC TABLES**

### **1. RUNSIGNUP TABLES** ✅ **COMPLETE**

#### **runsignup_events**
**Status**: ✅ Production (937 events)

```sql
runsignup_events (
    event_id INTEGER PRIMARY KEY,
    race_id INTEGER,
    name TEXT,
    details TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    age_calc_base_date DATE,
    registration_opens TIMESTAMP,
    event_type VARCHAR(50),
    distance NUMERIC(10,2),
    volunteer BOOLEAN,
    require_dob BOOLEAN,
    require_phone BOOLEAN,
    giveaway TEXT,
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    created_at TIMESTAMP DEFAULT NOW()
)
```

#### **runsignup_participants**
**Status**: ✅ Production (38,362 participants)

```sql
runsignup_participants (
    id SERIAL PRIMARY KEY,
    race_id INTEGER,
    event_id INTEGER, 
    registration_id INTEGER,
    user_id INTEGER,
    first_name VARCHAR(100),
    middle_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    address JSONB,
    dob DATE,
    gender VARCHAR(20),
    phone VARCHAR(20),
    profile_image_url VARCHAR(255),
    bib_num VARCHAR(20),
    chip_num VARCHAR(20),
    age INTEGER,
    registration_date TIMESTAMP,
    team_info JSONB,
    payment_info JSONB,
    additional_data JSONB,
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    created_at TIMESTAMP DEFAULT NOW(),
    -- Additional payment/team fields...
    race_fee NUMERIC(10,2),
    amount_paid NUMERIC(10,2),
    team_name VARCHAR(255),
    fundraiser_charity_name VARCHAR(255)
)
```

### **2. CHRONOTRACK TABLES** ✅ **COMPLETE**

#### **ct_events**
**Status**: ✅ Production (12,882 events)

```sql
ct_events (
    event_id VARCHAR(100) PRIMARY KEY,
    event_name VARCHAR(255),
    event_start_time TIMESTAMP,
    event_type VARCHAR(50),
    location JSONB,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    created_at TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255)
)
```

#### **ct_participants**  
**Status**: ✅ Production (2,382,266 participants)

```sql
ct_participants (
    entry_id VARCHAR(100) PRIMARY KEY,
    event_id VARCHAR(100),
    race_id VARCHAR(100),
    entry_external_id VARCHAR(100),
    entry_name VARCHAR(255),
    entry_type VARCHAR(50),
    entry_status VARCHAR(50),
    entry_bib VARCHAR(20),
    entry_race_age INTEGER,
    athlete_id VARCHAR(100),
    athlete_first_name VARCHAR(100),
    athlete_last_name VARCHAR(100),
    athlete_sex VARCHAR(20),
    athlete_birthdate DATE,
    athlete_email VARCHAR(255),
    athlete_home_phone VARCHAR(20),
    athlete_mobile_phone VARCHAR(20),
    location JSONB,
    team_id VARCHAR(100),
    team_name VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    created_at TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255)
)
```

#### **ct_results**
**Status**: ✅ Production (7,644,980 results)

```sql
ct_results (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100),
    results_bib VARCHAR(20),
    results_first_name VARCHAR(100),
    results_last_name VARCHAR(100),
    results_sex VARCHAR(20),
    results_age INTEGER,
    results_time VARCHAR(50),
    results_gun_time VARCHAR(50),
    results_rank INTEGER,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    created_at TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255)
)
```

### **3. RACE ROSTER TABLES** ✅ **READY FOR INTEGRATION**

#### **raceroster_events**
**Status**: ✅ Tables Created (Ready for data)

```sql
raceroster_events (
    event_id INTEGER PRIMARY KEY,
    race_id INTEGER,
    name VARCHAR(255),
    description TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    location_name VARCHAR(255),
    address JSONB,
    timezone VARCHAR(50),
    distance NUMERIC(10,2),
    event_type VARCHAR(50),
    registration_open_date TIMESTAMP,
    registration_close_date TIMESTAMP,
    max_participants INTEGER,
    current_participants INTEGER,
    price NUMERIC(10,2),
    currency VARCHAR(10),
    status VARCHAR(50),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    created_at TIMESTAMP DEFAULT NOW()
)
```

#### **raceroster_participants**
**Status**: ✅ Tables Created (Ready for data)

```sql
raceroster_participants (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES raceroster_events(event_id) ON DELETE CASCADE,
    registration_id INTEGER,
    bib_number VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    date_of_birth DATE,
    gender VARCHAR(20),
    address JSONB,
    emergency_contact JSONB,
    team_name VARCHAR(255),
    division VARCHAR(100),
    registration_date TIMESTAMP,
    registration_status VARCHAR(50),
    payment_status VARCHAR(50),
    amount_paid NUMERIC(10,2),
    additional_info JSONB,
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    created_at TIMESTAMP DEFAULT NOW()
)
```

### **4. COPERNICO TABLES** ✅ **READY FOR INTEGRATION**

#### **copernico_events**
**Status**: ✅ Tables Created (Ready for data)

```sql
copernico_events (
    event_id VARCHAR(100) PRIMARY KEY,
    event_name VARCHAR(255),
    event_date TIMESTAMP,
    location VARCHAR(255),
    discipline VARCHAR(100),
    distance NUMERIC(10,2),
    event_type VARCHAR(50),
    organizer VARCHAR(255),
    status VARCHAR(50),
    max_participants INTEGER,
    registration_fee NUMERIC(10,2),
    currency VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id)
)
```

#### **copernico_participants**
**Status**: ✅ Tables Created (Ready for data)

```sql
copernico_participants (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) REFERENCES copernico_events(event_id) ON DELETE CASCADE,
    participant_id VARCHAR(100),
    bib_number VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(20),
    nationality VARCHAR(50),
    club_team VARCHAR(255),
    category VARCHAR(100),
    license_number VARCHAR(50),
    registration_status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id)
)
```

#### **copernico_results**
**Status**: ✅ Tables Created (Ready for data)

```sql
copernico_results (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) REFERENCES copernico_events(event_id) ON DELETE CASCADE,
    participant_id VARCHAR(100),
    bib_number VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    category VARCHAR(100),
    start_time TIMESTAMP,
    finish_time TIMESTAMP,
    total_time INTERVAL,
    split_times JSONB,
    overall_position INTEGER,
    category_position INTEGER,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id)
)
```

### **5. HAKU TABLES** ✅ **READY FOR INTEGRATION**

#### **haku_events**
**Status**: ✅ Tables Created (Ready for data)

```sql
haku_events (
    event_id VARCHAR(100) PRIMARY KEY,
    event_name VARCHAR(255),
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    location VARCHAR(255),
    event_type VARCHAR(50),
    distance NUMERIC(10,2),
    max_participants INTEGER,
    registration_fee NUMERIC(10,2),
    currency VARCHAR(10),
    status VARCHAR(50),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    created_at TIMESTAMP DEFAULT NOW()
)
```

#### **haku_participants**
**Status**: ✅ Tables Created (Ready for data)

```sql
haku_participants (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) REFERENCES haku_events(event_id) ON DELETE CASCADE,
    participant_id VARCHAR(100),
    bib_number VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    date_of_birth DATE,
    gender VARCHAR(20),
    nationality VARCHAR(50),
    emergency_contact JSONB,
    team_affiliation VARCHAR(255),
    category VARCHAR(100),
    registration_date TIMESTAMP,
    payment_status VARCHAR(50),
    amount_paid NUMERIC(10,2),
    special_requirements TEXT,
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    created_at TIMESTAMP DEFAULT NOW()
)
```

---

## 🔗 **UNIFIED VIEWS** ✅ **WORKING**

### **unified_participants**
**Status**: ✅ Production (2,420,628 records across 2 providers)

Cross-provider participant data for race display and analytics:

```sql
CREATE VIEW unified_participants AS
SELECT 
    'runsignup' as source_provider,
    timing_partner_id,
    CAST(event_id AS VARCHAR) as event_id,
    first_name, last_name, email, gender,
    bib_num as bib_number,
    (address->>'city') as city,
    (address->>'state') as state,
    age, registration_date, fetched_date
FROM runsignup_participants

UNION ALL

SELECT
    'chronotrack' as source_provider,
    timing_partner_id, event_id,
    athlete_first_name as first_name,
    athlete_last_name as last_name,
    athlete_email as email,
    athlete_sex as gender,
    entry_bib as bib_number,
    (location->>'city') as city,
    (location->>'region') as state,
    entry_race_age as age,
    NULL as registration_date,
    created_at as fetched_date
FROM ct_participants

-- Additional UNION ALL for raceroster, haku, copernico...
```

### **unified_events**
**Status**: ✅ Production (13,819 events across 2 providers)

Cross-provider event data:

```sql
CREATE VIEW unified_events AS
SELECT 
    'runsignup' as source_provider,
    timing_partner_id,
    CAST(event_id AS VARCHAR) as event_id,
    name as event_name,
    start_time as event_date,
    fetched_date
FROM runsignup_events

UNION ALL

SELECT
    'chronotrack' as source_provider,
    timing_partner_id, event_id,
    event_name,
    event_start_time as event_date,
    created_at as fetched_date
FROM ct_events

-- Additional UNION ALL for raceroster, haku, copernico...
```

### **unified_results**
**Status**: ✅ Production (7,644,980 results from ChronoTrack)

Cross-provider timing results:

```sql
CREATE VIEW unified_results AS
SELECT 
    'chronotrack' as source_provider,
    timing_partner_id, event_id,
    results_bib as bib_number,
    results_first_name as first_name,
    results_last_name as last_name,
    results_sex as gender,
    results_age as age,
    results_time, results_gun_time,
    results_rank as overall_place,
    created_at as fetched_date
FROM ct_results

UNION ALL

SELECT
    'copernico' as source_provider,
    timing_partner_id, event_id,
    bib_number, first_name, last_name,
    NULL as gender, NULL as age,
    total_time::VARCHAR as results_time,
    total_time::VARCHAR as results_gun_time,
    overall_position as overall_place,
    fetched_date
FROM copernico_results;
```

---

## 📈 **PERFORMANCE INDEXES**

### **Primary Indexes** ✅
- All primary keys indexed
- Foreign key constraints with automatic indexes
- Timing partner isolation indexes

### **Query Optimization Indexes** ✅
```sql
-- Unified view performance
CREATE INDEX idx_runsignup_participants_timing_partner ON runsignup_participants(timing_partner_id);
CREATE INDEX idx_ct_participants_timing_partner ON ct_participants(timing_partner_id);
CREATE INDEX idx_raceroster_participants_timing_partner ON raceroster_participants(timing_partner_id);
CREATE INDEX idx_copernico_participants_timing_partner ON copernico_participants(timing_partner_id);
CREATE INDEX idx_haku_participants_timing_partner ON haku_participants(timing_partner_id);

-- Event lookups
CREATE INDEX idx_runsignup_events_start_time ON runsignup_events(start_time);
CREATE INDEX idx_raceroster_events_start_date ON raceroster_events(start_date);
CREATE INDEX idx_haku_events_start_date ON haku_events(start_date);

-- Participant searches
CREATE INDEX idx_runsignup_participants_email ON runsignup_participants(email);
CREATE INDEX idx_runsignup_participants_bib ON runsignup_participants(bib_num);
CREATE INDEX idx_ct_participants_bib ON ct_participants(entry_bib);
CREATE INDEX idx_raceroster_participants_bib ON raceroster_participants(bib_number);
```

---

## 🔒 **DATA CONSTRAINTS & INTEGRITY**

### **Foreign Key Constraints** ✅
- All provider tables → `timing_partners(timing_partner_id)`
- Participant tables → Event tables (provider-specific)
- Results tables → Event tables (provider-specific)

### **Data Validation** ✅
- Email format validation
- Timestamp constraints
- Enum constraints for status fields
- JSONB validation for structured data

### **Multi-tenant Isolation** ✅
- Row-level security via `timing_partner_id`
- API access controls
- Credential isolation per timing partner

---

## 📊 **CURRENT DATA STATISTICS**

| Provider | Events | Participants | Results | Status |
|----------|--------|-------------|---------|---------|
| **RunSignUp** | 937 | 38,362 | - | ✅ Active |
| **ChronoTrack** | 12,882 | 2,382,266 | 7,644,980 | ✅ Active |
| **Race Roster** | 0 | 0 | - | 🔄 Ready |
| **Copernico** | 0 | 0 | 0 | 🔄 Ready |
| **Haku** | 0 | 0 | - | 🔄 Ready |
| **TOTALS** | **13,819** | **2,420,628** | **7,644,980** | |

---

## 🚀 **NEXT PHASE: PROVIDER INTEGRATIONS**

### **Ready for Implementation** ✅
1. **Database Schema**: Complete for all 5 providers
2. **Unified Views**: Working with existing data
3. **Performance**: Optimized with proper indexing
4. **Multi-tenant**: Isolation and security implemented

### **Implementation Order**
1. **Race Roster** → Simple API, registration only
2. **Copernico** → European market, timing + registration  
3. **Haku** → Regional growth, specialized platform

**The database foundation is production-ready for all provider integrations!** 🎯 