-- ChronoTrack Live Schema Extension
-- Extends existing ct_ tables to support ChronoTrack Live API data
-- alongside existing TCP hardware data

-- Add data_source field to distinguish between TCP hardware and ChronoTrack Live API
-- Existing data will be marked as 'tcp_hardware', new data as 'chronotrack_live'

-- Extend ct_events table
ALTER TABLE ct_events 
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'tcp_hardware',
ADD COLUMN IF NOT EXISTS provider_event_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS api_fetched_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS api_credentials_used VARCHAR(100);

-- Add index for ChronoTrack Live queries
CREATE INDEX IF NOT EXISTS idx_ct_events_data_source ON ct_events(data_source);
CREATE INDEX IF NOT EXISTS idx_ct_events_provider_event_id ON ct_events(provider_event_id);

-- Extend ct_participants table  
ALTER TABLE ct_participants
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'tcp_hardware',
ADD COLUMN IF NOT EXISTS provider_participant_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS api_fetched_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS emergency_contact JSONB,
ADD COLUMN IF NOT EXISTS payment_status VARCHAR(50),
ADD COLUMN IF NOT EXISTS amount_paid DECIMAL(10,2),
ADD COLUMN IF NOT EXISTS registration_status VARCHAR(50) DEFAULT 'active';

-- Add indexes for ChronoTrack Live participant queries
CREATE INDEX IF NOT EXISTS idx_ct_participants_data_source ON ct_participants(data_source);
CREATE INDEX IF NOT EXISTS idx_ct_participants_provider_participant_id ON ct_participants(provider_participant_id);

-- Extend ct_results table for ChronoTrack Live results
ALTER TABLE ct_results
ADD COLUMN IF NOT EXISTS data_source VARCHAR(50) DEFAULT 'tcp_hardware',
ADD COLUMN IF NOT EXISTS provider_result_id VARCHAR(100),
ADD COLUMN IF NOT EXISTS api_fetched_date TIMESTAMP,
ADD COLUMN IF NOT EXISTS result_status VARCHAR(50) DEFAULT 'finished',
ADD COLUMN IF NOT EXISTS split_times JSONB;

-- Add indexes for ChronoTrack Live result queries  
CREATE INDEX IF NOT EXISTS idx_ct_results_data_source ON ct_results(data_source);
CREATE INDEX IF NOT EXISTS idx_ct_results_provider_result_id ON ct_results(provider_result_id);

-- Create view for ChronoTrack Live specific data
CREATE OR REPLACE VIEW ct_live_events AS
SELECT 
    event_id,
    timing_partner_id,
    provider_event_id,
    event_name,
    start_date,
    end_date,
    location,
    event_type,
    distance,
    status,
    api_fetched_date,
    api_credentials_used,
    created_at,
    updated_at
FROM ct_events 
WHERE data_source = 'chronotrack_live';

CREATE OR REPLACE VIEW ct_live_participants AS
SELECT 
    participant_id,
    event_id,
    timing_partner_id,
    provider_participant_id,
    first_name,
    last_name,
    email,
    phone,
    date_of_birth,
    age,
    gender,
    city,
    state,
    country,
    bib_number,
    emergency_contact,
    team_name,
    division,
    registration_date,
    registration_status,
    payment_status,
    amount_paid,
    api_fetched_date,
    created_at,
    updated_at
FROM ct_participants 
WHERE data_source = 'chronotrack_live';

CREATE OR REPLACE VIEW ct_live_results AS
SELECT 
    result_id,
    event_id,
    participant_id,
    timing_partner_id,
    provider_result_id,
    bib_number,
    chip_time,
    gun_time,
    overall_place,
    gender_place,
    division_place,
    finish_time,
    split_times,
    result_status,
    api_fetched_date,
    created_at
FROM ct_results 
WHERE data_source = 'chronotrack_live';

-- Update unified_results view to include ChronoTrack Live data
CREATE OR REPLACE VIEW unified_results AS
-- Existing ChronoTrack TCP data
SELECT 
    'chronotrack_tcp' as provider,
    event_id,
    participant_id,
    bib_number,
    chip_time,
    gun_time,
    overall_place,
    gender_place,
    division_place,
    finish_time,
    created_at,
    'tcp_hardware' as data_source
FROM ct_results 
WHERE data_source = 'tcp_hardware' OR data_source IS NULL
UNION ALL
-- New ChronoTrack Live API data
SELECT 
    'chronotrack_live' as provider,
    event_id,
    participant_id,
    bib_number,
    chip_time,
    gun_time,
    overall_place,
    gender_place,
    division_place,
    finish_time,
    created_at,
    'chronotrack_live' as data_source
FROM ct_results 
WHERE data_source = 'chronotrack_live'
UNION ALL
-- RunSignUp results
SELECT 
    'runsignup' as provider,
    event_id,
    null as participant_id,
    bib_number,
    chip_time,
    clock_time as gun_time,
    overall_place,
    gender_place,
    division_place,
    created_at as finish_time,
    created_at,
    'api' as data_source
FROM runsignup_results
UNION ALL
-- Copernico results (if table exists)
SELECT 
    'copernico' as provider,
    event_id,
    participant_id,
    bib_number,
    chip_time,
    gun_time,
    overall_place,
    gender_place,
    division_place,
    finish_time,
    created_at,
    'api' as data_source
FROM copernico_results
WHERE EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'copernico_results');

-- Add provider_id=1 for ChronoTrack Live in providers table (if not exists)
INSERT INTO providers (provider_id, name, description, created_at)
VALUES (1, 'ChronoTrack Live', 'ChronoTrack Live API Integration', NOW())
ON CONFLICT (provider_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description;

-- Add comments for documentation
COMMENT ON COLUMN ct_events.data_source IS 'Source of data: tcp_hardware (existing) or chronotrack_live (API)';
COMMENT ON COLUMN ct_events.provider_event_id IS 'ChronoTrack Live API event ID';
COMMENT ON COLUMN ct_participants.data_source IS 'Source of data: tcp_hardware (existing) or chronotrack_live (API)';
COMMENT ON COLUMN ct_participants.provider_participant_id IS 'ChronoTrack Live API participant ID';
COMMENT ON COLUMN ct_results.data_source IS 'Source of data: tcp_hardware (existing) or chronotrack_live (API)';
COMMENT ON COLUMN ct_results.provider_result_id IS 'ChronoTrack Live API result ID';

-- Create function to avoid duplicate events between TCP and ChronoTrack Live
CREATE OR REPLACE FUNCTION check_duplicate_chronotrack_event(
    p_event_name VARCHAR,
    p_event_date TIMESTAMP,
    p_timing_partner_id INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    existing_count INTEGER;
BEGIN
    -- Check if similar event exists in TCP data within 24 hours
    SELECT COUNT(*) INTO existing_count
    FROM ct_events 
    WHERE timing_partner_id = p_timing_partner_id
    AND LOWER(event_name) = LOWER(p_event_name)
    AND ABS(EXTRACT(EPOCH FROM (start_date - p_event_date))) < 86400 -- 24 hours
    AND data_source = 'tcp_hardware';
    
    RETURN existing_count > 0;
END;
$$ LANGUAGE plpgsql; 