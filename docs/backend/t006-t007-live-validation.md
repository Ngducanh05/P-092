> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# T-006/T-007 Live Validation

Live Supabase validation is opt-in and must run only against a confirmed development or test project. No live validation was executed as part of the offline Technician restoration work.

## Safety gates

Both settings are required before the integration suite may execute migrations:

- `RUN_SUPABASE_INTEGRATION_TESTS=true`
- `ALLOW_LIVE_MIGRATION=true`

The application environment must be `development` or `test`. Never enable these gates for production.

## Canonical test identities

- `SUPABASE_TEST_RESIDENT_ACCESS_TOKEN`
- `SUPABASE_TEST_BQL_ACCESS_TOKEN`
- `SUPABASE_TEST_TECHNICIAN_ACCESS_TOKEN`

Token values must never be printed or committed.

## Covered validation

The gated suite verifies:

- Alembic upgrades to the current single head.
- `residents`, `bql_staff`, `technician_profiles`, `technician_skills`, `ticket_assignments`, and `resident_unit_memberships` exist.
- `public.users`, `role_enum`, and obsolete Technician security views remain absent.
- Resident, BQL, Technician, and assignment actor foreign keys reference `auth.users` as designed.
- Three-profile exclusivity triggers exist.
- RLS is enabled and forced on final business tables.
- Resident ticket access is restricted by active unit membership.
- Active BQL staff can read the system-wide queue and Technician roster.
- Technicians can read only their own active assignments and parent tickets.
- Upload sessions, AI analysis, scoring, and audit tables remain unavailable to direct clients.
- The Storage bucket is private.
- Signed upload, transactional attachment consumption, and signed download still work.
- `resident_ticket_view` uses `security_invoker = true`.

## Command

Run only after confirming the target project and supplying synthetic test identities:

```powershell
python -m pytest tests/integration/test_supabase_live.py -v
```

Do not run downgrade, schema deletion, truncation, or destructive cleanup against a shared Supabase project. The suite removes only uniquely identified records it creates.

Do not claim live migration, Auth, RLS, or Storage success unless this gated suite actually passed against the intended safe project.
