> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Data Ownership Matrix

| Data | Owner | Access Rule |
| --- | --- | --- |
| Resident profile | Resident | Own active profile. |
| BQL profile | BQL | Own active profile; trusted provisioning only. |
| Technician profile/skills | Operations / Technician | BQL roster read; Technician own read; trusted provisioning. |
| Unit membership | Resident operations | Resident reads own active memberships. |
| Ticket | Resident issue workflow | Resident by active membership; BQL system-wide MVP read; Technician by active assignment. |
| Assignment | BQL/Technician workflow | BQL operational read; assigned Technician own active rows. |
| Attachments | Ticket parent | Access follows authorized parent Ticket. |
| Upload sessions | Backend Storage workflow | Backend-only direct table access. |
| Notifications | Recipient Auth UUID | Recipient only. |
| Audit logs | Security/operations | Backend/service only. |
| AI/scoring | Internal automation | Backend/service only unless safely projected. |
