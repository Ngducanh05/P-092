# T-006/T-007 Gap Analysis

| Requirement | Implementation action | Verification | Status |
|---|---|---|---|
| FixIt API routes | `/auth/me`, `/units/my`, signed upload, ticket create/list/detail, attachment download, and coordinator list are mounted under `/api/v1` | API tests | COMPLETE |
| Supabase Bearer auth | Cached verifier dependency supports JWKS, Auth server, and auto mode | JWT and API tests | COMPLETE |
| Resident profile mapping | `public.users.id` uses JWT `sub`; unknown valid Auth users are created only as residents | Auth dependency tests | COMPLETE |
| Phone-only residents | Email/full name nullable, phone unique when present, strict E.164 app validation and PostgreSQL check constraint | ORM/migration/auth tests | COMPLETE |
| Privileged users | Coordinator/technician provisioning remains backend-only | Script review and docs | IMPLEMENTED - UNIT TESTED |
| Ticket creation | Unit selection, status history, attachment consumption, and rollback are transactional | Service tests | COMPLETE |
| Private attachments | Public API uses upload sessions, not raw object paths; ticket responses hide private paths | API/service/storage tests | COMPLETE |
| Signed upload expiry | Upload target expiry is fixed at 7200 seconds | Storage tests | COMPLETE |
| Signed download | Download URL endpoint is authorized by ticket access and masks missing/unauthorized attachments | API/service tests | COMPLETE |
| JWT security cases | RS256, ES256, HS256 fallback, invalid claims, unknown keys, Auth-server failures, and cache reuse covered | JWT tests | COMPLETE |
| RLS identity binding | Final policies use `auth.uid()` for authenticated users and deny direct mutation | Migration tests | IMPLEMENTED - UNIT TESTED |
| Upload-session RLS | Upload-session table has RLS enabled and denies direct anon/authenticated access | Migration tests | IMPLEMENTED - UNIT TESTED |
| Auth FK validation | Additive migration validates `fk_users_id_auth_users` only when no orphan profiles exist | Migration tests and remediation doc | IMPLEMENTED - NOT LIVE TESTED |
| Private bucket setup | Backend-only setup script creates/verifies a private constrained bucket | Script review and storage docs | IMPLEMENTED - NOT LIVE TESTED |
| Secret scanning | Match-level allowlisting prevents mixed placeholder/secret bypasses | Secret scanner tests and CI | COMPLETE |
| Live Supabase validation | Gated tests fail fast when enabled without required variables and tokens | Not run locally | BLOCKED - MISSING SAFE ENVIRONMENT |

T-006 is code complete and covered by the default test suite.

T-007 is code complete, but live Supabase migration/Auth/RLS/Storage evidence is blocked until a confirmed development/test Supabase project and required tokens are available. Do not report production readiness from this repository state alone.
