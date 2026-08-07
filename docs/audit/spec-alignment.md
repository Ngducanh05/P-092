# Đối chiếu P-092 với Self Dev v2/v3

## Nguồn đối chiếu

- `Self_Dev_Docs/PRD_v2.md`
- `Self_Dev_Docs/dac_ta_tinh_nang_luong_nghiep_vu_v2.md`
- `Self_Dev_Docs/Logic_xử_lý_chính_v2.md`
- `Self_Dev_Docs/dexuatdb_API-_v2.md`
- `Self_Dev_Docs/WireFrame và UI Flow _v3.html`

Self Dev là chuẩn; tài liệu/code v1 hoặc Technician trước đây chỉ giữ để truy vết migration.

## Ma trận alignment

| Self Dev | Trạng thái P-092 sau refactor | Ghi chú |
| --- | --- | --- |
| Chỉ Resident + Coordinator | Đã căn chỉnh | Runtime Technician/assignment bị loại bỏ |
| Resident phone OTP | Đã căn chỉnh backend | OTP có thể do Supabase Auth xử lý trực tiếp |
| Coordinator email/password | Đã căn chỉnh backend | Trusted provision `user_profiles.role=COORDINATOR` |
| `user_profiles` + `resident_profiles` | Đã căn chỉnh | Physical schema hiện ở `public` |
| Nhiều resident account cùng unit | Đã căn chỉnh | `resident_profiles.unit_id` không unique; first bind primary |
| Catalog building/floor/unit/location | Đã căn chỉnh | Vị trí bắt buộc, kiểm tra cùng building/unit |
| 11 Category chuẩn | Đã căn chỉnh | Code cố định đúng v2 |
| Priority chỉ P1/P2/P3 | Đã căn chỉnh | P0 tách khỏi Priority |
| Business status v2 | Đã căn chỉnh | NEW/WAITING/APPROVED/IN_PROGRESS/COMPLETED/UNRESOLVABLE/CANCELLED |
| Classification status riêng | Đã căn chỉnh | PENDING/PROCESSING/RESOLVED/MANUAL_REVIEW/FAILED |
| Resident create/list/detail/cancel/supplement | Đã căn chỉnh API lõi | Signed upload là extension bảo mật |
| Resident không thấy raw P/score/SLA | Đã căn chỉnh | Chỉ trả mô tả Priority/ETA thân thiện |
| Notification list/read | Đã căn chỉnh |
| Coordinator dashboard/filter/search | Đã căn chỉnh |
| Manual review P0 | Đã căn chỉnh |
| Request information | Đã căn chỉnh |
| Approve/start/complete/unresolvable | Đã căn chỉnh | Coordinator xử lý trực tiếp, không assignment |
| Override Category/Priority + reason + audit | Đã căn chỉnh |
| Audit logs | Đã căn chỉnh |
| Ticket/SLA reports + CSV | Đã căn chỉnh API lõi |
| Scoring formula v2 | Đã căn chỉnh | Coordinator load active `scoring_rule_versions.config`; AI worker còn thiếu persistence `rule_version_id` |
| Category Ceiling | Đã căn chỉnh | Đọc từ category catalog |
| SLA P3/P2/P1 = 5m/3h/72h | Đã căn chỉnh |
| Density distinct unit / 3 ngày / tầng kề | Đã căn chỉnh phép tính | Duplicate-blocking sau khi biết Category còn cần tích hợp |
| AI Agent output boundary | Đã căn chỉnh schema | Product worker/Agent thật chưa triển khai |
| Image semantic readability gate trước insert | Chưa hoàn thành | Không được coi metadata check là semantic check |
| AI job/outbox/internal worker APIs | Chưa hoàn thành |
| Incident rebuild automation | Chưa hoàn thành |
| Push/SMS dispatch | Chưa hoàn thành | IN_APP persistence/event creation có |
| Idempotency/optimistic locking client transport | Chưa hoàn thành | Self Dev chưa quy định persistence/header cụ thể |
| Multi-label category-match rule | Chưa triển khai | Self Dev yêu cầu lead chốt thêm |
| `POST /tickets` multipart transport | Khác biệt có chủ đích, đã ghi nhận | Runtime dùng signed-upload session; cần adapter multipart nếu FE khóa contract nguyên văn |
| Schema `app`/`ai_private`/`audit` | Namespace chưa tách | Self Dev mô tả đây là kiến trúc đề xuất; physical cutover hiện ở `public` |

## Những phần legacy đã loại khỏi runtime

```text
technician_profiles
technician_skills
ticket_assignments
assignment_status_enum
/api/v1/technician/*
/api/v1/bql/technicians
/api/v1/bql/tickets/{id}/assign
require_technician
provision_technician.py
```

Migration lịch sử `f6a7b8c9d0e1` vẫn được giữ nguyên. Việc xóa runtime schema cũ được thực hiện bằng migration forward `a7b8c9d0e1f2`.
