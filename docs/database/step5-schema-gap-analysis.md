> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Schema Gap Analysis

The generic `public.users` design was correctly replaced by Auth-linked actor profiles. Revision `e5f6a7b8c9d0` also removed Technician structures, which conflicted with the lead specifications. Revision `f6a7b8c9d0e1` corrects that gap without restoring generic roles.

Current Technician-phase gap: secure Technician-owned completion-photo upload and consumption.

Priority/P0/Category/Severity and AI-scoring alignment remain separate approved work phases.
