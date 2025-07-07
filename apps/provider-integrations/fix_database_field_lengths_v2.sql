-- Fix Database Field Length Issues in RunSignUp Participants Table (V2)
-- Issue: Fields limited to VARCHAR(20) causing sync failures
-- Date: July 7, 2025

-- ========================================================================
-- STEP 1: DROP DEPENDENT VIEWS
-- ========================================================================

-- Drop the unified_participants view that depends on our columns
DROP VIEW IF EXISTS unified_participants;

-- ========================================================================
-- STEP 2: ALTER COLUMN TYPES
-- ========================================================================

-- Fix phone number field (international numbers can be longer)
ALTER TABLE runsignup_participants 
ALTER COLUMN phone TYPE VARCHAR(50);

-- Fix bib number field (some races use long alphanumeric bibs)
ALTER TABLE runsignup_participants 
ALTER COLUMN bib_num TYPE VARCHAR(50);

-- Fix chip number field (RFID chips can have long identifiers)
ALTER TABLE runsignup_participants 
ALTER COLUMN chip_num TYPE VARCHAR(50);

-- Gender field should be sufficient at 20 chars, but let's expand for safety
ALTER TABLE runsignup_participants 
ALTER COLUMN gender TYPE VARCHAR(30);

-- ========================================================================
-- STEP 3: RECREATE THE UNIFIED_PARTICIPANTS VIEW
-- ========================================================================

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

-- ========================================================================
-- STEP 4: VALIDATION QUERIES
-- ========================================================================

-- Check new field lengths
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'runsignup_participants' 
AND column_name IN ('phone', 'bib_num', 'chip_num', 'gender')
ORDER BY column_name;

-- Check for any existing data that was previously truncated
SELECT COUNT(*) as total_participants,
       COUNT(CASE WHEN LENGTH(phone) > 20 THEN 1 END) as long_phones,
       COUNT(CASE WHEN LENGTH(bib_num) > 20 THEN 1 END) as long_bibs,
       COUNT(CASE WHEN LENGTH(chip_num) > 20 THEN 1 END) as long_chips,
       COUNT(CASE WHEN LENGTH(gender) > 20 THEN 1 END) as long_genders
FROM runsignup_participants;

-- ========================================================================
-- STEP 5: VERIFICATION
-- ========================================================================

-- Test that the view was recreated successfully
SELECT COUNT(*) as total_unified_participants FROM unified_participants;

-- Show field lengths are now correct
SELECT 
    'Field length fixes applied successfully' as status,
    current_timestamp as applied_at;

-- ========================================================================
-- NOTES
-- ========================================================================

-- Original lengths (causing errors):
-- phone VARCHAR(20)      -> Now VARCHAR(50)
-- bib_num VARCHAR(20)    -> Now VARCHAR(50)  
-- chip_num VARCHAR(20)   -> Now VARCHAR(50)
-- gender VARCHAR(20)     -> Now VARCHAR(30)

-- This should resolve the sync errors:
-- ERROR - Error storing participant: value too long for type character varying(20)
-- ERROR - Error storing participant: current transaction is aborted, commands ignored until end of transaction block

-- After running this script, the sync should complete without field length errors
-- and the 2,174 errors across 7 timing partners should be resolved. 