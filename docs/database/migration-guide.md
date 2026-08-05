# Migration Guide

## Prerequisites

- Use `C:\TEAM PROJECT\P-092\.venv`.
- Confirm `python -c "import sys; print(sys.executable)"` points to the project venv.
- Use a safe database target: local PostgreSQL, disposable PostgreSQL, Supabase development branch, or temporary Supabase test project.
- Do not use production credentials for validation.

## Commands

```powershell
python -m alembic heads
python -m alembic history
python -m alembic upgrade head
python -m alembic current
```

Rollback command for approved non-production testing only:

```powershell
python -m alembic downgrade -1
```

## Cautions

- Never test destructive migration behavior against production Supabase.
- Take a backup before production migration.
- Do not run downgrade in production without approval, backup, and rollback plan.
- Verify no migration contains hardcoded credentials or Supabase project URLs.

## Verification Checklist

- RLS enabled and forced on approved tables.
- Security views exist and do not expose scoring/audit internals.
- Public table privileges are revoked.
- Static tests pass.
- Live PostgreSQL RLS behavior is tested only against a safe target.

