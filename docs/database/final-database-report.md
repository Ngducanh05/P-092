> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Final Database Report

Status: Technician restoration is statically implemented after the Resident/BQL actor refactor. **NOT TESTED ON LIVE POSTGRESQL** by default.

## Actor model

- `auth.users` stores authentication identity.
- `public.residents`, `public.bql_staff`, and `public.technician_profiles` store mutually exclusive business profiles.
- `public.users` and `role_enum` remain removed.

## Technician workflow

`technician_skills` and `ticket_assignments` support skill-aware BQL routing, own-assignment Technician access, state history, notifications, and audit evidence. One partial unique index allows at most one active assignment per Ticket.

## Security

RLS uses `auth.uid()` and is forced on final business tables. Resident access follows active membership, BQL uses active profile authorization, and Technician access follows active assignment ownership. Direct client mutations remain denied.

Legacy ticket status values remain for migration compatibility. The active Technician path now generates `assigned`, `in_progress`, and `waiting_assignment` transitions. Secure completion evidence remains intentionally blocked pending a Technician-owned upload contract.

Live migration and live Supabase token tests require explicit user approval and configured development credentials.
