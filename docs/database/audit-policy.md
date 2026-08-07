> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Audit Policy

Audit logs are backend-controlled append-only operational records.

- `audit_logs.actor_auth_user_id` stores the Supabase Auth UUID for Resident, BQL, or Technician actions.
- System/AI actions may store null.
- Assignment creation and Technician assignment-state changes write old/new state evidence.
- Audit payloads must never contain passwords, OTPs, access tokens, service keys, authorization headers, or private Storage URLs.

Audit values and metadata are not exposed directly to clients.
