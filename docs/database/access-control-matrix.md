# Access-Control Matrix

Actors: RESIDENT, BQL, TECHNICIAN, SYSTEM / AI, SERVICE ROLE, ANONYMOUS.

| Table | RESIDENT | BQL | TECHNICIAN | SYSTEM / AI | SERVICE ROLE | ANONYMOUS |
| --- | --- | --- | --- | --- | --- | --- |
| `residents` | Own active profile | Deny | Deny | Backend only | Admin provisioning | Deny |
| `bql_staff` | Deny | Own active profile | Deny | Backend only | Admin provisioning | Deny |
| `technician_profiles` | Deny | Active roster read | Own active profile | Backend only | Admin provisioning | Deny |
| `technician_skills` | Deny | Roster read | Own skills | Backend only | Backend only | Deny |
| `resident_unit_memberships` | Own active rows | Backend read | Deny | Backend only | Backend only | Deny |
| `units` | Active membership rows | Backend read | Through assigned Ticket projection | Backend only | Backend only | Deny |
| `tickets` | Active membership ownership | System-wide MVP read | Own active assignments only | Backend transitions | Backend only | Deny |
| `ticket_assignments` | Deny | Operational read | Own active rows | Backend only | Backend only | Deny |
| `ticket_attachments` | Authorized parent | Authorized parent | Assigned parent | Backend only | Backend only | Deny |
| `ticket_attachment_upload_sessions` | Backend endpoint only | Deny | Deny until Technician upload contract exists | Backend only | Backend only | Deny |
| `notifications` | Own recipient rows | Own recipient rows | Own recipient rows | Backend only | Backend only | Deny |
| `audit_logs` | Deny | Backend API only | Deny | Backend only | Backend only | Deny |
| `ai_analysis_runs` | Deny | Safe projection only | Deny | Backend only | Backend only | Deny |
| `ticket_scoring_results` | Deny | Safe projection only | Deny | Backend only | Backend only | Deny |

Direct client mutations remain denied where backend business logic owns changes.
