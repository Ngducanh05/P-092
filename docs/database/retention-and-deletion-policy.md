> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Retention and Deletion Policy

Actor profile IDs map to Supabase Auth identities and may be referenced by historical records, so deactivation is preferred over deletion.

- Deactivate `residents.is_active`.
- Deactivate `bql_staff.is_active`.
- Deactivate `technician_profiles.is_active` and stop new assignment.
- End or preserve assignment history rather than deleting it.
- Unlink memberships with `is_active = false` and `unlinked_at`.
- Preserve Tickets, status history, audit logs, notifications, and attachment metadata unless an approved retention process applies.
