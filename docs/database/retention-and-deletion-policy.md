# Retention And Deletion Policy

No authoritative retention durations are defined in the repository. For every table, retention period is REQUIRES BUSINESS/LEGAL CLARIFICATION.

| Table | Deletion policy | Retention period |
|---|---|---|
| `users` | Deactivation preferred | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `units` | Deactivation preferred | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `user_unit_memberships` | `is_active=false` and `unlinked_at` | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `technician_profiles` | Deactivation preferred | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `technician_skills` | Preserve unless profile capability cleanup approved | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `tickets` | Preserve operational history; hard delete exceptional | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `ticket_attachments` | Private storage lifecycle policy required | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `ticket_assignments` | Append history; use `is_active=false`, `ended_at` | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `ticket_status_history` | Append-only | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `ai_analysis_runs` | Preserve according to approved retention policy | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `ticket_scoring_results` | Preserve according to approved retention policy | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `notifications` | Product decision required | REQUIRES BUSINESS/LEGAL CLARIFICATION |
| `audit_logs` | Append-only; hard delete requires approval | REQUIRES BUSINESS/LEGAL CLARIFICATION |

Hard deletes require backup, approval, and a documented reason. Never test destructive migration behavior against production Supabase.

