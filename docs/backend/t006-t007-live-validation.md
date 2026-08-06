# T-006/T-007 Live Validation

Live Supabase integration tests remain gated by:

- `RUN_SUPABASE_INTEGRATION_TESTS`
- `ALLOW_LIVE_MIGRATION`

Canonical test tokens:

- `SUPABASE_TEST_RESIDENT_ACCESS_TOKEN`
- `SUPABASE_TEST_BQL_ACCESS_TOKEN`

Do not provide Technician tokens. Live validation covers Resident isolation, BQL system-wide MVP ticket read, private Storage upload/download, RLS policy presence, and final security-invoker view checks.
