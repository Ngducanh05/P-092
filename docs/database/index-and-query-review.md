# Index And Query Review

| Query path | Existing support | Decision |
|---|---|---|
| Resident ticket list by active membership and `tickets.unit_id` | `ix_user_unit_memberships_user_active`, `ix_tickets_unit_id` | Retain. |
| Resident filters by status/category/created_at | No composite ticket filter index | Defer until workload is measured; no speculative index. |
| Coordinator dashboard by management scope | Scope model missing | REQUIRES BUSINESS CLARIFICATION; no coordinator-scope index added. |
| Technician active assignment list | `ix_ticket_assignments_technician_active` | Retain. |
| Technician assignment chronology | `ix_ticket_assignments_ticket_assigned_at` | Retain. |
| Notifications unread inbox | `ix_notifications_recipient_unread_created_at` | Retain. |
| Audit entity lookup | `ix_audit_logs_entity` | Retain. |
| Audit actor lookup | `ix_audit_logs_actor_created_at` | Retain. |
| Status history chronology | `ix_ticket_status_history_ticket_created_at` | Retain. |
| Active assignment uniqueness | `uq_ticket_assignments_one_active_per_ticket` partial unique index | Retain. |

No new performance indexes are added in Step 6-8. RLS and view migration only changes security behavior.

