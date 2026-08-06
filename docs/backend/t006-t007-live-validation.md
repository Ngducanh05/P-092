# T-006/T-007 Live Validation

Live Supabase validation is opt-in and must run only against a confirmed development or test project.

## Safety gates

Both settings are required before the integration suite may execute migrations:

- `RUN_SUPABASE_INTEGRATION_TESTS=true`
- `ALLOW_LIVE_MIGRATION=true`

The application environment must be `development` or `test`. Never enable these gates for production.

## Canonical test identities

- `SUPABASE_TEST_RESIDENT_ACCESS_TOKEN`
- `SUPABASE_TEST_BQL_ACCESS_TOKEN`

There is no Coordinator or Technician test token in the final architecture. Token values must never be printed or committed.

## Covered validation

The live suite verifies:

- Alembic upgrades to the final head.
- `residents`, `bql_staff`, and `resident_unit_memberships` exist.
- `public.users`, `role_enum`, Technician tables, assignment tables, and the Technician view are absent.
- Resident and BQL profile foreign keys reference `auth.users` and are validated.
- Actor-profile exclusivity triggers exist.
- RLS is enabled and forced on all final business tables.
- Resident ticket access is restricted by active unit membership.
- Active BQL staff can read the system-wide MVP ticket queue.
- Upload sessions, AI analysis, scoring, and audit tables remain unavailable to direct clients.
- The Storage bucket is private.
- Signed upload, transactional attachment consumption, and signed download still work.
- `resident_ticket_view` uses `security_invoker = true`.

## Commands

Run only after confirming the target project and supplying the required settings:

```powershell
python -m pytest tests/integration/test_supabase_live.py -v
```

Do not run downgrade, schema deletion, truncation, or destructive cleanup against a shared Supabase project. The suite removes only uniquely identified records that it creates.

## Status reporting

Do not claim live migration, Auth, RLS, or Storage success unless this gated suite was actually executed and passed against the intended safe project.
