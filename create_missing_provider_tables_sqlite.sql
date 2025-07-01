-- ========================================================================
-- PROJECT88HUB - MISSING PROVIDER TABLES CREATION SCRIPT (SQLite Version)
-- Execute this on your SQLite database to add missing provider integrations
-- ========================================================================

-- ========================================================================
-- RACE ROSTER INTEGRATION TABLES
-- ========================================================================

CREATE TABLE IF NOT EXISTS raceroster_events (
    event_id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    start_date TEXT, -- SQLite uses TEXT for timestamps
    end_date TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    distance REAL,
    max_participants INTEGER,
    registration_open_date TEXT,
    registration_close_date TEXT,
    event_type TEXT,
    currency TEXT,
    registration_fee REAL,
    event_status TEXT DEFAULT 'active',
    fetched_date TEXT DEFAULT (datetime('now')),
    credentials_used TEXT,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS raceroster_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT REFERENCES raceroster_events(event_id) ON DELETE CASCADE,
    participant_id TEXT,
    bib_number TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    date_of_birth TEXT,
    gender TEXT,
    address TEXT, -- JSON stored as TEXT in SQLite
    emergency_contact TEXT, -- JSON stored as TEXT
    team_name TEXT,
    division TEXT,
    registration_date TEXT,
    payment_status TEXT,
    amount_paid REAL,
    special_requirements TEXT,
    fetched_date TEXT DEFAULT (datetime('now')),
    credentials_used TEXT,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ========================================================================
-- COPERNICO INTEGRATION TABLES  
-- ========================================================================

CREATE TABLE IF NOT EXISTS copernico_events (
    event_id TEXT PRIMARY KEY,
    event_name TEXT,
    event_description TEXT,
    event_date TEXT,
    location TEXT,
    event_type TEXT,
    distance_km REAL,
    max_participants INTEGER,
    event_status TEXT DEFAULT 'active',
    organization_id TEXT,
    fetched_date TEXT DEFAULT (datetime('now')),
    credentials_used TEXT,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS copernico_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT REFERENCES copernico_events(event_id) ON DELETE CASCADE,
    participant_id TEXT,
    bib_number TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    gender TEXT,
    age INTEGER,
    category TEXT,
    team_name TEXT,
    registration_status TEXT DEFAULT 'registered',
    fetched_date TEXT DEFAULT (datetime('now')),
    credentials_used TEXT,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS copernico_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT REFERENCES copernico_events(event_id) ON DELETE CASCADE,
    participant_id TEXT,
    bib_number TEXT,
    overall_place INTEGER,
    gender_place INTEGER,
    division_place INTEGER,
    start_time TEXT,
    finish_time TEXT,
    total_time TEXT,
    split_times TEXT, -- JSON stored as TEXT
    result_status TEXT DEFAULT 'finished', -- finished, dns, dnf, dq
    fetched_date TEXT DEFAULT (datetime('now')),
    credentials_used TEXT,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now'))
);

-- ========================================================================
-- COMPLETE HAKU INTEGRATION (extend existing foundation)
-- ========================================================================

CREATE TABLE IF NOT EXISTS haku_events (
    event_id TEXT PRIMARY KEY,
    organization_id TEXT,
    event_name TEXT,
    event_description TEXT,
    start_date TEXT,
    end_date TEXT,
    location TEXT,
    event_type TEXT,
    distance TEXT, -- Haku uses string format
    registration_limit INTEGER,
    registration_count INTEGER,
    registration_fee REAL,
    currency TEXT,
    event_status TEXT DEFAULT 'active',
    fetched_date TEXT DEFAULT (datetime('now')),
    credentials_used TEXT,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS haku_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT REFERENCES haku_events(event_id) ON DELETE CASCADE,
    participant_id TEXT,
    bib_number TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    date_of_birth TEXT,
    gender TEXT,
    nationality TEXT,
    emergency_contact TEXT, -- JSON stored as TEXT
    team_affiliation TEXT,
    category TEXT,
    registration_date TEXT,
    payment_status TEXT,
    amount_paid REAL,
    special_requirements TEXT,
    fetched_date TEXT DEFAULT (datetime('now')),
    credentials_used TEXT,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TEXT DEFAULT (datetime('now'))
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

-- Drop existing views to recreate them
DROP VIEW IF EXISTS unified_participants;
DROP VIEW IF EXISTS unified_events;
DROP VIEW IF EXISTS unified_results;

-- Create updated unified_participants view to include all providers
CREATE VIEW unified_participants AS
SELECT 
    'runsignup' as source_provider,
    timing_partner_id,
    CAST(event_id AS TEXT) as event_id,
    first_name,
    last_name,
    email,
    gender,
    bib_num as bib_number,
    city,
    state,
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
    json_extract(address, '$.city') as city,
    json_extract(address, '$.state') as state,
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
    NULL as city, -- JSON parsing would be needed for ChronoTrack location
    NULL as state,
    entry_race_age as age,
    NULL as registration_date,
    created_at as fetched_date
FROM ct_participants;

-- Create updated unified_events view to include all providers
CREATE VIEW unified_events AS
SELECT 
    'runsignup' as source_provider,
    timing_partner_id,
    CAST(event_id AS TEXT) as event_id,
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
CREATE VIEW unified_results AS
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
    total_time as results_time,
    total_time as results_gun_time,
    overall_place,
    fetched_date
FROM copernico_results; 