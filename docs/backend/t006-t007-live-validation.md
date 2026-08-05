# T-006/T-007 Live Validation

Run only against a disposable Supabase development/test project.

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
3. Run `python -m alembic current`.
4. Run `python -m alembic upgrade head`.
5. Run `python -m alembic current`.
6. Confirm expected tables, `users.phone_number`, E.164 check constraint, upload-session table, indexes, RLS policies, and private Storage setup.

If `fk_users_id_auth_users` validation fails because orphan application profiles exist, do not delete rows automatically. Follow `docs/backend/supabase-user-migration-remediation.md`.

Integration validation:

```powershell
python -m pytest tests/integration -v
```

When `RUN_SUPABASE_INTEGRATION_TESTS=false`, integration tests skip. When it is `true`, missing required variables fail fast with variable names only. Phone/SMS OTP is never automated; resident and coordinator token scenarios require manually supplied test tokens.

Current status:

- Supabase migration: BLOCKED - MISSING SAFE ENVIRONMENT
- Auth resident token: BLOCKED - MISSING TEST TOKEN
- Auth coordinator token: BLOCKED - MISSING TEST TOKEN
- RLS isolation: BLOCKED - MISSING SAFE ENVIRONMENT
- Private bucket: BLOCKED - MISSING SAFE ENVIRONMENT
- Signed upload: BLOCKED - MISSING SAFE ENVIRONMENT
- Ticket with attachment: BLOCKED - MISSING SAFE ENVIRONMENT
- Signed download: BLOCKED - MISSING SAFE ENVIRONMENT

Do not run `alembic downgrade base`, `DROP SCHEMA`, `DROP DATABASE`, or `TRUNCATE` against a shared project. Clean up only uniquely prefixed test records created by validation.
