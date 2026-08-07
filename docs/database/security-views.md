> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Security Views

`resident_ticket_view` is retained with `security_invoker = true` and excludes internal scoring, AI model, audit, and private Storage fields.

Technician access is implemented through assignment-scoped RLS and actor-specific FastAPI response models rather than a broad Technician view. Any future view must use `security_invoker = true`, preserve underlying RLS, and exclude score breakdowns and private Storage paths.
