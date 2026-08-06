# Access-Control Matrix

Actors: RESIDENT, BQL, SYSTEM / AI, SERVICE ROLE, ANONYMOUS.

| Table | RESIDENT | BQL | SYSTEM / AI | SERVICE ROLE | ANONYMOUS |
| --- | --- | --- | --- | --- | --- |
| `residents` | Own active profile | Deny | Backend only | Admin provisioning | Deny |
| `bql_staff` | Deny | Own active profile | Backend only | Admin provisioning | Deny |
| `resident_unit_memberships` | Own active rows | Backend read | Backend only | Backend only | Deny |
| `units` | Active membership rows | Backend read | Backend only | Backend only | Deny |
| `tickets` | Active membership ownership | BQL system-wide MVP read | Backend transitions | Backend only | Deny |
| `ticket_attachments` | Authorized parent ticket | Authorized parent ticket | Backend only | Backend only | Deny |
| `ticket_attachment_upload_sessions` | Backend endpoint only | Deny | Backend only | Backend only | Deny |
| `notifications` | `recipient_auth_user_id = auth.uid()` | `recipient_auth_user_id = auth.uid()` | Backend only | Backend only | Deny |
| `audit_logs` | Deny | Deny | Backend only | Backend only | Deny |
| `ai_analysis_runs` | Deny | Backend projection only | Backend only | Backend only | Deny |
| `ticket_scoring_results` | Deny | Backend projection only | Backend only | Backend only | Deny |

Direct client mutations remain denied where backend business logic owns changes.
