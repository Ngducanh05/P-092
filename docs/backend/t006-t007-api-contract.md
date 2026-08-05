# T-006/T-007 API Contract

All FixIt endpoints use `/api/v1` and Supabase Bearer authentication unless noted.

| Method | Path | Role | Request | Response | Authorization |
|---|---|---|---|---|---|
| GET | `/auth/me` | authenticated | none | local user profile and active memberships | Valid token, profile auto-created only as resident |
| GET | `/units/my` | resident | none | active linked units | Active membership |
| POST | `/storage/ticket-attachments/upload-url` | resident | image metadata | signed upload target | Server-generated private path |
| POST | `/tickets` | resident | title, description, optional unit/location/paths | ticket | Transaction creates ticket, status history, attachments |
| GET | `/tickets/my` | resident | filters/page | ticket page | Active unit membership |
| GET | `/tickets/{ticket_id}` | resident/coordinator | path id | ticket | Resident ownership or coordinator MVP system-wide read |
| GET | `/coordinator/tickets` | coordinator | filters/page | ticket page | System-wide MVP read |
| GET | `/health` | public | none | application, environment, status | No secrets |

Stable errors use `{ "error": { "code", "message", "details", "request_id" } }`. New tickets return `estimated_resolution_at = null` and `estimated_resolution_text = "Đang phân tích"` because SLA/ETA rules are deferred.
