> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Supabase Profile Migration Remediation

Historical migrations aligned `public.users` with Supabase Auth. The final architecture replaces that table with `residents` and `bql_staff`.

For current remediation, verify:

- Resident Auth UUIDs exist in `residents`.
- BQL Auth UUIDs exist in `bql_staff`.
- No Auth UUID appears in both profile tables.
- BQL profiles are provisioned only through backend administrative tooling.
