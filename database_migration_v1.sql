-- ========================================================================
-- PROJECT88HUB DATABASE MIGRATION V1.0
-- Provider Integration & Data Normalization Enhancement
-- Target Database: project88_myappdb (extend existing)
-- ========================================================================

-- ========================================================================
-- SECTION 1: PROVIDER CONNECTION MANAGEMENT
-- ========================================================================

-- Provider connections table - manages timing partner integrations
CREATE TABLE provider_connections (
    id SERIAL PRIMARY KEY,
    timing_partner_id INTEGER REFERENCES timing_partners(id) ON DELETE CASCADE,
    source_provider_id INTEGER REFERENCES providers(id),      -- Registration provider
    target_provider_id INTEGER REFERENCES providers(id),      -- Scoring provider  
    connection_name VARCHAR(255) NOT NULL,
    connection_type VARCHAR(50) DEFAULT 'registration_to_scoring',
    sync_frequency INTERVAL DEFAULT '4 hours',                -- Scheduled sync frequency
    auto_sync_enabled BOOLEAN DEFAULT true,
    last_sync_at TIMESTAMP,
    next_sync_at TIMESTAMP,
    sync_status VARCHAR(20) DEFAULT 'active',                 -- active, paused, error
    mapping_config JSONB,                                     -- Field mappings and transformations
    sync_settings JSONB,                                      -- Sync-specific settings
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id),
    UNIQUE(timing_partner_id, source_provider_id, target_provider_id, connection_name)
);

-- Enhanced provider table if needed (may already exist)
INSERT INTO providers (provider_name, provider_type, api_base_url, rate_limit_per_hour) VALUES
    ('Race Roster', 'registration', 'https://raceroster.com/api/v1', 1000),
    ('Haku', 'registration', 'https://api.hakuapp.com/v1', 500),
    ('Copernico', 'scoring', 'https://development.timingsense.cloud', 2000),
    ('CTLive', 'scoring', 'https://api.chronotrack.com', 1000)
ON CONFLICT (provider_name) DO NOTHING;

-- ========================================================================
-- SECTION 2: NORMALIZED DATA SCHEMA
-- ========================================================================

-- Normalized events table - cross-provider event data
CREATE TABLE normalized_events (
    id SERIAL PRIMARY KEY,
    timing_partner_id INTEGER REFERENCES timing_partners(id) ON DELETE CASCADE,
    source_provider VARCHAR(50) NOT NULL,
    source_event_id VARCHAR(100) NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    event_date DATE,
    event_type VARCHAR(50),                                    -- marathon, 5k, triathlon, etc.
    location_city VARCHAR(100),
    location_state VARCHAR(50),
    location_country VARCHAR(50),
    race_distance REAL,                                        -- in kilometers
    max_participants INTEGER,
    registration_open_date DATE,
    registration_close_date DATE,
    event_status VARCHAR(20) DEFAULT 'active',                 -- active, cancelled, completed
    normalized_data JSONB,                                     -- Full provider data
    hash_key VARCHAR(64),                                      -- For duplicate detection
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    synced_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(timing_partner_id, source_provider, source_event_id)
);

-- Normalized participants table - cross-provider participant data
CREATE TABLE normalized_participants (
    id SERIAL PRIMARY KEY,
    normalized_event_id INTEGER REFERENCES normalized_events(id) ON DELETE CASCADE,
    timing_partner_id INTEGER REFERENCES timing_partners(id) ON DELETE CASCADE,
    source_provider VARCHAR(50) NOT NULL,
    source_participant_id VARCHAR(100) NOT NULL,
    global_participant_id UUID DEFAULT gen_random_uuid(),     -- Track across events/systems
    bib_number VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    date_of_birth DATE,
    gender VARCHAR(10),
    age INTEGER,
    city VARCHAR(100),
    state VARCHAR(50),
    country VARCHAR(50),
    emergency_contact JSONB,
    race_distance REAL,
    division VARCHAR(50),
    team_name VARCHAR(100),
    registration_date DATE,
    participant_status VARCHAR(20) DEFAULT 'registered',       -- registered, checked_in, dns, dnf
    normalized_data JSONB,                                     -- Full provider data
    hash_key VARCHAR(64),                                      -- For duplicate detection
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    synced_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(normalized_event_id, source_provider, source_participant_id)
);

-- Normalized results table - cross-provider results data  
CREATE TABLE normalized_results (
    id SERIAL PRIMARY KEY,
    normalized_event_id INTEGER REFERENCES normalized_events(id) ON DELETE CASCADE,
    normalized_participant_id INTEGER REFERENCES normalized_participants(id) ON DELETE CASCADE,
    timing_partner_id INTEGER REFERENCES timing_partners(id) ON DELETE CASCADE,
    source_provider VARCHAR(50) NOT NULL,
    source_result_id VARCHAR(100),
    bib_number VARCHAR(20),
    overall_place INTEGER,
    gender_place INTEGER,
    division_place INTEGER,
    start_time TIMESTAMP,
    finish_time TIMESTAMP,
    total_time INTERVAL,
    chip_time INTERVAL,
    split_times JSONB,                                         -- Array of split times
    result_status VARCHAR(20) DEFAULT 'finished',              -- finished, dns, dnf, dq
    normalized_data JSONB,                                     -- Full provider data
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    synced_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(normalized_event_id, source_provider, bib_number)
);

-- ========================================================================
-- SECTION 3: SYNC OPERATIONS MANAGEMENT
-- ========================================================================

-- Sync operations tracking table
CREATE TABLE sync_operations (
    id SERIAL PRIMARY KEY,
    connection_id INTEGER REFERENCES provider_connections(id) ON DELETE CASCADE,
    operation_type VARCHAR(50) NOT NULL,                      -- event_sync, participant_sync, results_sync
    sync_direction VARCHAR(50) NOT NULL,                      -- registration_to_scoring, scoring_to_registration
    trigger_type VARCHAR(20) DEFAULT 'scheduled',             -- scheduled, manual, webhook
    status VARCHAR(20) DEFAULT 'pending',                     -- pending, running, completed, failed, cancelled
    
    -- Progress tracking
    total_records INTEGER DEFAULT 0,
    processed_records INTEGER DEFAULT 0,
    success_records INTEGER DEFAULT 0,
    error_records INTEGER DEFAULT 0,
    
    -- Data details
    source_event_id VARCHAR(100),
    target_event_id VARCHAR(100),
    sync_payload JSONB,                                       -- Request/response data
    error_details JSONB,                                      -- Error messages and details
    
    -- Timing
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Metadata
    started_by INTEGER REFERENCES users(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Enhanced sync queue table (may need to update existing)
CREATE TABLE IF NOT EXISTS enhanced_sync_queue (
    id SERIAL PRIMARY KEY,
    connection_id INTEGER REFERENCES provider_connections(id),
    operation_type VARCHAR(50) NOT NULL,
    priority INTEGER DEFAULT 5,                               -- 1=highest, 10=lowest
    scheduled_for TIMESTAMP DEFAULT NOW(),
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    payload JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

-- ========================================================================
-- SECTION 4: PARTICIPANT CROSS-SYSTEM TRACKING
-- ========================================================================

-- Global participant tracking - link participants across systems
CREATE TABLE global_participants (
    id SERIAL PRIMARY KEY,
    global_participant_id UUID DEFAULT gen_random_uuid(),
    primary_email VARCHAR(255),
    primary_first_name VARCHAR(100),
    primary_last_name VARCHAR(100),
    confidence_score REAL DEFAULT 1.0,                        -- Matching confidence
    linked_participants JSONB,                                -- Array of linked participant records
    timing_partner_id INTEGER REFERENCES timing_partners(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(timing_partner_id, primary_email)
);

-- ========================================================================
-- SECTION 5: RACE DISPLAY INTEGRATION
-- ========================================================================

-- Enhanced timing sessions for race display integration
CREATE TABLE enhanced_timing_sessions (
    id SERIAL PRIMARY KEY,
    timing_partner_id INTEGER REFERENCES timing_partners(id) ON DELETE CASCADE,
    normalized_event_id INTEGER REFERENCES normalized_events(id),
    session_name VARCHAR(255) NOT NULL,
    session_type VARCHAR(50) DEFAULT 'live_timing',           -- live_timing, results_display
    display_mode VARCHAR(20) DEFAULT 'pre-race',              -- pre-race, live, results
    template_config JSONB,                                    -- Display template settings
    participant_data_source VARCHAR(50),                      -- provider name for participant data
    timing_data_source VARCHAR(50) DEFAULT 'chronotrack',     -- source for timing data
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    ended_at TIMESTAMP
);

-- Link timing reads to events
ALTER TABLE timing_reads ADD COLUMN IF NOT EXISTS normalized_event_id INTEGER REFERENCES normalized_events(id);
ALTER TABLE timing_reads ADD COLUMN IF NOT EXISTS timing_partner_id INTEGER REFERENCES timing_partners(id);

-- ========================================================================
-- SECTION 6: PERFORMANCE INDEXES
-- ========================================================================

-- Provider connections indexes
CREATE INDEX idx_provider_connections_timing_partner ON provider_connections(timing_partner_id);
CREATE INDEX idx_provider_connections_source_target ON provider_connections(source_provider_id, target_provider_id);
CREATE INDEX idx_provider_connections_sync_status ON provider_connections(sync_status);
CREATE INDEX idx_provider_connections_next_sync ON provider_connections(next_sync_at) WHERE auto_sync_enabled = true;

-- Normalized data indexes
CREATE INDEX idx_normalized_events_timing_partner ON normalized_events(timing_partner_id);
CREATE INDEX idx_normalized_events_source_provider ON normalized_events(source_provider, source_event_id);
CREATE INDEX idx_normalized_events_date ON normalized_events(event_date DESC);
CREATE INDEX idx_normalized_events_hash ON normalized_events(hash_key);

CREATE INDEX idx_normalized_participants_event ON normalized_participants(normalized_event_id);
CREATE INDEX idx_normalized_participants_timing_partner ON normalized_participants(timing_partner_id);
CREATE INDEX idx_normalized_participants_global_id ON normalized_participants(global_participant_id);
CREATE INDEX idx_normalized_participants_bib ON normalized_participants(bib_number);
CREATE INDEX idx_normalized_participants_email ON normalized_participants(email);
CREATE INDEX idx_normalized_participants_hash ON normalized_participants(hash_key);

CREATE INDEX idx_normalized_results_event ON normalized_results(normalized_event_id);
CREATE INDEX idx_normalized_results_participant ON normalized_results(normalized_participant_id);
CREATE INDEX idx_normalized_results_bib ON normalized_results(bib_number);

-- Sync operations indexes
CREATE INDEX idx_sync_operations_connection ON sync_operations(connection_id);
CREATE INDEX idx_sync_operations_status ON sync_operations(status);
CREATE INDEX idx_sync_operations_type ON sync_operations(operation_type);
CREATE INDEX idx_sync_operations_started_at ON sync_operations(started_at DESC);

-- Enhanced sync queue indexes
CREATE INDEX idx_enhanced_sync_queue_scheduled ON enhanced_sync_queue(scheduled_for) WHERE status = 'pending';
CREATE INDEX idx_enhanced_sync_queue_priority ON enhanced_sync_queue(priority, scheduled_for);

-- Global participants indexes
CREATE INDEX idx_global_participants_timing_partner ON global_participants(timing_partner_id);
CREATE INDEX idx_global_participants_email ON global_participants(primary_email);
CREATE INDEX idx_global_participants_global_id ON global_participants(global_participant_id);

-- Enhanced timing sessions indexes
CREATE INDEX idx_enhanced_timing_sessions_timing_partner ON enhanced_timing_sessions(timing_partner_id);
CREATE INDEX idx_enhanced_timing_sessions_event ON enhanced_timing_sessions(normalized_event_id);
CREATE INDEX idx_enhanced_timing_sessions_status ON enhanced_timing_sessions(status);

-- ========================================================================
-- SECTION 7: VIEWS FOR COMMON QUERIES
-- ========================================================================

-- Unified event view across all providers
CREATE OR REPLACE VIEW unified_events AS
SELECT 
    ne.id as normalized_event_id,
    ne.timing_partner_id,
    tp.name as timing_partner_name,
    ne.source_provider,
    ne.source_event_id,
    ne.event_name,
    ne.event_date,
    ne.event_type,
    ne.location_city,
    ne.location_state,
    ne.race_distance,
    COUNT(np.id) as participant_count,
    COUNT(nr.id) as results_count,
    ne.event_status,
    ne.created_at,
    ne.updated_at,
    ne.synced_at
FROM normalized_events ne
LEFT JOIN timing_partners tp ON ne.timing_partner_id = tp.id
LEFT JOIN normalized_participants np ON ne.id = np.normalized_event_id
LEFT JOIN normalized_results nr ON ne.id = nr.normalized_event_id
GROUP BY ne.id, tp.name
ORDER BY ne.event_date DESC;

-- Sync status summary view
CREATE OR REPLACE VIEW sync_status_summary AS
SELECT 
    pc.id as connection_id,
    pc.connection_name,
    tp.name as timing_partner_name,
    p1.provider_name as source_provider,
    p2.provider_name as target_provider,
    pc.sync_frequency,
    pc.last_sync_at,
    pc.next_sync_at,
    pc.sync_status,
    COUNT(so.id) as total_sync_operations,
    COUNT(CASE WHEN so.status = 'completed' THEN 1 END) as successful_syncs,
    COUNT(CASE WHEN so.status = 'failed' THEN 1 END) as failed_syncs
FROM provider_connections pc
JOIN timing_partners tp ON pc.timing_partner_id = tp.id
JOIN providers p1 ON pc.source_provider_id = p1.id
JOIN providers p2 ON pc.target_provider_id = p2.id
LEFT JOIN sync_operations so ON pc.id = so.connection_id
GROUP BY pc.id, tp.name, p1.provider_name, p2.provider_name;

-- Participant cross-system tracking view
CREATE OR REPLACE VIEW participant_tracking AS
SELECT 
    gp.global_participant_id,
    gp.primary_email,
    gp.primary_first_name,
    gp.primary_last_name,
    tp.name as timing_partner_name,
    COUNT(np.id) as events_participated,
    MIN(ne.event_date) as first_event_date,
    MAX(ne.event_date) as last_event_date,
    STRING_AGG(DISTINCT ne.source_provider, ', ') as providers_used
FROM global_participants gp
JOIN timing_partners tp ON gp.timing_partner_id = tp.id
LEFT JOIN normalized_participants np ON gp.global_participant_id = np.global_participant_id
LEFT JOIN normalized_events ne ON np.normalized_event_id = ne.id
GROUP BY gp.global_participant_id, gp.primary_email, gp.primary_first_name, gp.primary_last_name, tp.name;

-- ========================================================================
-- SECTION 8: TRIGGERS AND FUNCTIONS
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
CREATE TRIGGER update_provider_connections_updated_at 
    BEFORE UPDATE ON provider_connections 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_normalized_events_updated_at 
    BEFORE UPDATE ON normalized_events 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_normalized_participants_updated_at 
    BEFORE UPDATE ON normalized_participants 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_normalized_results_updated_at 
    BEFORE UPDATE ON normalized_results 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_global_participants_updated_at 
    BEFORE UPDATE ON global_participants 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_enhanced_timing_sessions_updated_at 
    BEFORE UPDATE ON enhanced_timing_sessions 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate next sync time
CREATE OR REPLACE FUNCTION calculate_next_sync()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.auto_sync_enabled = true THEN
        NEW.next_sync_at = NOW() + NEW.sync_frequency;
    ELSE
        NEW.next_sync_at = NULL;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger to automatically calculate next sync time
CREATE TRIGGER calculate_next_sync_trigger
    BEFORE INSERT OR UPDATE ON provider_connections
    FOR EACH ROW EXECUTE FUNCTION calculate_next_sync();

-- ========================================================================
-- SECTION 9: DATA MIGRATION HELPERS
-- ========================================================================

-- Function to migrate existing RunSignUp data to normalized tables
CREATE OR REPLACE FUNCTION migrate_runsignup_data(partner_id INTEGER)
RETURNS INTEGER AS $$
DECLARE
    migrated_count INTEGER := 0;
    event_record RECORD;
BEGIN
    -- Migrate events
    FOR event_record IN 
        SELECT * FROM runsignup_events WHERE timing_partner_id = partner_id
    LOOP
        INSERT INTO normalized_events (
            timing_partner_id, source_provider, source_event_id, event_name, 
            event_date, event_type, location_city, location_state, normalized_data
        ) VALUES (
            partner_id, 'RunSignUp', event_record.event_id::VARCHAR, event_record.event_name,
            event_record.start_date, 'running', event_record.address_city, 
            event_record.address_state, row_to_json(event_record)
        ) ON CONFLICT (timing_partner_id, source_provider, source_event_id) DO NOTHING;
        
        migrated_count := migrated_count + 1;
    END LOOP;
    
    RETURN migrated_count;
END;
$$ LANGUAGE plpgsql;

-- ========================================================================
-- SECTION 10: PERMISSIONS
-- ========================================================================

-- Grant permissions to existing application user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO project88_myappuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO project88_myappuser;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO project88_myappuser;

-- ========================================================================
-- END OF MIGRATION SCRIPT
-- ======================================================================== 