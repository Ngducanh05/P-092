> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Operational Schema

The operational schema contains:

- `residents`
- `bql_staff`
- `technician_profiles`
- `technician_skills`
- `resident_unit_memberships`
- `tickets`
- `ticket_assignments`
- `ticket_attachments`
- `ticket_attachment_upload_sessions`
- `ticket_status_history`
- `notifications`
- `audit_logs`
- `ai_analysis_runs`
- `ticket_scoring_results`

`public.users` and `role_enum` remain removed. Technician workflow is restored by additive revision `f6a7b8c9d0e1` using Auth UUID profiles.
