-- Fix Database Field Length Issues in RunSignUp Participants Table
-- Issue: Fields limited to VARCHAR(20) causing sync failures
-- Date: July 7, 2025

-- ========================================================================
-- RUNSIGNUP PARTICIPANTS TABLE FIELD LENGTH FIXES
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
-- VALIDATION QUERIES - Run these to verify changes
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

-- Sample of longest values (for debugging)
SELECT 'phone' as field_type, phone as value, LENGTH(phone) as length
FROM runsignup_participants 
WHERE LENGTH(phone) > 20
LIMIT 5

UNION ALL

SELECT 'bib_num' as field_type, bib_num as value, LENGTH(bib_num) as length
FROM runsignup_participants 
WHERE LENGTH(bib_num) > 20
LIMIT 5

UNION ALL

SELECT 'chip_num' as field_type, chip_num as value, LENGTH(chip_num) as length
FROM runsignup_participants 
WHERE LENGTH(chip_num) > 20
LIMIT 5

UNION ALL

SELECT 'gender' as field_type, gender as value, LENGTH(gender) as length
FROM runsignup_participants 
WHERE LENGTH(gender) > 20
LIMIT 5;

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