# T-006/T-007 Live Validation

Run only against a disposable Supabase development/test project. Do not run these steps against production.

Required safety gates:

- `APP_ENV` is `development` or `test`.
- `ALLOW_LIVE_MIGRATION=true` before migration actions.
- `RUN_SUPABASE_INTEGRATION_TESTS=true` before live integration tests.
- `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, and `SUPABASE_STORAGE_BUCKET` are present.
- The target project is explicitly confirmed as non-production.

Never print credentials, database passwords, Supabase keys, access tokens, or `.env` values. Use:

```powershell
python scripts/check_t006_t007_environment.py
```

Migration validation:

1. Run `python -m alembic heads` and `python -m alembic history`.
2. Confirm the target is not production.
3. Confirm `APP_ENV=development` or `APP_ENV=test`.
4. Confirm `ALLOW_LIVE_MIGRATION=true`.
5. Run `python -m alembic upgrade head`.
6. Run `python -m alembic current`.
7. Confirm expected tables, `users.phone_number`, E.164 check constraint, upload-session table, PostgreSQL enum use, partial indexes, `FOR UPDATE` upload-session locking, RLS policies, security-invoker views, and private Storage setup.

Without `ALLOW_LIVE_MIGRATION=true`, online Alembic commands must fail before a database connection is opened.

If `fk_users_id_auth_users` validation fails because orphan application profiles exist, do not delete rows automatically. Follow `docs/backend/supabase-user-migration-remediation.md`.

Integration validation:

```powershell
python -m pytest tests/integration -v
```

When `RUN_SUPABASE_INTEGRATION_TESTS=false`, integration tests skip clearly. When it is `true`, missing required variables fail fast with variable names only. Phone/SMS OTP is never automated; resident and coordinator token scenarios require manually supplied test tokens:

- `SUPABASE_TEST_RESIDENT_ACCESS_TOKEN`
- `SUPABASE_TEST_COORDINATOR_ACCESS_TOKEN`
- `SUPABASE_TEST_TECHNICIAN_ACCESS_TOKEN` if a future technician scenario is added

The live suite validates:

- migration upgrade to head
- database revision at Alembic head
- required public tables
- `public.users.id -> auth.users.id` validation state
- RLS enabled on business tables
- final RLS policy names
- anonymous direct access denial
- private bucket configuration
- resident `/api/v1/auth/me`
- resident unit ownership and unowned-unit rejection
- coordinator `/api/v1/auth/me` and coordinator ticket read
- non-coordinator rejection from coordinator route
- signed upload target creation
- small PNG upload to private Storage
- upload-session creation, verification, and consumption
- attachment metadata persistence
- authorized signed download URL
- signed download object fetch
- unauthorized attachment download returning 404
- PostgREST RLS isolation for an unowned ticket

Current status:

- migration: BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED
- resident Auth: BLOCKED — MISSING TEST TOKEN
- coordinator Auth: BLOCKED — MISSING TEST TOKEN
- RLS isolation: BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED
- anonymous denial: BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED
- private bucket: BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED
- signed upload: BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED
- ticket with attachment: BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED
- signed download: BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED

Do not run `alembic downgrade base`, `DROP SCHEMA`, `DROP DATABASE`, or `TRUNCATE` against a shared project. Clean up only uniquely prefixed test records created by validation.

Final status stays T-007 IMPLEMENTED — LIVE VALIDATION BLOCKED until migration, Auth, RLS, and Storage are all validated on a confirmed Supabase development/test environment.
