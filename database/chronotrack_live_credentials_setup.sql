-- ChronoTrack Live Credentials Setup
-- This script sets up provider_id=1 credentials for ChronoTrack Live integration

-- First, ensure provider_id=1 exists for ChronoTrack Live
INSERT INTO providers (provider_id, name, description, created_at)
VALUES (1, 'ChronoTrack Live', 'ChronoTrack Live API Integration', NOW())
ON CONFLICT (provider_id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description;

-- Example credential setup (replace with actual values)
-- Run this for each timing partner that has ChronoTrack Live credentials

-- TEMPLATE: Replace these values with actual credentials
-- INSERT INTO partner_provider_credentials (
--     timing_partner_id,
--     provider_id,
--     principal,
--     secret,
--     additional_config,
--     created_at
-- ) VALUES (
--     [TIMING_PARTNER_ID],     -- Replace with actual timing partner ID
--     1,                       -- ChronoTrack Live provider_id
--     '[USERNAME]',            -- Replace with actual ChronoTrack Live username
--     '[SHA_ENCODED_PASSWORD]', -- Replace with SHA-encoded password
--     '{"base_url": "https://chronotrack.com/api/v1", "timeout": 30}', -- Additional config
--     NOW()
-- ) ON CONFLICT (timing_partner_id, provider_id) 
-- DO UPDATE SET
--     principal = EXCLUDED.principal,
--     secret = EXCLUDED.secret,
--     additional_config = EXCLUDED.additional_config;

-- Example for timing partner ID 1 (REPLACE WITH REAL VALUES):
-- INSERT INTO partner_provider_credentials (
--     timing_partner_id,
--     provider_id,
--     principal,
--     secret,
--     additional_config,
--     created_at
-- ) VALUES (
--     1,                                          -- Timing partner ID 1
--     1,                                          -- ChronoTrack Live provider_id
--     'example_username',                         -- ChronoTrack Live username
--     'sha256_encoded_password_hash_here',        -- SHA-256 encoded password
--     '{"base_url": "https://chronotrack.com/api/v1", "timeout": 30, "rate_limit": 1500}',
--     NOW()
-- ) ON CONFLICT (timing_partner_id, provider_id) 
-- DO UPDATE SET
--     principal = EXCLUDED.principal,
--     secret = EXCLUDED.secret,
--     additional_config = EXCLUDED.additional_config;

-- Example for timing partner ID 2 (REPLACE WITH REAL VALUES):
-- INSERT INTO partner_provider_credentials (
--     timing_partner_id,
--     provider_id,
--     principal,
--     secret,
--     additional_config,
--     created_at
-- ) VALUES (
--     2,                                          -- Timing partner ID 2
--     1,                                          -- ChronoTrack Live provider_id
--     'another_username',                         -- ChronoTrack Live username
--     'another_sha256_encoded_password_hash',     -- SHA-256 encoded password
--     '{"base_url": "https://chronotrack.com/api/v1", "timeout": 30, "rate_limit": 1500}',
--     NOW()
-- ) ON CONFLICT (timing_partner_id, provider_id) 
-- DO UPDATE SET
--     principal = EXCLUDED.principal,
--     secret = EXCLUDED.secret,
--     additional_config = EXCLUDED.additional_config;

-- Check which timing partners exist
SELECT 
    timing_partner_id,
    company_name,
    created_at
FROM timing_partners 
ORDER BY timing_partner_id;

-- Check existing provider credentials
SELECT 
    tp.timing_partner_id,
    tp.company_name,
    p.name as provider_name,
    ppc.principal,
    CASE 
        WHEN ppc.secret IS NOT NULL THEN 'SET'
        ELSE 'NOT SET'
    END as secret_status,
    ppc.additional_config,
    ppc.created_at
FROM timing_partners tp
LEFT JOIN partner_provider_credentials ppc ON tp.timing_partner_id = ppc.timing_partner_id
LEFT JOIN providers p ON ppc.provider_id = p.provider_id
WHERE p.provider_id = 1 OR p.provider_id IS NULL
ORDER BY tp.timing_partner_id;

-- Check if ChronoTrack Live extension schema has been applied
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'ct_events' 
AND column_name IN ('data_source', 'provider_event_id', 'api_fetched_date', 'api_credentials_used')
ORDER BY column_name;

-- Check if views exist
SELECT 
    table_name,
    table_type
FROM information_schema.tables 
WHERE table_name IN ('ct_live_events', 'ct_live_participants', 'ct_live_results')
ORDER BY table_name;

-- Instructions:
-- 
-- 1. First run the database schema extension:
--    psql -d project88_myappdb -f database/chronotrack_live_schema_extension.sql
--
-- 2. Get actual ChronoTrack Live credentials from timing partners
--
-- 3. Encode passwords using SHA-256:
--    python3 -c "import hashlib; print(hashlib.sha256('your_password'.encode()).hexdigest())"
--
-- 4. Update the INSERT statements above with real values
--
-- 5. Run this script:
--    psql -d project88_myappdb -f database/chronotrack_live_credentials_setup.sql
--
-- 6. Verify credentials are set up correctly using the SELECT statements above 