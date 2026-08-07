# Source of Truth — Self Dev

## Quy tắc ưu tiên tài liệu

Thư mục `Self_Dev_Docs/` là **chuẩn nghiệp vụ và kỹ thuật bắt buộc** của P-092. Khi code, migration, README, tài liệu cũ hoặc ghi chú trước đây mâu thuẫn với Self Dev, phải ưu tiên Self Dev.

Bộ phiên bản hiện hành dùng để triển khai:

1. `Self_Dev_Docs/PRD_v2.md`
2. `Self_Dev_Docs/dac_ta_tinh_nang_luong_nghiep_vu_v2.md`
3. `Self_Dev_Docs/Logic_xử_lý_chính_v2.md`
4. `Self_Dev_Docs/dexuatdb_API-_v2.md`
5. `Self_Dev_Docs/WireFrame và UI Flow _v3.html`

`ai_evaluation_metrics_v1.md` vẫn được dùng cho tiêu chí đánh giá AI vì chưa có bản mới hơn thay thế phần này. Các file v1 còn lại chỉ giữ để truy vết lịch sử, không dùng để quyết định kiến trúc khi đã có v2/v3 tương ứng.

## Các quyết định đã khóa

- Chỉ có hai actor người dùng: **Cư dân** và **Điều phối viên BQL**. Không có actor Kỹ thuật viên và không có assignment workflow.
- Supabase Auth xác thực danh tính. Backend đọc role/unit từ database, không tin role, user ID hoặc unit ID do Frontend tự khai báo.
- Mô hình danh tính nghiệp vụ: `auth.users -> user_profiles -> resident_profiles` (resident only).
- Cư dân dùng SĐT + OTP. Điều phối viên dùng email + password và phải được backend provision role `COORDINATOR`.
- P0 là `classification_status = MANUAL_REVIEW`, không phải Priority. Priority chỉ có P1/P2/P3.
- Vòng đời ticket: `NEW -> APPROVED -> IN_PROGRESS -> COMPLETED|UNRESOLVABLE`; Cư dân chỉ hủy khi `NEW`; yêu cầu bổ sung dùng `WAITING_RESIDENT_INFO`.
- Điều phối viên tự xử lý ticket trực tiếp, không gán cho Kỹ thuật viên.
- Backend là nguồn chuẩn cho Category/Priority/SLA/available actions; Frontend không tự tính.
- Scoring: Category base + Location×Category + Density + Severity; red flag ép P3 và bỏ qua ceiling.
- Density tính `COUNT(DISTINCT source_unit_id)` cho rò nước/chập điện trong cửa sổ 3 ngày và cùng/tầng liền kề.
- Một unit có thể có nhiều tài khoản Cư dân; tài khoản bind đầu tiên có `is_primary=true`.
- Agent chỉ trả dữ liệu AI; Backend tự tính match, score, priority và ceiling.

## Điểm Self Dev chưa chốt

Không tự suy đoán các điểm này trong code:

- Quy tắc so khớp hai danh sách multi-label `text_categories` và `image_categories` (exact-set hay chỉ cần intersection).
- Cách truyền `version`/optimistic-lock từ client và cơ chế lưu Idempotency-Key cụ thể.
- Cách triển khai vật lý các schema PostgreSQL `app`, `ai_private`, `audit` khi chuyển từ schema legacy hiện tại; tài liệu DB gọi đây là kiến trúc đề xuất.

Mọi thay đổi ở các điểm chưa chốt phải được lead phê duyệt hoặc bổ sung vào Self Dev trước khi coi là chuẩn mới.
