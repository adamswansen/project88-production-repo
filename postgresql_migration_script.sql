-- ========================================================================
-- PROJECT88HUB POSTGRESQL MIGRATION SCRIPT
-- Migrate SQLite race_results.db to PostgreSQL project88_myappdb
-- Database: PostgreSQL 13+
-- ========================================================================

-- Connect to the correct database
\c project88_myappdb;

-- ========================================================================
-- SECTION 1: BACKUP AND PREPARATION
-- ========================================================================

-- Create backup schema for existing data
CREATE SCHEMA IF NOT EXISTS backup_migration;

-- Backup existing tables if they exist
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'timing_partners') THEN
        EXECUTE 'CREATE TABLE backup_migration.timing_partners_backup AS SELECT * FROM timing_partners';
    END IF;
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users') THEN
        EXECUTE 'CREATE TABLE backup_migration.users_backup AS SELECT * FROM users';
    END IF;
END $$;

-- ========================================================================
-- SECTION 2: CORE INFRASTRUCTURE TABLES
-- ========================================================================

-- Timing Partners (may already exist - merge carefully)
CREATE TABLE IF NOT EXISTS timing_partners (
    timing_partner_id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    access_password VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Users (may already exist - merge carefully)  
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Providers table
CREATE TABLE IF NOT EXISTS providers (
    provider_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    provider_type VARCHAR(50), -- 'registration', 'scoring', 'timing'
    api_base_url VARCHAR(255),
    rate_limit_per_hour INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert provider data
INSERT INTO providers (name, provider_type, api_base_url, rate_limit_per_hour) VALUES 
    ('RunSignUp', 'registration', 'https://runsignup.com/REST', 1000),
    ('ChronoTrack', 'timing', 'https://api.chronotrack.com', 2000),
    ('Race Roster', 'registration', 'https://raceroster.com/api/v1', 1000),
    ('Haku', 'registration', 'https://api.hakuapp.com/v1', 500),
    ('Copernico', 'scoring', 'https://development.timingsense.cloud', 2000)
ON CONFLICT (name) DO NOTHING;

-- Provider credentials
CREATE TABLE IF NOT EXISTS partner_provider_credentials (
    partner_provider_credential_id SERIAL PRIMARY KEY,
    provider_id INTEGER REFERENCES providers(provider_id) ON DELETE CASCADE,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    principal VARCHAR(255), -- username, client_id, api_key
    secret VARCHAR(255),    -- password, client_secret, api_secret
    credential_type VARCHAR(50), -- 'oauth', 'api_key', 'basic_auth'
    additional_config JSONB, -- Store provider-specific config
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(timing_partner_id, provider_id)
);

-- ========================================================================
-- SECTION 3: SYNC INFRASTRUCTURE TABLES
-- ========================================================================

-- Enhanced sync queue
CREATE TABLE IF NOT EXISTS sync_queue (
    sync_queue_id SERIAL PRIMARY KEY,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id),
    provider_id INTEGER REFERENCES providers(provider_id),
    event_id VARCHAR(100),
    operation_type VARCHAR(50) NOT NULL, -- 'events', 'participants', 'results'
    sync_direction VARCHAR(50) DEFAULT 'pull', -- 'pull', 'push', 'bidirectional'
    priority INTEGER DEFAULT 5, -- 1=highest, 10=lowest
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    scheduled_time TIMESTAMP DEFAULT NOW(),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    payload JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Enhanced sync history
CREATE TABLE IF NOT EXISTS sync_history (
    sync_history_id SERIAL PRIMARY KEY,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    provider_id INTEGER REFERENCES providers(provider_id),
    event_id VARCHAR(100),
    operation_type VARCHAR(50),
    sync_direction VARCHAR(50),
    sync_time TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20), -- 'success', 'failed', 'partial'
    num_of_synced_records INTEGER DEFAULT 0,
    entries_success INTEGER DEFAULT 0,
    entries_failed INTEGER DEFAULT 0,
    error_details JSONB,
    data_snapshot JSONB, -- Summary of synced data
    duration_seconds INTEGER,
    callback_url VARCHAR(255),
    reason TEXT
);

-- ========================================================================
-- SECTION 4: RUNSIGNUP TABLES (PostgreSQL-optimized)
-- ========================================================================

-- RunSignUp Races
CREATE TABLE IF NOT EXISTS runsignup_races (
    race_id INTEGER PRIMARY KEY,
    name TEXT,
    last_date TIMESTAMP,
    last_end_date TIMESTAMP,
    next_date TIMESTAMP,
    next_end_date TIMESTAMP,
    is_draft_race BOOLEAN,
    is_private_race BOOLEAN,
    is_registration_open BOOLEAN,
    created TIMESTAMP,
    last_modified TIMESTAMP,
    description TEXT,
    url VARCHAR(255),
    external_race_url VARCHAR(255),
    external_results_url VARCHAR(255),
    fb_page_id VARCHAR(50),
    fb_event_id VARCHAR(50),
    address JSONB, -- Store address as JSON
    timezone VARCHAR(50),
    logo_url VARCHAR(255),
    real_time_notifications_enabled BOOLEAN,
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- RunSignUp Events  
CREATE TABLE IF NOT EXISTS runsignup_events (
    event_id INTEGER PRIMARY KEY,
    race_id INTEGER REFERENCES runsignup_races(race_id) ON DELETE CASCADE,
    name TEXT,
    details TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    age_calc_base_date DATE,
    registration_opens TIMESTAMP,
    event_type VARCHAR(50),
    distance DECIMAL(10,2),
    volunteer BOOLEAN,
    require_dob BOOLEAN,
    require_phone BOOLEAN,
    giveaway TEXT,
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- RunSignUp Participants
CREATE TABLE IF NOT EXISTS runsignup_participants (
    id SERIAL PRIMARY KEY,
    race_id INTEGER REFERENCES runsignup_races(race_id) ON DELETE CASCADE,
    event_id INTEGER REFERENCES runsignup_events(event_id) ON DELETE CASCADE,
    registration_id INTEGER,
    user_id INTEGER,
    first_name VARCHAR(100),
    middle_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    address JSONB, -- Store address as JSON
    dob DATE,
    gender VARCHAR(20),
    phone VARCHAR(20),
    profile_image_url VARCHAR(255),
    bib_num VARCHAR(20),
    chip_num VARCHAR(20),
    age INTEGER,
    registration_date TIMESTAMP,
    team_info JSONB, -- Store team data as JSON
    payment_info JSONB, -- Store payment data as JSON
    additional_data JSONB, -- Store misc data as JSON
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ========================================================================
-- SECTION 5: CHRONOTRACK TABLES (PostgreSQL-optimized)
-- ========================================================================

-- ChronoTrack Events
CREATE TABLE IF NOT EXISTS ct_events (
    event_id VARCHAR(100) PRIMARY KEY,
    event_tag VARCHAR(50),
    event_name VARCHAR(255),
    event_description TEXT,
    event_start_time TIMESTAMP,
    event_end_time TIMESTAMP,
    event_site_uri VARCHAR(255),
    event_is_published BOOLEAN,
    event_device_protocol VARCHAR(50),
    event_external_id VARCHAR(100),
    organization_id VARCHAR(100),
    organization_name VARCHAR(255),
    location JSONB, -- Store location data as JSON
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ChronoTrack Races
CREATE TABLE IF NOT EXISTS ct_races (
    race_id VARCHAR(100),
    event_id VARCHAR(100) REFERENCES ct_events(event_id) ON DELETE CASCADE,
    race_tag VARCHAR(50),
    race_name VARCHAR(255),
    race_type VARCHAR(50),
    race_subtype VARCHAR(50),
    race_course_distance DECIMAL(10,2),
    race_pref_distance_unit VARCHAR(20),
    race_planned_start_time TIMESTAMP,
    race_planned_end_time TIMESTAMP,
    race_actual_start_time TIMESTAMP,
    race_actual_end_time TIMESTAMP,
    race_age_ref_time TIMESTAMP,
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (race_id, event_id)
);

-- ChronoTrack Participants
CREATE TABLE IF NOT EXISTS ct_participants (
    entry_id VARCHAR(100) PRIMARY KEY,
    event_id VARCHAR(100) REFERENCES ct_events(event_id) ON DELETE CASCADE,
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
    athlete_sex VARCHAR(10),
    athlete_birthdate DATE,
    athlete_email VARCHAR(255),
    athlete_home_phone VARCHAR(20),
    athlete_mobile_phone VARCHAR(20),
    location JSONB, -- Store location as JSON
    team_id VARCHAR(100),
    team_name VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255)
);

-- ChronoTrack Results
CREATE TABLE IF NOT EXISTS ct_results (
    id SERIAL PRIMARY KEY,
    event_id VARCHAR(100) REFERENCES ct_events(event_id) ON DELETE CASCADE,
    race_id VARCHAR(100),
    entry_id VARCHAR(100),
    results_bib VARCHAR(20),
    results_first_name VARCHAR(100),
    results_last_name VARCHAR(100),
    results_sex VARCHAR(10),
    results_age INTEGER,
    results_hometown VARCHAR(100),
    results_state_code VARCHAR(10),
    results_postal_code VARCHAR(20),
    results_country_code VARCHAR(10),
    results_time INTERVAL,
    results_gun_time INTERVAL,
    results_pace INTERVAL,
    results_gun_pace INTERVAL,
    results_rank INTEGER,
    results_bracket_name VARCHAR(100),
    results_primary_bracket_name VARCHAR(100),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255)
);

-- ========================================================================
-- SECTION 6: NEW PROVIDER TABLES
-- ========================================================================

-- Race Roster Events
CREATE TABLE IF NOT EXISTS raceroster_events (
    event_id INTEGER PRIMARY KEY,
    race_id INTEGER,
    name VARCHAR(255),
    description TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    location_name VARCHAR(255),
    address JSONB, -- Store address as JSON
    timezone VARCHAR(50),
    distance DECIMAL(10,2),
    event_type VARCHAR(50),
    registration_open_date TIMESTAMP,
    registration_close_date TIMESTAMP,
    max_participants INTEGER,
    current_participants INTEGER,
    price DECIMAL(10,2),
    currency VARCHAR(10),
    status VARCHAR(50),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Race Roster Participants
CREATE TABLE IF NOT EXISTS raceroster_participants (
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
    address JSONB, -- Store address as JSON
    emergency_contact JSONB, -- Store emergency contact as JSON
    team_name VARCHAR(255),
    division VARCHAR(100),
    registration_date TIMESTAMP,
    registration_status VARCHAR(50),
    payment_status VARCHAR(50),
    amount_paid DECIMAL(10,2),
    additional_info JSONB, -- Store shirt size, dietary restrictions, etc.
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Copernico Events
CREATE TABLE IF NOT EXISTS copernico_events (
    event_id VARCHAR(100) PRIMARY KEY,
    competition_id VARCHAR(100),
    event_name VARCHAR(255),
    event_description TEXT,
    event_date TIMESTAMP,
    location VARCHAR(255),
    discipline VARCHAR(100),
    categories JSONB, -- Store gender, age, distance categories as JSON
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE
);

-- Copernico Participants
CREATE TABLE IF NOT EXISTS copernico_participants (
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
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE
);

-- Copernico Results
CREATE TABLE IF NOT EXISTS copernico_results (
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
    split_times JSONB, -- Store split times as JSON array
    overall_position INTEGER,
    category_position INTEGER,
    status VARCHAR(20), -- finished, dns, dnf, dq
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE
);

-- Haku Events
CREATE TABLE IF NOT EXISTS haku_events (
    event_id VARCHAR(100) PRIMARY KEY,
    organization_id VARCHAR(100),
    event_name VARCHAR(255),
    event_description TEXT,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    location VARCHAR(255),
    event_type VARCHAR(50),
    distance DECIMAL(10,2),
    registration_limit INTEGER,
    registration_count INTEGER,
    registration_fee DECIMAL(10,2),
    currency VARCHAR(10),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE
);

-- Haku Participants
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
    category VARCHAR(100),
    registration_date TIMESTAMP,
    payment_status VARCHAR(50),
    amount_paid DECIMAL(10,2),
    special_requirements TEXT,
    fetched_date TIMESTAMP DEFAULT NOW(),
    credentials_used VARCHAR(255),
    timing_partner_id INTEGER REFERENCES timing_partners(timing_partner_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ========================================================================
-- SECTION 7: UNIFIED VIEWS
-- ========================================================================

-- Unified participants view across all providers
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
    event_id::VARCHAR,
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
    NULL as email,
    gender,
    bib_number,
    NULL as city,
    NULL as state,
    NULL as age,
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

-- Unified events view across all providers  
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
    event_id::VARCHAR,
    name as event_name,
    start_date as event_date,
    (address->>'city') as city,
    (address->>'state') as state,
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
    location as city,
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
FROM copernico_events

UNION ALL

SELECT
    'chronotrack' as source_provider,
    timing_partner_id,
    event_id,
    event_name,
    event_start_time as event_date,
    (location->>'city') as city,
    (location->>'region') as state,
    NULL as distance,
    created_at as fetched_date
FROM ct_events;

-- Unified results view
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
    created_at
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
    NULL as age,
    total_time as results_time,
    NULL as results_gun_time,
    overall_position as overall_place,
    created_at
FROM copernico_results;

-- ========================================================================
-- SECTION 8: PERFORMANCE INDEXES
-- ========================================================================

-- Core table indexes
CREATE INDEX IF NOT EXISTS idx_timing_partners_company ON timing_partners(company_name);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_timing_partner ON users(timing_partner_id);

-- Provider credentials indexes
CREATE INDEX IF NOT EXISTS idx_credentials_timing_partner ON partner_provider_credentials(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_credentials_provider ON partner_provider_credentials(provider_id);

-- Sync infrastructure indexes
CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(status);
CREATE INDEX IF NOT EXISTS idx_sync_queue_scheduled ON sync_queue(scheduled_time) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_sync_queue_timing_partner ON sync_queue(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_timing_partner ON sync_history(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_sync_history_sync_time ON sync_history(sync_time DESC);

-- RunSignUp indexes
CREATE INDEX IF NOT EXISTS idx_runsignup_events_timing_partner ON runsignup_events(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_runsignup_events_start_time ON runsignup_events(start_time);
CREATE INDEX IF NOT EXISTS idx_runsignup_participants_event ON runsignup_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_runsignup_participants_timing_partner ON runsignup_participants(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_runsignup_participants_bib ON runsignup_participants(bib_num);
CREATE INDEX IF NOT EXISTS idx_runsignup_participants_email ON runsignup_participants(email);

-- ChronoTrack indexes
CREATE INDEX IF NOT EXISTS idx_ct_events_timing_partner ON ct_events(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_ct_events_start_time ON ct_events(event_start_time);
CREATE INDEX IF NOT EXISTS idx_ct_participants_event ON ct_participants(event_id);
CREATE INDEX IF NOT EXISTS idx_ct_participants_timing_partner ON ct_participants(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_ct_participants_bib ON ct_participants(entry_bib);
CREATE INDEX IF NOT EXISTS idx_ct_results_event ON ct_results(event_id);
CREATE INDEX IF NOT EXISTS idx_ct_results_timing_partner ON ct_results(timing_partner_id);
CREATE INDEX IF NOT EXISTS idx_ct_results_bib ON ct_results(results_bib);

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

-- ========================================================================
-- SECTION 9: TRIGGERS AND FUNCTIONS
-- ========================================================================

-- Function to automatically update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at columns
CREATE TRIGGER update_timing_partners_updated_at 
    BEFORE UPDATE ON timing_partners 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_partner_provider_credentials_updated_at 
    BEFORE UPDATE ON partner_provider_credentials 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================================================
-- SECTION 10: PERMISSIONS
-- ========================================================================

-- Grant permissions to existing application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO project88_myappuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO project88_myappuser;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO project88_myappuser;

-- ========================================================================
-- SECTION 11: VERIFICATION QUERIES
-- ========================================================================

-- Show table counts after migration
SELECT 
    'timing_partners' as table_name, COUNT(*) as row_count FROM timing_partners
UNION ALL
SELECT 
    'providers' as table_name, COUNT(*) as row_count FROM providers
UNION ALL
SELECT 
    'runsignup_events' as table_name, COUNT(*) as row_count FROM runsignup_events
UNION ALL
SELECT 
    'ct_events' as table_name, COUNT(*) as row_count FROM ct_events
ORDER BY table_name;

-- ========================================================================
-- END OF MIGRATION SCRIPT
-- ======================================================================== 