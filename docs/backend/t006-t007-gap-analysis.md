> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# T-006/T-007 Gap Analysis

## Implemented final actor model

- Resident, BQL, and Technician profiles map directly to Supabase `auth.users`.
- Generic `public.users` and `role_enum` remain removed.
- `/api/v1/bql/tickets` is the canonical BQL queue.
- Technician profiles, skills, assignments, auth resolution, assignment APIs, and assignment-scoped RLS are restored by revision `f6a7b8c9d0e1`.
- Attachment privacy, ticket transaction behavior, Resident membership checks, audit history, and notification ownership are preserved.

## Remaining gap in this phase

Technician completion evidence is not implemented because the existing upload-session contract is Resident-owned. The API rejects `completed` with `COMPLETION_EVIDENCE_REQUIRED`; it does not accept raw object paths or misuse Resident uploads. See `docs/audit/remaining-spec-gaps.md`.

Broader P0/Priority/Category/Severity, AI scoring, Density, batching, reporting, Celery/Redis, and frontend alignment remain separate phases and are not claimed here.
