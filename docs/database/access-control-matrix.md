# Access-Control Matrix

Status: PARTIAL. Runtime identity and coordinator scope are not confirmed, so client-side RLS grants remain denied in the migration.

Legend: DENY, ALLOW OWN ROWS, ALLOW ASSIGNED ROWS, ALLOW MANAGED SCOPE, BACKEND ONLY, SERVICE ONLY, REQUIRES BUSINESS CLARIFICATION.

| Table | RESIDENT | TECHNICIAN | COORDINATOR | ADMIN | SYSTEM / AI | SERVICE ROLE | ANONYMOUS |
|---|---|---|---|---|---|---|---|
| `users` | OWN ROWS requires identity | OWN ROWS requires identity | MANAGED SCOPE requires scope | REQUIRES BUSINESS CLARIFICATION | SERVICE ONLY | SERVICE ONLY | DENY |
| `units` | Through active membership | Assigned ticket context only | MANAGED SCOPE requires scope | REQUIRES BUSINESS CLARIFICATION | BACKEND ONLY | SERVICE ONLY | DENY |
| `user_unit_memberships` | OWN ROWS requires identity | DENY | BACKEND ONLY | REQUIRES BUSINESS CLARIFICATION | DENY | SERVICE ONLY | DENY |
| `technician_profiles` | DENY | OWN ROWS requires identity | BACKEND ONLY | REQUIRES BUSINESS CLARIFICATION | DENY | SERVICE ONLY | DENY |
| `technician_skills` | DENY | OWN ROWS requires identity | BACKEND ONLY | REQUIRES BUSINESS CLARIFICATION | DENY | SERVICE ONLY | DENY |
| `tickets` | ALLOW OWN ROWS through membership when identity approved | ALLOW ASSIGNED ROWS when identity approved | ALLOW MANAGED SCOPE requires scope | REQUIRES BUSINESS CLARIFICATION | BACKEND ONLY | SERVICE ONLY | DENY |
| `ticket_attachments` | Parent ticket ownership | Parent assigned ticket | MANAGED SCOPE requires scope | REQUIRES BUSINESS CLARIFICATION | BACKEND ONLY | SERVICE ONLY | DENY |
| `ticket_assignments` | DENY | ALLOW ASSIGNED ROWS when identity approved | BACKEND ONLY | REQUIRES BUSINESS CLARIFICATION | DENY | SERVICE ONLY | DENY |
| `ticket_status_history` | Parent ticket ownership | Parent assigned ticket | MANAGED SCOPE requires scope | REQUIRES BUSINESS CLARIFICATION | BACKEND ONLY | SERVICE ONLY | DENY |
| `ai_analysis_runs` | DENY | DENY | BACKEND ONLY | REQUIRES BUSINESS CLARIFICATION | SERVICE ONLY | SERVICE ONLY | DENY |
| `ticket_scoring_results` | DENY | DENY | BACKEND ONLY | REQUIRES BUSINESS CLARIFICATION | SERVICE ONLY | SERVICE ONLY | DENY |
| `notifications` | ALLOW OWN ROWS when identity approved | ALLOW OWN ROWS when identity approved | OWN ROWS requires identity | REQUIRES BUSINESS CLARIFICATION | BACKEND ONLY | SERVICE ONLY | DENY |
| `audit_logs` | DENY | DENY | BACKEND/security review only | REQUIRES BUSINESS CLARIFICATION | SERVICE ONLY | SERVICE ONLY | DENY |

## Column Exposure Notes

- AI confidence, model name, AI summary internals: BACKEND ONLY unless product approves public exposure.
- Score total, scoring breakdown, and scoring reasons: SERVICE ONLY or coordinator backend projection; not exposed to residents or technicians by default.
- Internal audit metadata and old/new values: SERVICE ONLY.
- Attachment path in `ticket_attachments.file_url`: CONFIDENTIAL; expose signed URL or path only through backend/storage policy.
- Resident contact information: `users.email`, `users.full_name` are CONFIDENTIAL.
- Technician operational details: `is_available`, `skills` are INTERNAL and coordinator/backend controlled.

