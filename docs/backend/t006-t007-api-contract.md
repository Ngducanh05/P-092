> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# T-006/T-007 API Contract

Canonical protected paths use the `/api/v1` prefix. Supabase Bearer tokens determine the actor; client-supplied role values are ignored.

| Method | Path | Actor | Notes |
| --- | --- | --- | --- |
| GET | `/auth/me` | Resident/BQL/Technician | Actor-discriminated profile response. |
| GET | `/units/my` | Resident | Active Resident memberships. |
| POST | `/storage/ticket-attachments/upload-url` | Resident | Private signed upload target; no raw Storage path returned. |
| POST | `/tickets` | Resident | Ticket owner comes from the authenticated Resident. |
| GET | `/tickets/my` | Resident | Tickets reachable through active Resident memberships. |
| GET | `/tickets/{ticket_id}` | Resident/BQL | Resident-scoped read or BQL system-wide read. |
| GET | `/tickets/{ticket_id}/attachments/{attachment_id}/download-url` | Resident/BQL | Authorized parent ticket required; signed URL only. |
| GET | `/bql/tickets` | BQL | System-wide queue ordered P3, P2, P1, then legacy/unknown values. |
| GET | `/bql/technicians` | BQL | Active Technician roster with skills and availability. |
| POST | `/bql/tickets/{ticket_id}/assign` | BQL | Assigns an eligible waiting ticket atomically. |
| GET | `/technician/assignments` | Technician | Own active assignments only. |
| GET | `/technician/assignments/{assignment_id}` | Technician | Own active assignment detail; foreign records are masked as 404. |
| GET | `/technician/assignments/{assignment_id}/attachments/{attachment_id}/download-url` | Technician | Signed URL for an attachment on the owned active assignment. |
| POST | `/technician/assignments/{assignment_id}/accept` | Technician | `assigned -> accepted`. |
| POST | `/technician/assignments/{assignment_id}/status` | Technician | `accepted -> in_progress` or active state -> `unable_to_handle`. |

Assignment creates status history, audit data, and Technician/Resident notifications in one backend transaction. Completion is deliberately rejected with `COMPLETION_EVIDENCE_REQUIRED` until a Technician-owned signed-upload contract exists. `/coordinator` is not canonical.
