-- ========================================================================
-- PROJECT88HUB - MISSING PROVIDER TABLES CREATION SCRIPT
-- Execute this on your PostgreSQL database to add missing provider integrations
-- ========================================================================

-- Connect to the correct database
\c project88_myappdb;

-- ========================================================================
-- RACE ROSTER INTEGRATION TABLES
-- ========================================================================

CREATE TABLE IF NOT EXISTS raceroster_events (
    event_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50),
    distance DECIMAL(10,2),
    max_participants INTEGER,
    registration_open_date TIMESTAMP,
    registration_close_date TIMESTAMP,
    event_type VARCHAR(50),
    currency VARCHAR(10),
    registration_fee DECIMAL(10,2),
    event_status VARCHAR(20) DEFAULT 'active',
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS raceroster_participants (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) REFERENCES raceroster_events(event_id) ON DELETE CASCADE,
    participant_id VARCHAR(100),
    bib_number VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    date_of_birth DATE,
    gender VARCHAR(20),
    address JSONB, -- Store address as JSON
    emergency_contact JSONB,
    team_name VARCHAR(255),
    division VARCHAR(50),
    registration_date TIMESTAMP,
    payment_status VARCHAR(20),
    amount_paid DECIMAL(10,2),
    special_requirements TEXT,
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ========================================================================
-- COPERNICO INTEGRATION TABLES  
-- ========================================================================

CREATE TABLE IF NOT EXISTS copernico_events (
    event_id VARCHAR(100) PRIMARY KEY,
    event_name VARCHAR(255),
    event_description TEXT,
    event_date TIMESTAMP,
    location VARCHAR(255),
    event_type VARCHAR(50),
    distance_km DECIMAL(10,2),
    max_participants INTEGER,
    event_status VARCHAR(20) DEFAULT 'active',
    organization_id VARCHAR(100),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS copernico_participants (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) REFERENCES copernico_events(event_id) ON DELETE CASCADE,
    participant_id VARCHAR(100),
    bib_number VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    gender VARCHAR(20),
    age INTEGER,
    category VARCHAR(50),
    team_name VARCHAR(255),
    registration_status VARCHAR(20) DEFAULT 'registered',
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS copernico_results (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) REFERENCES copernico_events(event_id) ON DELETE CASCADE,
    participant_id VARCHAR(100),
    bib_number VARCHAR(20),
    overall_place INTEGER,
    gender_place INTEGER,
    division_place INTEGER,
    start_time TIMESTAMP,
    finish_time TIMESTAMP,
    total_time INTERVAL,
    split_times JSONB, -- Store split times as JSON
    result_status VARCHAR(20) DEFAULT 'finished', -- finished, dns, dnf, dq
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ========================================================================
-- COMPLETE HAKU INTEGRATION (extend existing foundation)
-- ========================================================================

CREATE TABLE IF NOT EXISTS haku_events (
    event_id VARCHAR(100) PRIMARY KEY,
    organization_id VARCHAR(100),
    event_name VARCHAR(255),
    event_description TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    location VARCHAR(255),
    event_type VARCHAR(50),
    distance VARCHAR(50), -- Haku uses string format
    registration_limit INTEGER,
    registration_count INTEGER,
    registration_fee DECIMAL(10,2),
    currency VARCHAR(10),
    event_status VARCHAR(20) DEFAULT 'active',
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS haku_participants (
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
    category VARCHAR(50),
    registration_date TIMESTAMP,
    payment_status VARCHAR(20),
    amount_paid DECIMAL(10,2),
    special_requirements TEXT,
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ========================================================================
-- PERFORMANCE INDEXES
-- ========================================================================

-- Race Roster indexes
CREATE INDEX IF NOT EXISTS idx_raceroster_events_timing_partner ON raceroster_events(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_raceroster_events_start_date ON raceroster_events(start_date);
CREATE INDEX IF NOT EXISTS idx_raceroster_participants_event ON raceroster_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_raceroster_participants_timing_partner ON raceroster_participants(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_raceroster_participants_bib ON raceroster_participants(bib_number);
CREATE INDEX IF NOT EXISTS idx_raceroster_participants_email ON raceroster_participants(email);

-- Copernico indexes
CREATE INDEX IF NOT EXISTS idx_copernico_events_timing_partner ON copernico_events(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_copernico_events_date ON copernico_events(event_date);
CREATE INDEX IF NOT EXISTS idx_copernico_participants_event ON copernico_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_copernico_participants_timing_partner ON copernico_participants(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_copernico_participants_bib ON copernico_participants(bib_number);
CREATE INDEX IF NOT EXISTS idx_copernico_results_event ON copernico_results(event_id);
CREATE INDEX IF NOT EXISTS idx_copernico_results_timing_partner ON copernico_results(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_copernico_results_bib ON copernico_results(bib_number);

-- Haku indexes
CREATE INDEX IF NOT EXISTS idx_haku_events_timing_partner ON haku_events(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_haku_events_start_date ON haku_events(start_date);
CREATE INDEX IF NOT EXISTS idx_haku_participants_event ON haku_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_haku_participants_timing_partner ON haku_participants(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_haku_participants_bib ON haku_participants(bib_number);

-- ========================================================================
-- UPDATE UNIFIED VIEWS (Extend existing to include new providers)
-- ========================================================================

-- Update unified_participants view to include all providers
CREATE OR REPLACE VIEW unified_participants AS
SELECT 
    'runsignup' as source_provider,
    timing_partner_id,
    event_id::VARCHAR,
    first_name,
    last_name,
    email,
    gender,
    bib_num as bib_number,
    (address->>'city') as city,
    (address->>'state') as state,
    age,
    registration_date,
    fetched_date
FROM runsignup_participants

UNION ALL

SELECT 
    'raceroster' as source_provider,
    timing_partner_id,
    event_id,
    first_name,
    last_name,
    email,
    gender,
    bib_number,
    (address->>'city') as city,
    (address->>'state') as state,
    NULL as age,
    registration_date,
    fetched_date
FROM raceroster_participants

UNION ALL

SELECT 
    'haku' as source_provider,
    timing_partner_id,
    event_id,
    first_name,
    last_name,
    email,
    gender,
    bib_number,
    NULL as city,
    NULL as state,
    NULL as age,
    registration_date,
    fetched_date
FROM haku_participants

UNION ALL

SELECT 
    'copernico' as source_provider,
    timing_partner_id,
    event_id,
    first_name,
    last_name,
    email,
    gender,
    bib_number,
    NULL as city,
    NULL as state,
    age,
    NULL as registration_date,
    fetched_date
FROM copernico_participants

UNION ALL

SELECT
    'chronotrack' as source_provider,
    timing_partner_id,
    event_id,
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
FROM ct_participants;

-- Update unified_events view to include all providers
CREATE OR REPLACE VIEW unified_events AS
SELECT 
    'runsignup' as source_provider,
    timing_partner_id,
    event_id::VARCHAR,
    name as event_name,
    start_time as event_date,
    fetched_date
FROM runsignup_events

UNION ALL

SELECT 
    'raceroster' as source_provider,
    timing_partner_id,
    event_id,
    name as event_name,
    start_date as event_date,
    fetched_date
FROM raceroster_events

UNION ALL

SELECT 
    'haku' as source_provider,
    timing_partner_id,
    event_id,
    event_name,
    start_date as event_date,
    fetched_date
FROM haku_events

UNION ALL

SELECT 
    'copernico' as source_provider,
    timing_partner_id,
    event_id,
    event_name,
    event_date,
    fetched_date
FROM copernico_events

UNION ALL

SELECT
    'chronotrack' as source_provider,
    timing_partner_id,
    event_id,
    event_name,
    event_start_time as event_date,
    created_at as fetched_date
FROM ct_events;

-- Create unified_results view (includes existing ChronoTrack + new Copernico)
CREATE OR REPLACE VIEW unified_results AS
SELECT 
    'chronotrack' as source_provider,
    timing_partner_id,
    event_id,
    results_bib as bib_number,
    results_first_name as first_name,
    results_last_name as last_name,
    results_sex as gender,
    results_age as age,
    results_time,
    results_gun_time,
    results_rank as overall_place,
    created_at as fetched_date
FROM ct_results

UNION ALL

SELECT
    'copernico' as source_provider,
    timing_partner_id,
    event_id,
    bib_number,
    first_name,
    last_name,
    gender,
    age,
    total_time::VARCHAR as results_time,
    total_time::VARCHAR as results_gun_time,
    overall_place,
    fetched_date
FROM copernico_results;

-- ========================================================================
-- VERIFICATION & TESTING QUERIES
-- ========================================================================

-- Verify tables were created successfully
SELECT 
    table_name, 
    table_type 
FROM information_schema.tables 
WHERE table_schema = 'public' 
    AND (table_name LIKE 'raceroster_%' 
         OR table_name LIKE 'copernico_%' 
         OR table_name LIKE 'haku_%')
ORDER BY table_name;

-- Test unified views with existing data
SELECT 
    source_provider,
    COUNT(*) as total_participants
FROM unified_participants 
GROUP BY source_provider;

SELECT 
    source_provider,
    COUNT(*) as total_events
FROM unified_events 
GROUP BY source_provider;

-- Check indexes were created
SELECT 
    indexname,
    tablename
FROM pg_indexes 
WHERE schemaname = 'public' 
    AND (tablename LIKE 'raceroster_%' 
         OR tablename LIKE 'copernico_%' 
         OR tablename LIKE 'haku_%')
ORDER BY tablename, indexname;

PRINT 'Database tables created successfully!';
PRINT 'Next: Test unified views and start provider integrations.'; 