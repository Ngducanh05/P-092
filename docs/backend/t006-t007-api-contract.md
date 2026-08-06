# T-006/T-007 API Contract

Canonical protected paths:

| Method | Path | Actor | Notes |
| --- | --- | --- | --- |
| GET | `/auth/me` | Resident/BQL | Actor-discriminated profile response. |
| GET | `/units/my` | Resident | Active resident memberships. |
| POST | `/storage/ticket-attachments/upload-url` | Resident | Private signed upload target; no raw Storage path returned. |
| POST | `/tickets` | Resident | Ticket owner is authenticated Resident. |
| GET | `/tickets/my` | Resident | Tickets through active resident memberships. |
| GET | `/tickets/{ticket_id}` | Resident/BQL | Resident scoped read or BQL system-wide MVP read. |
| GET | `/tickets/{ticket_id}/attachments/{attachment_id}/download-url` | Resident/BQL | Authorized parent ticket required; signed URL only. |
| GET | `/bql/tickets` | BQL | Canonical BQL system-wide MVP queue. |

No Technician endpoint exists. `/coordinator` is not canonical.
