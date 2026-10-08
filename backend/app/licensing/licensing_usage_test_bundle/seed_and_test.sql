-- Licensing usage test database
-- Current seeded values:
--   volume_usage = 100
--   token_usage  = 10000

-- Read current values
SELECT current_usage FROM volume_usage WHERE id = 1;
SELECT current_usage FROM token_usage WHERE id = 1;

-- PASS examples for a signed policy:
--   volume limit = 500       -> 100 < 500
--   token limit  = 500000    -> 10000 < 500000

-- Boundary/FAIL tests:
UPDATE volume_usage
SET current_usage = 500,
    updated_at = CURRENT_TIMESTAMP
WHERE id = 1;

UPDATE token_usage
SET current_usage = 500000,
    updated_at = CURRENT_TIMESTAMP
WHERE id = 1;

-- Reset to safe test values:
UPDATE volume_usage
SET current_usage = 100,
    updated_at = CURRENT_TIMESTAMP
WHERE id = 1;

UPDATE token_usage
SET current_usage = 10000,
    updated_at = CURRENT_TIMESTAMP
WHERE id = 1;
