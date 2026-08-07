# Data Ownership Matrix

| Data | Owner | Access Rule |
| --- | --- | --- |
| Resident profile | Resident | Own active profile. |
| BQL profile | BQL | Own active profile; trusted provisioning only. |
| Technician profile/skills | Operations / Technician | BQL roster read; Technician own read; trusted provisioning. |
| Unit membership | Resident operations | Resident reads own active memberships. |
| Ticket | Resident issue workflow | Resident by active membership; BQL system-wide MVP read; Technician by active assignment. |
| Assignment | BQL/Technician workflow | BQL operational read; assigned Technician own active rows. |
| Attachments | Ticket parent | Access follows authorized parent Ticket. |
| Upload sessions | Backend Storage workflow | Backend-only direct table access. |
| Notifications | Recipient Auth UUID | Recipient only. |
| Audit logs | Security/operations | Backend/service only. |
| AI/scoring | Internal automation | Backend/service only unless safely projected. |
