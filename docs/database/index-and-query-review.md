> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

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
