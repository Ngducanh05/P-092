# Migration Guide

Existing revisions through `c3d4e5f6a7b8` remain historical. Do not delete, reorder, squash, or rewrite them to pretend the old `public.users` and Technician architecture never existed.

The Resident/BQL actor refactor uses two later revisions:

## `d4e5f6a7b8c9`

Down revision: `c3d4e5f6a7b8`

Purpose: introduce and copy.

- Creates `residents` and `bql_staff`.
- Adds conditional `auth.users` foreign keys as `NOT VALID` during the additive phase.
- Creates the database trigger that prevents the same Auth UUID from appearing in both profile tables.
- Aborts with counts only when Technician/Admin users, invalid Resident phone data, invalid BQL email data, non-Resident memberships, non-Resident ticket ownership, or non-Resident upload ownership exists.
- Copies Resident and BQL profile rows.
- Creates and copies `resident_unit_memberships`.
- Adds Resident-compatible ticket and upload-session foreign keys.
- Adds new shared Auth UUID columns for status history, notifications, and audit logs.
- Preserves the old structures temporarily for cutover validation.

## `e5f6a7b8c9d0`

Down revision: `d4e5f6a7b8c9`

Purpose: validate, cut over, and clean up.

- Verifies copied Resident, BQL, and membership counts.
- Verifies membership, ticket, and upload-session Resident references.
- Verifies no UUID exists in both profile tables.
- Aborts when any Technician profile, Technician skill, or assignment row exists.
- Validates the two profile foreign keys to `auth.users` when those constraints exist.
- Removes old role-based policies, the Technician view, Technician tables, old actor columns, `user_unit_memberships`, `public.users`, and `role_enum`.
- Adds shared Auth UUID foreign keys for history, notifications, and audit logs.
- Recreates the safe Resident view and final Resident/BQL RLS policies.
- Adds explicit deny-all client policies for upload sessions, AI analysis, scoring, and audit logs.

## Safe validation

```powershell
python -m alembic heads
python -m alembic history
python -m pytest tests/test_migrations tests/test_security -v
```

Do not execute `alembic upgrade head` against the configured live database without explicit user action, a confirmed non-production target, and the migration safety gates. The final cutover downgrade is intentionally unsupported.
