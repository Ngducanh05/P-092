# T-006/T-007 Gap Analysis

| Requirement | Implementation action | Verification | Status |
|---|---|---|---|
| FixIt API routes | `/auth/me`, `/units/my`, signed upload, ticket create/list/detail, attachment download, coordinator list, `/health`, and `/ready` are mounted | API tests | COMPLETE |
| Supabase Bearer auth | Cached verifier dependency supports JWKS, Auth server, and auto mode | JWT and API tests | COMPLETE |
| Resident profile mapping | `public.users.id` uses JWT `sub`; unknown valid Auth users are created only as residents | Auth dependency tests | COMPLETE |
| Phone-only residents | Email/full name nullable, phone unique when present, strict E.164 app validation and PostgreSQL check constraint | ORM/migration/auth tests | COMPLETE |
| Privileged users | Coordinator/technician provisioning remains backend-only | Script review and docs | IMPLEMENTED — UNIT TESTED |
| Alembic safety gate | Online migrations require `APP_ENV=development|test` and `ALLOW_LIVE_MIGRATION=true` before any connection is created | Migration behavior tests | IMPLEMENTED — UNIT TESTED |
| Supabase admin headers | Shared helper sends `sb_secret_*` as `apikey` only and keeps legacy service-role Bearer compatibility | Security tests | IMPLEMENTED — UNIT TESTED |
| Ticket creation | Unit selection, status history, attachment consumption, and rollback are transactional | Service tests | COMPLETE |
| Private attachments | Public API uses upload sessions, not raw object paths; ticket responses hide private paths | API/service/storage tests | COMPLETE |
| Signed upload expiry | Upload target expiry is fixed at 7200 seconds | Storage tests | COMPLETE |
| Signed download | Download URL endpoint is authorized by ticket access and masks missing/unauthorized attachments | API/service tests | COMPLETE |
| JWT security cases | RS256, ES256, HS256 Auth-server verification, invalid claims, unknown keys, invalid signatures, inactive users, and role source behavior covered | JWT/auth tests | COMPLETE |
| RLS identity binding | Final policies use `auth.uid()` for authenticated users and deny direct mutation | Migration tests | IMPLEMENTED — UNIT TESTED |
| Upload-session RLS | Upload-session table has RLS enabled and denies direct anon/authenticated access | Migration tests | IMPLEMENTED — UNIT TESTED |
| Auth FK validation | Additive migration validates `fk_users_id_auth_users` only when no orphan profiles exist | Migration tests and remediation doc | IMPLEMENTED — UNIT TESTED |
| Private bucket setup | Backend-only setup script creates/verifies a private constrained bucket | Script review and storage docs | IMPLEMENTED — UNIT TESTED |
| Secret scanning | Match-level allowlisting detects OpenAI-like keys, JWTs, database URLs with passwords, and `sb_secret_*` keys without printing values | Secret scanner tests and CI | COMPLETE |
| Live Supabase validation | Real gated integration tests cover migration, Auth, RLS, anonymous denial, private bucket config, signed upload, ticket attachment flow, and signed download | Not run without confirmed Supabase development/test environment | BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED |
| Scenario tokens | Resident/coordinator scenarios use manually supplied access tokens only | Not run without tokens | BLOCKED — MISSING TEST TOKEN |

T-006 COMPLETE.

T-007 IMPLEMENTED — LIVE VALIDATION BLOCKED until migration, Auth, RLS, and Storage are validated on a confirmed Supabase development/test environment. Do not report T-007 COMPLETE from code, static tests, or SQLite tests alone.
