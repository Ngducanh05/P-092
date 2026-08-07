# Index and Query Review

Hot-path indexes include:

- Resident membership and upload-session indexes
- Ticket status-history and notification indexes
- `ix_technician_profiles_email`
- `ix_technician_profiles_active_available`
- `ix_technician_skills_category`
- `ix_ticket_assignments_technician_active`
- `ix_ticket_assignments_ticket_assigned_at`
- `uq_ticket_assignments_one_active_per_ticket`

BQL and Technician queues order business priorities P3, P2, then P1. Technician ownership predicates always include `technician_id` and active assignment state.
