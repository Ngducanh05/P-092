# Data Ownership Matrix

| Data | Owner | Access Rule |
| --- | --- | --- |
| Resident profile | Resident | Own active profile. |
| BQL profile | BQL | Own active profile; backend provisioning only. |
| Unit membership | Resident operations | Resident reads own active memberships. |
| Ticket | Resident issue workflow | Resident via active membership; BQL system-wide MVP read. |
| Attachments | Ticket parent | Access follows authorized parent ticket. |
| Upload sessions | Backend Storage workflow | Backend-only direct table access. |
| Notifications | Recipient auth UUID | Recipient only. |
| Audit logs | Security/operations | Backend/service only. |
| AI/scoring | Internal automation | Backend/service only unless projected safely. |
