# T-006/T-007 Live Validation

Run only against a disposable Supabase development/test project.

1. Confirm `APP_ENV=development` or `APP_ENV=test`.
2. Confirm `ALLOW_LIVE_MIGRATION=1` before migration actions.
3. Redact the database target before recording evidence.
4. Run `python -m alembic heads` and `python -m alembic history`.
5. Inspect pending migrations.
6. Run `python -m alembic upgrade head` and `python -m alembic current`.
7. Check the expected tables, `users.phone_number`, partial indexes, and RLS policies.
8. Create test Supabase Auth users for resident phone and coordinator email in the dashboard or admin helper.
9. Verify `/api/v1/auth/me`, resident ownership isolation, coordinator list access, private bucket existence, signed upload, and signed download.
10. Confirm anonymous direct table access remains denied.

Do not run `alembic downgrade base`, `DROP SCHEMA`, `DROP DATABASE`, or `TRUNCATE` against a shared project. Clean up only uniquely prefixed test records created by validation.

Current status: NOT RUN - SAFE ENVIRONMENT UNAVAILABLE.
