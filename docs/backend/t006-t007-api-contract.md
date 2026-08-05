# T-006/T-007 API Contract

All FixIt endpoints use `/api/v1` and Supabase Bearer authentication unless noted.

| Method | Path | Role | Request | Response | Authorization |
|---|---|---|---|---|---|
| GET | `/auth/me` | authenticated | none | local user profile and active memberships | Valid token, profile auto-created only as resident |
| GET | `/units/my` | resident | none | active linked units | Active membership |
| POST | `/storage/ticket-attachments/upload-url` | resident | image metadata | upload session ID and signed upload target | Server-generated private path stored server-side |
| POST | `/tickets` | resident | title, description, optional unit/location/upload IDs | ticket | Transaction creates ticket, status history, attachments, and consumes upload sessions |
| GET | `/tickets/my` | resident | filters/page | ticket page | Active unit membership |
| GET | `/tickets/{ticket_id}` | resident/coordinator | path ID | ticket | Resident ownership or coordinator MVP system-wide read |
| GET | `/tickets/{ticket_id}/attachments/{attachment_id}/download-url` | resident/coordinator | path IDs | signed download URL | Authorized parent ticket and attachment ownership |
| GET | `/coordinator/tickets` | coordinator | filters/page | ticket page | System-wide MVP read |
| GET | `/health` | public | none | application, environment, status | No secrets |
| GET | `/ready` | public | none | readiness status and safe check labels | No hosts, URLs, credentials, or stack traces |

Stable errors use `{ "error": { "code", "message", "details", "request_id" } }`.

New tickets return `estimated_resolution_at = null` and `estimated_resolution_text = "Đang phân tích"` until SLA/ETA rules are approved.

`/ready` is a shallow operational readiness endpoint. It checks database connectivity, the current Alembic revision where practical, and whether Supabase Auth/Storage settings are present. It is not a complete Supabase end-to-end test and does not replace `tests/integration`.

Attachment upload flow:

1. The resident requests `/storage/ticket-attachments/upload-url` with filename, MIME type, and size.
2. The backend creates a pending `ticket_attachment_upload_sessions` row only after Supabase returns a signed upload credential.
3. The frontend uploads directly to the private Supabase bucket.
4. The resident creates a ticket with `attachment_upload_ids`.
5. The backend locks and verifies each upload session, verifies the Storage object metadata, creates attachment rows, marks sessions consumed, and commits in one transaction.

Normal ticket responses never expose raw private storage paths.
