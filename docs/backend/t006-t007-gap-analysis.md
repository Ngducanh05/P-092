# T-006/T-007 Gap Analysis

| Requirement | Current state | Gap | Implementation action | Verification | Status |
|---|---|---|---|---|---|
| T-006 core API | Starter chat/status only | Missing FixIt endpoints | Added `/api/v1` auth, units, storage, tickets, coordinator routes | API tests/import | COMPLETE |
| T-007 Supabase database | Core tables and placeholder RLS existed | User/Auth alignment missing | Added user schema migration and RLS identity migration | Migration static tests | COMPLETE |
| Resident phone OTP | `users.email` required | Phone-only profile blocked | Added nullable email/full_name and unique phone | ORM/migration tests | COMPLETE |
| Coordinator email/password | Role enum existed | Provisioning process absent | Added backend-only provisioning script | Static review | COMPLETE |
| Technician email/password | Role enum existed | Provisioning process absent | Added backend-only provisioning script | Static review | COMPLETE |
| JWT verification | None | Bearer token not validated | Added JWKS/auth-server/auto verifier | JWT tests | COMPLETE |
| Local user profile | Local UUID default | Not tied to Supabase `sub` | `users.id` now supplied from Auth UUID | Migration/ORM tests | COMPLETE |
| Membership ownership | Tables existed | API enforcement missing | Added unit/ticket repositories and service checks | Service/API tests | COMPLETE |
| Ticket creation | Table existed | No route/service | Added transactional create service | Service/API tests | COMPLETE |
| Ticket list/detail | Table existed | No API | Added resident/coordinator list/detail | API tests | COMPLETE |
| Coordinator ticket list | Deferred in docs | No endpoint | Added system-wide MVP read endpoint | API tests | COMPLETE |
| Private attachments | `file_url` metadata existed | No signed storage flow | Added signed upload service and attachment path checks | Storage tests | COMPLETE |
| RLS | Deny placeholders | `NULL::uuid`/pending policies | New migration drops placeholders and binds `auth.uid()` | Static RLS tests | COMPLETE |
| Live migration | No safe env proven | Cannot run safely by default | Documented gated live validation | Manual only | NOT RUN - SAFE ENVIRONMENT UNAVAILABLE |
| Tests | DB tests existed | T-006/T-007 coverage missing | Added focused tests | pytest | COMPLETE |
| Documentation | Starter/product docs incomplete | Missing Supabase/API docs | Added backend docs and README update | Static review | COMPLETE |

Live Supabase validation remains blocked unless `APP_ENV` is `development` or `test`, `ALLOW_LIVE_MIGRATION=1`, and a disposable Supabase target is configured.
