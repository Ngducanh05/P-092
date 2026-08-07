# Tiến độ triển khai P-092 theo Self Dev v2/v3

Tài liệu này ghi nhận trạng thái **sau khi refactor P-092 theo bộ `Self_Dev_Docs` làm source of truth**. Các tài liệu/flow Technician trước đây chỉ còn giá trị lịch sử migration và không còn là chuẩn sản phẩm.

## 1. Source of truth đã khóa

Bộ tài liệu hiện hành:

1. `Self_Dev_Docs/PRD_v2.md`
2. `Self_Dev_Docs/dac_ta_tinh_nang_luong_nghiep_vu_v2.md`
3. `Self_Dev_Docs/Logic_xử_lý_chính_v2.md`
4. `Self_Dev_Docs/dexuatdb_API-_v2.md`
5. `Self_Dev_Docs/WireFrame và UI Flow _v3.html`

`Self_Dev_Docs/ai_evaluation_metrics_v1.md` tiếp tục được dùng cho tiêu chí đánh giá AI vì chưa có bản mới hơn thay thế phần này.

Các file v1 khác chỉ giữ để truy vết lịch sử khi đã có v2/v3 tương ứng.

## 2. Quyết định kiến trúc đã căn chỉnh

| Hạng mục | Trạng thái | Kết quả |
| --- | --- | --- |
| Actor người dùng | Đã căn chỉnh | Chỉ còn `RESIDENT` và `COORDINATOR`; System/AI chạy nền |
| Technician/assignment | Đã loại khỏi runtime | Không còn route, service, repository hoặc ORM Technician/assignment |
| Identity | Đã căn chỉnh | Supabase `auth.users -> user_profiles -> resident_profiles` |
| Resident auth | Đã căn chỉnh backend | SĐT + OTP qua Supabase Auth |
| Coordinator auth | Đã căn chỉnh backend | Email + password; role `COORDINATOR` chỉ được trusted provisioning |
| Ticket lifecycle | Đã căn chỉnh | NEW/WAITING_RESIDENT_INFO/APPROVED/IN_PROGRESS/COMPLETED/UNRESOLVABLE/CANCELLED |
| Classification lifecycle | Đã căn chỉnh | PENDING/PROCESSING/RESOLVED/MANUAL_REVIEW/FAILED |
| P0 | Đã căn chỉnh | P0 = `MANUAL_REVIEW`, không phải Priority |
| Priority | Đã căn chỉnh | Chỉ P1/P2/P3 |
| Category | Đã căn chỉnh | Đúng 11 Category của Self Dev v2 |
| Severity | Đã căn chỉnh | LOW/MEDIUM/HIGH |
| Coordinator workflow | Đã căn chỉnh | BQL tự review/approve/start/complete/unresolvable, không assign Technician |
| Resident privacy | Đã căn chỉnh | Không trả raw Priority, score/breakdown hoặc thuật ngữ SLA cho Resident |
| Backend ownership | Đã căn chỉnh | Backend suy ra actor/unit/ownership từ token + DB, không tin ID/role client gửi |

## 3. Database runtime sau refactor

Các bảng canonical đã được đưa vào ORM/migration:

```text
user_profiles
resident_profiles
buildings
floors
units
location_types
locations
categories
scoring_rule_versions
tickets
ticket_attachments
ai_analysis_runs
ticket_status_history
information_requests
incident_cases
incident_case_members
notifications
audit_logs
```

Backend giữ thêm:

```text
ticket_attachment_upload_sessions
```

để hỗ trợ signed-upload một lần cho private Storage. Đây là extension bảo mật ở lớp transport, không phải bảng nghiệp vụ mới thay thế Self Dev.

### Identity và unit binding

```text
auth.users
    |
    v
user_profiles
    |
    +-- role=RESIDENT ----> resident_profiles ----> units
    |
    +-- role=COORDINATOR
```

- Một user profile có một role nghiệp vụ.
- Resident bind đúng một unit.
- Một unit có thể có nhiều tài khoản Resident.
- Tài khoản bind đầu tiên được đánh dấu `is_primary=true`; các tài khoản sau có quyền nghiệp vụ ngang nhau ở MVP.

## 4. Migration forward theo Self Dev

Migration lịch sử `f6a7b8c9d0e1` đã tồn tại nên **không bị sửa**.

Revision mới:

```text
f6a7b8c9d0e1
        |
        v
a7b8c9d0e1f2
```

`a7b8c9d0e1f2_align_self_dev_v2.py` thực hiện forward cutover theo Self Dev v2/v3:

- tạo mô hình `user_profiles` / `resident_profiles`;
- tạo building/floor/unit/location catalog;
- tạo Category catalog và scoring rule version;
- remodel `tickets` theo business/classification state tách biệt;
- tạo information request, incident, notification và audit schema;
- loại bỏ runtime Technician/assignment legacy;
- seed các Category, location type và scoring rule chuẩn;
- cập nhật RLS theo hai actor;
- có preflight fail-closed để không xóa dữ liệu operational legacy âm thầm.

Nếu phát hiện dữ liệu legacy không thể cutover an toàn, migration dừng bằng:

```text
SELF_DEV_V2_CUTOVER_REQUIRES_MANUAL_DATA_MIGRATION
```

Revision này là **forward-only**. Không dùng downgrade để giả lập rollback dữ liệu.

### Trạng thái migration thực tế

- Alembic local head: `a7b8c9d0e1f2`.
- Offline PostgreSQL SQL generation: PASS.
- Revision `a7b8c9d0e1f2` **chưa được chạy lên Supabase/live database**.
- Không sửa, stamp hoặc downgrade migration `f6a7b8c9d0e1` đã tồn tại.

## 5. API đã căn chỉnh

### Auth / hồ sơ

```text
POST /api/v1/auth/otp/request
POST /api/v1/auth/otp/verify
GET  /api/v1/me
POST /api/v1/me/bind-unit
```

### Catalog

```text
GET /api/v1/catalog/locations
GET /api/v1/catalog/categories
```

Catalog location của Resident chỉ cho phép common-area trong building hoặc location thuộc chính unit của Resident; không lộ unit khác trong cùng tòa.

### Cư dân

```text
POST /api/v1/storage/ticket-attachments/upload-url
POST /api/v1/tickets
GET  /api/v1/tickets
GET  /api/v1/tickets/{ticket_id}
POST /api/v1/tickets/{ticket_id}/cancel
POST /api/v1/tickets/{ticket_id}/supplements
GET  /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url
GET  /api/v1/notifications
POST /api/v1/notifications/{notification_id}/read
```

### Điều phối viên

```text
GET   /api/v1/coordinator/tickets
GET   /api/v1/coordinator/tickets/{ticket_id}
POST  /api/v1/coordinator/tickets/{ticket_id}/manual-review/resolve
POST  /api/v1/coordinator/tickets/{ticket_id}/request-information
POST  /api/v1/coordinator/tickets/{ticket_id}/approve
PATCH /api/v1/coordinator/tickets/{ticket_id}/classification
POST  /api/v1/coordinator/tickets/{ticket_id}/start
POST  /api/v1/coordinator/tickets/{ticket_id}/complete
POST  /api/v1/coordinator/tickets/{ticket_id}/unresolvable
GET   /api/v1/coordinator/tickets/{ticket_id}/attachments/{attachment_id}/download-url
GET   /api/v1/coordinator/audit-logs
GET   /api/v1/coordinator/reports/tickets-summary
GET   /api/v1/coordinator/reports/sla-performance
POST  /api/v1/coordinator/reports/export
```

Không còn:

```text
/api/v1/technician/*
/api/v1/bql/technicians
/api/v1/bql/tickets/{id}/assign
```

## 6. API envelope và error contract

Actor-facing API dùng envelope:

```json
{
  "data": {},
  "meta": {},
  "error": null,
  "request_id": "uuid"
}
```

Error dùng:

```json
{
  "data": null,
  "error": {
    "code": "STABLE_ERROR_CODE",
    "message": "..."
  },
  "request_id": "uuid"
}
```

Middleware tạo/chuẩn hóa `X-Request-ID`, trả lại response header và đưa `request_id` vào audit log.

## 7. Scoring đã căn chỉnh

Backend tính theo Self Dev:

```text
Score = Category base + (Location x Category) + Density + Severity
```

Đã triển khai:

- Category base chuẩn;
- location bonus chuẩn;
- density cho WATER_LEAK/ELECTRICAL_SHORT;
- severity score;
- threshold P1/P2/P3;
- category Priority Ceiling;
- red flag ép P3 và bypass score/ceiling;
- SLA P3=5 phút, P2=3 giờ, P1=72 giờ;
- runtime Coordinator đọc `scoring_rule_versions.config` của rule active thay vì hard-code toàn bộ rule production.

Density dùng `COUNT(DISTINCT source_unit_id)` trong cửa sổ 3 ngày và cùng/tầng liền kề.

## 8. Ranh giới Backend <-> AI

Contract nội bộ đã được khóa trong `src/models/agent_schemas.py`.

Agent request chứa:

```text
ticket_id
text
image.storage_bucket
image.object_path
rule_version_id
```

Agent chỉ được trả:

```text
text_categories
red_flag_text
image_categories
red_flag_signal
severity
severity_source
text_model_version
vision_model_version
error_code
```

Backend chịu trách nhiệm Category match, scoring, final Priority, ceiling và state transition.

Generic Chat/LangGraph demo cũ đã bị loại khỏi runtime để không giả vờ đó là product AI pipeline. Dependency LangGraph vẫn được giữ để triển khai agent thật ở phase AI tiếp theo.

## 9. Validation đã chạy trong workspace này

| Command/check | Kết quả |
| --- | --- |
| `python -m compileall -q src alembic/versions scripts tests` | PASS |
| `python -m pytest tests -q` | PASS — `92 passed` |
| `python scripts/scan_secrets.py` | PASS — không phát hiện secret |
| `python -m alembic heads` | PASS — `a7b8c9d0e1f2 (head)` |
| `python -m alembic history` | PASS — migration chain tuyến tính `f6 -> a7` |
| `git diff --check` | PASS |
| Offline migration `f6:a7 --sql` với PostgreSQL dialect | PASS — 751 dòng SQL được sinh |
| FastAPI route listing | PASS — chỉ còn Resident/Coordinator + catalog/storage extensions, không có Technician |
| `python -m pip check` | Môi trường hệ thống có conflict ngoài repo: `moviepy 2.2.1` yêu cầu Pillow `<12`, hiện là `12.2.0` |
| Ruff | Không chạy được trong Linux workspace vì module `ruff` không được cài; executable trong `.venv` của project là Windows-only |

Không thay thế hai kết quả môi trường cuối bằng kết quả giả. Khi mở project trong `.venv` Windows gốc, chạy lại `pip check` và Ruff trước commit/deploy.

## 10. Những phần chưa được ghi nhận sai là hoàn thành

Các khoảng trống còn lại được ghi chi tiết tại `docs/audit/remaining-spec-gaps.md`:

1. semantic image-quality gate trước khi insert ticket có ảnh (`IMAGE_UNREADABLE`);
2. product AI worker/queue/outbox thực tế;
3. multi-label Category matching chưa được Self Dev chốt;
4. duplicate blocking cùng unit + Category + location trong 3 ngày tại đúng điểm pipeline;
5. AI worker phải persist `rule_version_id` và production fail-closed khi thiếu active scoring rule;
6. Idempotency-Key persistence và optimistic-lock transport chưa được Self Dev quy định đủ chi tiết;
7. PUSH/SMS dispatcher production;
8. optional physical schema split `app` / `ai_private` / `audit` nếu lead chốt triển khai đề xuất này;
9. live Supabase cutover/validation của revision `a7b8c9d0e1f2`;
10. `POST /tickets` hiện dùng signed-upload session thay vì multipart transport nguyên văn của tài liệu Self Dev.

## 11. Kết luận phase refactor

P-092 hiện đã được chuyển từ kiến trúc cũ ba actor/Technician sang runtime hai actor theo Self Dev v2/v3 ở các lớp:

```text
Domain enums
Database ORM
Forward migration
Supabase Auth integration
Authorization
Resident profile/unit binding
Ticket workflow
Classification workflow
Coordinator workflow
RLS
Catalog
Notifications
Audit
Reports
Scoring runtime
AI boundary contract
OpenAPI
Tests
Documentation
```

Self Dev tiếp tục là chuẩn bắt buộc. Nếu code/tài liệu cũ mâu thuẫn với Self Dev, ưu tiên Self Dev và thực hiện thay đổi bằng forward migration/API refactor có kiểm chứng; không sửa migration đã áp dụng trong lịch sử.
