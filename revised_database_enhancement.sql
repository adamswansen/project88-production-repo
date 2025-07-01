-- ========================================================================
-- PROJECT88HUB DATABASE ENHANCEMENT V2.0  
-- Targeted additions to existing race_results.db system
-- Database Type: SQLite (not PostgreSQL)
-- ========================================================================

-- ========================================================================
-- SECTION 1: ADD MISSING PROVIDER TABLES (Following Existing Pattern)
-- ========================================================================

-- Add Race Roster tables (following runsignup_ pattern)
CREATE TABLE IF NOT EXISTS raceroster_events (
    event_id INTEGER PRIMARY KEY,
    race_id INTEGER,
    name TEXT,
    description TEXT,
    start_date TEXT,
    end_date TEXT,
    location_name TEXT,
    address_line1 TEXT,
    address_line2 TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT,
    timezone TEXT,
    distance TEXT,
    event_type TEXT,
    registration_open_date TEXT,
    registration_close_date TEXT,
    max_participants INTEGER,
    current_participants INTEGER,
    price TEXT,
    currency TEXT,
    status TEXT,
    fetched_date TEXT,
    credentials_used TEXT,
    timing_partner_id INTEGER
);

CREATE TABLE IF NOT EXISTS raceroster_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id INTEGER,
    registration_id INTEGER,
    bib_number TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    date_of_birth TEXT,
    gender TEXT,
    address_line1 TEXT,
    address_line2 TEXT,
    city TEXT,
    state TEXT,
    postal_code TEXT,
    country TEXT,
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    team_name TEXT,
    division TEXT,
    registration_date TEXT,
    registration_status TEXT,
    payment_status TEXT,
    amount_paid TEXT,
    shirt_size TEXT,
    dietary_restrictions TEXT,
    medical_conditions TEXT,
    fetched_date TEXT,
    credentials_used TEXT,
    timing_partner_id INTEGER
);

-- Add Copernico tables (for results/scoring)
CREATE TABLE IF NOT EXISTS copernico_events (
    event_id TEXT PRIMARY KEY,
    competition_id TEXT,
    event_name TEXT,
    event_description TEXT,
    event_date TEXT,
    location TEXT,
    discipline TEXT,
    gender_categories TEXT,
    age_categories TEXT,
    distance_categories TEXT,
    status TEXT,
    created_at TEXT,
    updated_at TEXT,
    fetched_date TEXT,
    credentials_used TEXT,
    timing_partner_id INTEGER
);

CREATE TABLE IF NOT EXISTS copernico_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    participant_id TEXT,
    bib_number TEXT,
    first_name TEXT,
    last_name TEXT,
    date_of_birth TEXT,
    gender TEXT,
    nationality TEXT,
    club_team TEXT,
    category TEXT,
    license_number TEXT,
    registration_status TEXT,
    created_at TEXT,
    updated_at TEXT,
    fetched_date TEXT,
    credentials_used TEXT,
    timing_partner_id INTEGER
);

CREATE TABLE IF NOT EXISTS copernico_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    participant_id TEXT,
    bib_number TEXT,
    first_name TEXT,
    last_name TEXT,
    category TEXT,
    start_time TEXT,
    finish_time TEXT,
    total_time TEXT,
    split_times TEXT, -- JSON string of split times
    overall_position INTEGER,
    category_position INTEGER,
    status TEXT, -- finished, dns, dnf, dq
    created_at TEXT,
    updated_at TEXT,
    fetched_date TEXT,
    credentials_used TEXT,
    timing_partner_id INTEGER
);

-- Complete Haku integration (extend existing timing_partner_haku_orgs)
CREATE TABLE IF NOT EXISTS haku_events (
    event_id TEXT PRIMARY KEY,
    organization_id TEXT,
    event_name TEXT,
    event_description TEXT,
    start_date TEXT,
    end_date TEXT,
    location TEXT,
    event_type TEXT,
    distance TEXT,
    registration_limit INTEGER,
    registration_count INTEGER,
    registration_fee TEXT,
    currency TEXT,
    status TEXT,
    created_at TEXT,
    updated_at TEXT,
    fetched_date TEXT,
    credentials_used TEXT,
    timing_partner_id INTEGER
);

CREATE TABLE IF NOT EXISTS haku_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT,
    participant_id TEXT,
    bib_number TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    date_of_birth TEXT,
    gender TEXT,
    nationality TEXT,
    emergency_contact TEXT,
    team_affiliation TEXT,
    category TEXT,
    registration_date TEXT,
    payment_status TEXT,
    amount_paid TEXT,
    special_requirements TEXT,
    fetched_date TEXT,
    credentials_used TEXT,
    timing_partner_id INTEGER
);

-- ========================================================================
-- SECTION 2: NOTES ON EXISTING INTEGRATIONS
-- ========================================================================

-- CTLive = ChronoTrack (existing ct_* tables cover this)
-- Haku partially implemented (timing_partner_haku_orgs exists)
-- Focus on Race Roster and Copernico as new integrations

-- ========================================================================
-- SECTION 3: ENHANCE EXISTING SYNC INFRASTRUCTURE
-- ========================================================================

-- Add more detailed sync tracking
ALTER TABLE sync_queue ADD COLUMN provider_name TEXT;
ALTER TABLE sync_queue ADD COLUMN operation_type TEXT; -- 'participants', 'results', 'events'
ALTER TABLE sync_queue ADD COLUMN sync_direction TEXT; -- 'pull', 'push', 'bidirectional'
ALTER TABLE sync_queue ADD COLUMN priority INTEGER DEFAULT 5;
ALTER TABLE sync_queue ADD COLUMN scheduled_time TEXT;

ALTER TABLE sync_history ADD COLUMN provider_name TEXT;
ALTER TABLE sync_history ADD COLUMN operation_type TEXT;
ALTER TABLE sync_history ADD COLUMN sync_direction TEXT;
ALTER TABLE sync_history ADD COLUMN error_details TEXT;
ALTER TABLE sync_history ADD COLUMN data_snapshot TEXT; -- JSON snapshot of synced data

-- Add new provider entries (if not already present)
INSERT OR IGNORE INTO providers (provider_id, name) VALUES 
    (4, 'Race Roster'),
    (5, 'Haku'),  
    (6, 'Copernico');

-- ========================================================================
-- SECTION 4: ENHANCE EVENTS TABLE FOR BETTER PROVIDER SUPPORT
-- ========================================================================

-- Add columns to main events table for new providers
ALTER TABLE events ADD COLUMN raceroster_event_id TEXT;
ALTER TABLE events ADD COLUMN copernico_event_id TEXT;
ALTER TABLE events ADD COLUMN haku_event_id TEXT;

-- Add sync settings for each provider connection
ALTER TABLE events ADD COLUMN sync_settings TEXT; -- JSON config for sync behavior
ALTER TABLE events ADD COLUMN last_sync_timestamps TEXT; -- JSON of last sync times per provider

-- ========================================================================
-- SECTION 5: CREATE UNIFIED VIEWS FOR CROSS-PROVIDER QUERIES
-- ========================================================================

-- Unified participants view across all providers
CREATE VIEW IF NOT EXISTS unified_participants AS
SELECT 
    'runsignup' as source_provider,
    timing_partner_id,
    event_id,
    first_name,
    last_name,
    email,
    gender,
    bib_num as bib_number,
    city,
    state,
    age,
    registration_date
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
    city,
    state,
    NULL as age,
    registration_date
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
    registration_date
FROM haku_participants

UNION ALL

SELECT 
    'copernico' as source_provider,
    timing_partner_id,
    NULL as event_id,
    first_name,
    last_name,
    NULL as email,
    gender,
    bib_number,
    NULL as city,
    NULL as state,
    NULL as age,
    NULL as registration_date
FROM copernico_participants;

-- Unified events view across all providers  
CREATE VIEW IF NOT EXISTS unified_events AS
SELECT 
    'runsignup' as source_provider,
    timing_partner_id,
    event_id,
    name as event_name,
    start_time as event_date,
    city,
    state,
    distance,
    fetched_date
FROM runsignup_events

UNION ALL

SELECT 
    'raceroster' as source_provider,
    timing_partner_id,
    event_id,
    name as event_name,
    start_date as event_date,
    city,
    state,
    distance,
    fetched_date
FROM raceroster_events

UNION ALL

SELECT 
    'haku' as source_provider,
    timing_partner_id,
    event_id,
    event_name,
    start_date as event_date,
    NULL as city,
    NULL as state,
    distance,
    fetched_date
FROM haku_events

UNION ALL

SELECT 
    'copernico' as source_provider,
    timing_partner_id,
    event_id,
    event_name,
    event_date,
    location as city,
    NULL as state,
    NULL as distance,
    fetched_date
FROM copernico_events;

-- Unified results view
CREATE VIEW IF NOT EXISTS unified_results AS
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
    results_rank as overall_place
FROM ct_results

UNION ALL

SELECT 
    'copernico' as source_provider,
    timing_partner_id,
    event_id,
    bib_number,
    first_name,
    last_name,
    NULL as gender,
    NULL as age,
    total_time as results_time,
    NULL as results_gun_time,
    overall_position as overall_place
FROM copernico_results;

-- ========================================================================
-- SECTION 6: CREATE INDEXES FOR PERFORMANCE
-- ========================================================================

-- Race Roster indexes
CREATE INDEX IF NOT EXISTS idx_raceroster_events_timing_partner ON raceroster_events(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_raceroster_participants_event ON raceroster_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_raceroster_participants_timing_partner ON raceroster_participants(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_raceroster_participants_bib ON raceroster_participants(bib_number);

-- Copernico indexes
CREATE INDEX IF NOT EXISTS idx_copernico_events_timing_partner ON copernico_events(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_copernico_participants_event ON copernico_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_copernico_participants_timing_partner ON copernico_participants(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_copernico_results_event ON copernico_results(event_id);
CREATE INDEX IF NOT EXISTS idx_copernico_results_timing_partner ON copernico_results(timing_partner_id);

-- Haku indexes
CREATE INDEX IF NOT EXISTS idx_haku_events_timing_partner ON haku_events(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_haku_participants_event ON haku_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_haku_participants_timing_partner ON haku_participants(timing_partner_id);

-- Note: CTLive indexes not needed (CTLive = ChronoTrack, using existing ct_* indexes)

-- Enhanced sync indexes
CREATE INDEX IF NOT EXISTS idx_sync_queue_provider ON sync_queue(provider_name, status);
CREATE INDEX IF NOT EXISTS idx_sync_queue_scheduled ON sync_queue(scheduled_time) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_sync_history_provider ON sync_history(provider_name, sync_time);

-- ========================================================================
-- END OF ENHANCEMENT SCRIPT
-- ======================================================================== 