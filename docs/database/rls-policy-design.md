# RLS Policy Design

## Principles

- Deny by default.
- Least privilege.
- Ownership derives from stored relationships.
- Do not trust client-supplied `resident_id`, `user_id`, `unit_id`, `technician_id`, `role`, or recipient identifiers.
- Preserve history.
- Isolate service-role operations.
- Treat audit logs as append-only.
- Use views/backend projections for column exposure because RLS controls rows, not columns.

## Runtime Identity Status

Status: REQUIRES BUSINESS CLARIFICATION.

The migration does not call `auth.uid()` or `auth.jwt()`. Supabase Auth and JWT claim mapping are not confirmed. The current policies are non-granting placeholders that preserve required ownership predicates with `NULL::uuid` markers and `false` guards.

## Table Policy Review

| Table | RLS enabled? | Forced RLS? | Allowed actors | SELECT predicate | INSERT/UPDATE/DELETE | Backend-only? | Column concerns |
|---|---|---|---|---|---|---|---|
| `users` | Yes | Yes | Service only pending identity | Deny | Deny | Yes | Email/name |
| `units` | Yes | Yes | Service only pending scope | Deny | Deny | Yes | Unit identifiers |
| `user_unit_memberships` | Yes | Yes | Service only pending identity | Deny | Deny | Yes | Ownership links |
| `technician_profiles` | Yes | Yes | Service only pending identity | Deny | Deny | Yes | Availability |
| `technician_skills` | Yes | Yes | Service only pending identity | Deny | Deny | Yes | Skills |
| `tickets` | Yes | Yes | Resident/technician predicates pending identity | Active membership or active assignment, currently guarded false | Deny client mutation | Yes for writes | Description/location |
| `ticket_attachments` | Yes | Yes | Parent ticket predicates pending identity | Parent ticket ownership, currently guarded false | Deny client mutation | Yes | Private object path |
| `ticket_assignments` | Yes | Yes | Technician predicate pending identity | Active assignment, currently guarded false | Deny client mutation | Yes | Routing |
| `ticket_status_history` | Yes | Yes | Parent ticket predicates pending identity | Parent ticket access, currently guarded false | Deny client mutation | Yes | Reason text |
| `ai_analysis_runs` | Yes | Yes | Service only | Deny | Deny | Yes | AI internals |
| `ticket_scoring_results` | Yes | Yes | Service only | Deny | Deny | Yes | Score breakdown |
| `notifications` | Yes | Yes | Recipient predicate pending identity | Recipient-owned, currently guarded false | Deny client mutation | Yes | Message body |
| `audit_logs` | Yes | Yes | Service/security only | Deny client select | Deny client update/delete; insert pending service identity | Yes | JSONB audit payloads |

