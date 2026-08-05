# Data Ownership Matrix

| Entity/table | Business owner | Authorization key | Read basis | Write basis | Sensitive fields | History requirement | Deletion behavior |
|---|---|---|---|---|---|---|---|
| `users` | Account management | `users.id`, `users.role` | Backend/service only until identity model is approved | Backend/service only | `email`, `full_name`, role | Preserve user references | Deactivation preferred |
| `units` | Property operations | `units.id` | Backend/service; resident through membership for ticket access | Backend/service only | Unit identifiers | Preserve ticket links | Deactivation preferred |
| `user_unit_memberships` | Residency management | `(user_id, unit_id, is_active)` | User through approved identity; backend/service currently | Backend/service with audit | Membership link | Preserve link/unlink history | `is_active`, `unlinked_at` |
| `technician_profiles` | Operations | `user_id` | Technician self access when identity is approved; backend/service currently | Backend/service with audit | Availability | Preserve assignment links | Deactivation preferred |
| `technician_skills` | Operations | `technician_id`, `category` | Backend/coordinator workflow | Backend/service with audit | Skill categories | Current capability history limited | Profile-owned, restricted |
| `tickets` | Resident issue workflow | `unit_id`, active membership; active assignment | Resident own unit, technician active assignment, coordinator managed scope pending | Backend-controlled | Description, location | Preserve operational record | Hard delete exceptional |
| `ticket_attachments` | Ticket workflow | Parent `ticket_id` | Derived from parent ticket access | Backend/service only | `file_url`, file metadata | Preserve with ticket | Cascades with physical ticket delete |
| `ticket_assignments` | Coordinator workflow | Active `technician_id`, `ticket_id` | Technician assigned rows; coordinator scope pending | Backend/service with audit | Assignment routing | Append history | `is_active`, `ended_at` |
| `ticket_status_history` | Ticket workflow | Parent `ticket_id` | Derived from parent ticket access | Backend/service with audit | Status reason | Append-only | Cascades with physical ticket delete |
| `ai_analysis_runs` | System/AI | Parent `ticket_id` | Backend/service only | System/service only | Summary, confidence, model metadata | Preserve analysis history | Cascades with physical ticket delete |
| `ticket_scoring_results` | System/AI | Parent `ticket_id` | Backend/service only; no client scoring breakdown by default | System/service only | Score breakdown, reasons | Preserve scoring history | Cascades with physical ticket delete |
| `notifications` | Notification workflow | `recipient_user_id` | Recipient only when identity is approved | Backend/service only | Message body | Product decision pending | Retention pending |
| `audit_logs` | Security/governance | `entity_type`, `entity_id`, `actor_user_id` | Service/security review only | Service-only insert | Old/new values, metadata | Append-only | No client update/delete |

