"""Comprehensive production tests for the Databricks Key Vault-backed Ed25519 licensing subsystem.

Test requirements coverage:
 1. Valid signed license artifact validates and enables features.
 2. Tampered signature bytes fail closed.
 3. Modified license_id fails closed.
 4. Modified product fails closed.
 5. Modified environment fails closed.
 6. Modified expires_at fails closed.
 7. Expired license fails closed.
 8. Malformed JSON fails closed.
 9. Missing signature fails closed.
10. Invalid base64 signature fails closed.
11. Missing required field fails closed.
12. Wrong field type fails closed.
13. Invalid feature type (non-boolean) fails closed.
14. Empty secret fails closed.
15. Secret provider failure fails closed.
16. Wrong public key fails closed.
17. Exact expiration boundary: now == expires_at => expired.
18. Future valid expiration: now < expires_at => valid.
19. Embedded public key cannot be overridden through environment.
20. Licensing cannot be disabled through environment.
21. Identity mismatches fail closed.
22. Databricks provider error handling.
23. Timezone-naive issued_at is strictly rejected.
24. Timezone-naive expires_at is strictly rejected.
25. Non-UTC timezone offsets are strictly rejected.
26. Canonical UTC timestamps with 'Z' are accepted.
27. Expiration boundary triad: now < exp (valid), now == exp (expired), now > exp (expired).
"""

from backend.tests.test_licensing import *
