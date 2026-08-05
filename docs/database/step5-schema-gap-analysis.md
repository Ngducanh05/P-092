# Step 5 Schema Gap Analysis

This review compares the confirmed FixIt Agent operational flow with the database schema that existed after the initial migration. The initial six tables support core ticket intake and AI/scoring history, but they do not fully represent resident unit membership, technician operations, assignments, status transitions, notifications, and audit history.

| Business flow | Required data | Existing support | Gap | Action | Source |
|---|---|---|---|---|---|
| Resident account linked to apartment/unit | A user can be linked to one or more units over time, with active/inactive membership state | `users`, `units`, and `tickets.unit_id` exist | No account-to-unit relationship independent of tickets | IMPLEMENT NOW: add `user_unit_memberships` with `(user_id, unit_id)` uniqueness and active indexes | Step 5 confirmed ownership rules |
| Resident-owned ticket lookup | Ticket ownership through resident and unit relationships | `tickets.resident_id`, `tickets.unit_id`, and indexes exist | Ticket has unit data, but active resident access needs membership structure | IMPLEMENT NOW: add `user_unit_memberships`; keep existing ticket resident/unit fields | Step 5 resident access basis |
| Technician profile and availability | Technician operational profile separate from generic account data | `users.role` includes `technician` | No active/available technician operations table | IMPLEMENT NOW: add `technician_profiles` keyed by `users.id` | Step 5 confirmed actors |
| Technician category skills | Technician-to-category mapping | Shared `Category` enum exists | No skill mapping table | IMPLEMENT NOW: add `technician_skills` reusing `category_enum` | Coordinator assignment by category skill |
| Ticket assignment | Ticket assigned to technician by coordinator, with current active assignment | No assignment table | No structural basis for technician ticket ownership | IMPLEMENT NOW: add `ticket_assignments` | Technician access through active assignment |
| Technician assignment history | Preserve previous assignments instead of overwriting | No assignment table | No assignment history or one-active-ticket assignment constraint | IMPLEMENT NOW: add assignment rows and partial unique active-ticket index | Step 5 assignment history requirement |
| Ticket status history | Every status transition with optional actor and reason | `tickets.status` stores current state | No historical status transition rows | IMPLEMENT NOW: add `ticket_status_history` | Step 5 historical traceability |
| Notifications | Stored notifications for residents, coordinators, technicians | No notification table | No durable notification inbox | IMPLEMENT NOW: add `notifications` | Step 5 notification storage requirement |
| Coordinator override auditing | Sensitive coordinator changes with old/new values | No audit table | No append-only audit structure for overrides | IMPLEMENT NOW: add `audit_logs` with JSONB old/new values | Step 5 auditability requirement |
| System/AI history | AI analysis/scoring records by ticket | `ai_analysis_runs`, `ticket_scoring_results` exist | Core AI/scoring history already exists; system status/audit events still need structures | ALREADY SUPPORTED for analysis/scoring; IMPLEMENT NOW for nullable actor status history and audit logs | Existing initial schema and Step 5 system/AI scope |
| Resident additional information request | Coordinator can request more information; resident can submit text/photos | `ticket_attachments` stores ticket-level attachments | Repository docs do not define an exact request/response storage contract | REQUIRES BUSINESS CLARIFICATION: do not add chat/message/comment tables in Step 5 | Step 5 additional-information instruction and repository search |
| Later access-control and RLS preparation | Ownership identifiers derived from authenticated backend relationships | `resident_id` and `unit_id` exist on tickets | Missing structural access bases for resident membership and technician assignment | IMPLEMENT NOW: add memberships and active assignments; DEFER policies/enforcement | Step 5 out-of-scope RLS/API enforcement |

## Deferred Or Clarification Items

- Resident additional-information request/response needs an approved storage contract before adding a table. Existing `ticket_attachments` can continue to attach files directly to a ticket.
- API authorization, authentication, and Supabase RLS policies are deferred to the next access-control step.
- Technician auto-assignment, notification delivery, and status-transition validation services are out of scope for this database-only step.
