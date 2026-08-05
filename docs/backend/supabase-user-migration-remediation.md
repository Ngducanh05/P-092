# Supabase User Migration Remediation

The `public.users.id -> auth.users.id` foreign key can be validated only when every application profile has a matching Supabase Auth user.

Before validating, run only the count check:

```sql
SELECT COUNT(*)
FROM public.users app_user
LEFT JOIN auth.users auth_user
  ON auth_user.id = app_user.id
WHERE auth_user.id IS NULL;
```

Do not print IDs, emails, phone numbers, or other PII. If the count is zero, the migration may run:

```sql
ALTER TABLE public.users
VALIDATE CONSTRAINT fk_users_id_auth_users;
```

The migration intentionally does not delete orphan profiles. If it stops with an orphan count:

1. Confirm the database is a development/test target, not production.
2. Record only the orphan count in validation notes.
3. Investigate the orphan profiles through a privileged SQL session.
4. For each orphan, decide whether to create the missing Supabase Auth user and preserve the same UUID, deactivate the application profile, or remove the profile through an approved data-remediation process.
5. Do not publish user IDs, emails, phone numbers, or other PII in tickets, logs, or validation reports.
6. Re-run `python -m alembic upgrade head` only after the orphan count is zero.

Production data remediation requires a separate reviewed migration/runbook and is deferred from T-006/T-007.

Current live status is BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED until the count check, validation state, and migration head are verified on a confirmed Supabase development/test environment.
