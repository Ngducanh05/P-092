> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

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


## `f6a7b8c9d0e1`

Down revision: `e5f6a7b8c9d0`

Purpose: restore the source-required Technician actor without restoring the obsolete generic-user design.

- Requires `auth.users` to exist; preflight fails safely with count-only diagnostics when required objects or data invariants are invalid.
- Creates `technician_profiles` with `id` as both PK and FK to `auth.users.id`.
- Creates `technician_skills` and `ticket_assignments`.
- Creates `assignment_status_enum` and assignment lifecycle timestamps/notes.
- Adds the Auth FK for `ticket_assignments.assigned_by_auth_user_id`.
- Enforces one active assignment per ticket using a partial unique index.
- Extends actor-profile exclusivity to Resident, BQL, and Technician.
- Enables and forces RLS on Technician tables; grants only assignment-scoped reads to authenticated Technicians.
- Preserves backend-only mutation boundaries and does not recreate `public.users` or `role_enum`.

This revision has not been applied automatically. Validate statically and on an isolated PostgreSQL target before any explicit live upgrade.

## Safe validation

```powershell
python -m alembic heads
python -m alembic history
python -m pytest tests/test_migrations tests/test_security -v
```

Do not execute `alembic upgrade head` against the configured live database without explicit user action, a confirmed non-production target, and the migration safety gates. The final cutover downgrade is intentionally unsupported.
