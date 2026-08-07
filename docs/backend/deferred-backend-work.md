> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Deferred Backend Work

Items intentionally outside the Technician-restoration phase:

| Area | Status |
| --- | --- |
| Secure Technician-owned completion-photo upload and atomic completion transition | Required follow-up |
| Full P0/Priority/Category/Severity contract alignment | Separate lead-spec phase |
| Final AI scoring rules and numeric matrices from pipeline section H | Blocked by missing approved matrices |
| Density and P1 batching | Separate lead-spec phase |
| Notification delivery provider (push/SMS) | Adapter integration pending |
| Report export and resident rating clarification | Pending/needs product clarification |
| Celery + Redis task execution | Separate infrastructure phase |
| Next.js frontend | Separate frontend workspace/deliverable |
| Live production migration | Requires explicit confirmed safe action |

Technician identity, skills, assignment persistence, BQL assignment, Technician work access, assignment audit/history/notifications, provisioning, and assignment-scoped RLS are no longer deferred.
