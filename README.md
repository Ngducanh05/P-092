# API FixIt Agent

Backend FastAPI dành cho việc tiếp nhận phản ánh sự cố chung cư, phân loại có hỗ trợ AI, điều phối của Ban Quản lý và quy trình phân công công việc cho Kỹ thuật viên. Việc xác thực được ủy quyền cho Supabase Auth; PostgreSQL/Supabase lưu trữ hồ sơ nghiệp vụ và ticket; Row Level Security được sử dụng như một lớp bảo vệ bổ sung trong database.

## Mô hình sản phẩm làm nguồn chuẩn

Hệ thống hiện hỗ trợ ba actor là con người:

- **Cư dân** — đăng nhập bằng OTP qua số điện thoại của Supabase Auth và sử dụng hồ sơ `public.residents`.
- **Điều phối viên BQL** — đăng nhập bằng email/mật khẩu của Supabase Auth và sử dụng hồ sơ `public.bql_staff` được backend provision.
- **Kỹ thuật viên** — đăng nhập bằng email/mật khẩu của Supabase Auth và sử dụng hồ sơ `public.technician_profiles` được backend provision.

Mô hình định danh được chuẩn hóa như sau:

```text
auth.users
├── public.residents
├── public.bql_staff
└── public.technician_profiles
```

Mỗi UUID của Supabase Auth chỉ được thuộc đúng một hồ sơ nghiệp vụ. Ứng dụng **không** khôi phục bảng `public.users` hoặc `role_enum`, đồng thời không bao giờ tin tưởng role do client tự gửi.

## Phase khôi phục Kỹ thuật viên đã triển khai

Alembic revision `f6a7b8c9d0e1` nối trực tiếp sau revision `e5f6a7b8c9d0` và khôi phục:

- `technician_profiles`;
- `technician_skills`;
- `ticket_assignments`;
- `assignment_status_enum`;
- ràng buộc một ticket chỉ có một assignment đang hoạt động;
- cơ chế ngăn một Auth UUID thuộc nhiều actor profile;
- RLS giới hạn theo assignment của Kỹ thuật viên;
- các khóa ngoại từ hồ sơ nghiệp vụ đến `auth.users`.

Migration đã được áp dụng thủ công và xác minh thành công trên Supabase development. Migration production chưa được chạy.

## Vòng đời phân công công việc

BQL chỉ được gán ticket đang ở trạng thái `waiting_assignment`, có Category hợp lệ, cho Kỹ thuật viên đang hoạt động, đang sẵn sàng và có chuyên môn phù hợp với Category đó.

```text
Ticket: waiting_assignment -> assigned -> in_progress
Assignment: assigned -> accepted -> in_progress
Assignment: assigned|accepted|in_progress -> unable_to_handle
Ticket sau unable_to_handle -> waiting_assignment
```

Mỗi lần gán việc sẽ ghi:

- lịch sử trạng thái;
- audit log;
- notification liên quan.

Danh sách công việc của Kỹ thuật viên được sắp xếp theo mức độ khẩn cấp của sản phẩm: P3 trước, sau đó P2 và cuối cùng P1.

P4 hiện vẫn còn tồn tại trong một số hợp đồng dữ liệu cũ vì việc chuẩn hóa Priority nằm ngoài phase migration này.

Cơ chế upload ảnh hoàn thành an toàn cho Kỹ thuật viên chưa được triển khai. Khi yêu cầu chuyển assignment sang `completed`, API trả về `COMPLETION_EVIDENCE_REQUIRED` thay vì chấp nhận đường dẫn object thô hoặc tái sử dụng upload session thuộc sở hữu của Cư dân.

## API

### Endpoint kiểm tra trạng thái hệ thống

- `GET /health`
- `GET /ready`

### Endpoint actor đã xác thực

- `GET /api/v1/auth/me`

### Endpoint Cư dân

- `GET /api/v1/units/my`
- `POST /api/v1/storage/ticket-attachments/upload-url`
- `POST /api/v1/tickets`
- `GET /api/v1/tickets/my`
- `GET /api/v1/tickets/{ticket_id}`
- `GET /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url`

### Endpoint BQL

- `GET /api/v1/bql/tickets`
- `GET /api/v1/bql/technicians`
- `POST /api/v1/bql/tickets/{ticket_id}/assign`

### Endpoint Kỹ thuật viên

- `GET /api/v1/technician/assignments`
- `GET /api/v1/technician/assignments/{assignment_id}`
- `GET /api/v1/technician/assignments/{assignment_id}/attachments/{attachment_id}/download-url`
- `POST /api/v1/technician/assignments/{assignment_id}/accept`
- `POST /api/v1/technician/assignments/{assignment_id}/status`

Quyền của Kỹ thuật viên được xác định từ `sub` trong access token đã được xác minh. Assignment của Kỹ thuật viên khác hoặc ticket chưa được gán sẽ được che dưới phản hồi `404`.

## Provision hồ sơ đặc quyền

Hồ sơ BQL và Kỹ thuật viên không bao giờ được tự động tạo từ token chỉ có email nhưng chưa có hồ sơ được backend xác nhận.

```powershell
python scripts/provision_bql_staff.py --help
python scripts/provision_technician.py --help
```

Quy trình provision Kỹ thuật viên yêu cầu:

- một UUID Supabase Auth đã tồn tại;
- email khớp với tài khoản Auth;
- kiểm tra xung đột với hồ sơ Cư dân hoặc BQL;
- sử dụng SQL có tham số;
- hỗ trợ `--dry-run`;
- không nhận và không lưu mật khẩu.

## Bảo mật

- Backend nhận Supabase access token, không nhận OTP hoặc mật khẩu.
- Quyền sở hữu của Cư dân được suy ra từ hồ sơ đã xác minh và quan hệ căn hộ đang hoạt động.
- Danh tính BQL được suy ra từ hồ sơ `bql_staff` đang hoạt động.
- Kỹ thuật viên chỉ được truy cập các assignment đang hoạt động của chính mình và ticket cha tương ứng.
- Đường dẫn Storage nội bộ, score breakdown, audit payload và service key không được trả về trong các API response thông thường.
- Client không được phép mutation trực tiếp các luồng assignment, audit, AI và scoring; FastAPI thực hiện các transaction do backend kiểm soát.
- Signed URL của Storage có thời hạn ngắn.
- Email-only token không thể tự động trở thành BQL hoặc Kỹ thuật viên.
- Quyền truy cập chéo giữa các Kỹ thuật viên bị chặn ở cả backend và RLS.

## Cấu hình

Sao chép `.env.example` thành `.env` trên máy local và điền thông tin môi trường development.

Không được commit file `.env`.

Các live integration test hỗ trợ các biến sau:

```text
SUPABASE_TEST_RESIDENT_ACCESS_TOKEN
SUPABASE_TEST_BQL_ACCESS_TOKEN
SUPABASE_TEST_TECHNICIAN_ACCESS_TOKEN
```

Giá trị token không được in ra log hoặc commit vào repository.

Migration online còn được bảo vệ bởi safety gate:

```text
ALLOW_LIVE_MIGRATION=true
```

Chỉ bật biến này có chủ đích, trong terminal hiện tại, sau khi đã xác nhận `DATABASE_URL` trỏ đúng môi trường development hoặc test.

## Cài đặt và chạy development

```powershell
python -m pip install -r requirements-dev.txt
python -m uvicorn src.main:app --reload --port 8000
```

Tài liệu API:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Kiểm tra chất lượng

```powershell
python -m pip check
python -m ruff check src tests scripts alembic
python scripts/scan_secrets.py
python -m pytest tests -q
python -m alembic heads
python -m alembic history
git diff --check
```

Kết quả validation gần nhất trên Windows `.venv`:

```text
pip check:         PASS
Ruff:              PASS
Secret scan:       PASS
Pytest:            380 passed, 30 skipped, 1 warning
Alembic local:     f6a7b8c9d0e1 (head)
Supabase dev:      f6a7b8c9d0e1 (head)
git diff --check:  PASS
```

`30 skipped` là các live integration test chưa được bật bằng token Supabase test.

Cảnh báo `StarletteDeprecationWarning` hiện tại đến từ dependency của môi trường test và không làm test suite thất bại.

## Trạng thái Git và migration

Commit hoàn thành phase Kỹ thuật viên:

```text
083598be06c6b27a70f192c4cb6d706dbca2e97a
Restore technician actor and assignment workflow
```

Commit đã được đẩy lên nhánh `main` của repository:

```text
https://github.com/Ngducanh05/P-092
```

Alembic revision hiện tại:

```text
e5f6a7b8c9d0
        ↓
f6a7b8c9d0e1
```

Supabase development đã được nâng cấp thành công lên:

```text
f6a7b8c9d0e1 (head)
```

Production migration chưa được chạy.

Không sử dụng `downgrade`, `stamp` hoặc chỉnh sửa migration cũ đã được áp dụng.

## Ghi chú phạm vi

Thay đổi này hoàn thành phase khôi phục Kỹ thuật viên, bao gồm:

- database schema;
- ORM;
- xác thực ba actor;
- authorization;
- RLS;
- BQL assignment;
- Technician workflow;
- audit;
- notification;
- status history;
- trusted provisioning;
- unit/API test;
- tài liệu;
- migration trên Supabase development.

Các đặc tả của lead còn yêu cầu những phase rộng hơn:

- chuẩn hóa P0;
- loại bỏ Priority P4;
- chuẩn hóa Category và Severity;
- hoàn thiện công thức scoring;
- red-flag override;
- LangGraph AI pipeline;
- Density theo vị trí liền kề;
- batching ticket P1;
- báo cáo và xuất thống kê;
- Celery và Redis;
- Next.js frontend;
- upload ảnh hoàn thành thuộc sở hữu Kỹ thuật viên;
- live integration test đầy đủ;
- deployment và migration production.

Các nội dung này thuộc các phase triển khai riêng và không được ghi nhận sai là đã hoàn thành trong tài liệu này.
