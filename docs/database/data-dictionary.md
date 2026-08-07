> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Data Dictionary

## Actor tables

- `residents`: Auth-linked Resident profile with unique E.164 phone.
- `bql_staff`: Auth-linked BQL profile with unique email.
- `technician_profiles`: Auth-linked Technician profile with email, optional contact fields, `is_active`, and `is_available`.
- `technician_skills`: unique `(technician_id, category)` qualifications.

The application has no `public.users` table and no `role_enum`.

## Assignment tables

- `ticket_assignments.ticket_id -> tickets.id`
- `ticket_assignments.technician_id -> technician_profiles.id`
- `ticket_assignments.assigned_by_auth_user_id -> auth.users.id` in PostgreSQL
- `status`: `assigned`, `accepted`, `in_progress`, `completed`, `unable_to_handle`
- `assignment_note`: optional BQL routing note
- `work_note`: Technician cause/material/action note
- `unable_reason`: required when status is `unable_to_handle`
- a partial unique index enforces one active assignment per Ticket

## Shared identity references

- `ticket_status_history.changed_by_auth_user_id -> auth.users.id`
- `notifications.recipient_auth_user_id -> auth.users.id`
- `audit_logs.actor_auth_user_id -> auth.users.id`
