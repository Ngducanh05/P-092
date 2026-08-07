# Các khoảng trống còn lại so với Self Dev v2/v3

Danh sách này chỉ ghi những phần **chưa thể khẳng định đã hoàn thành**. Không dùng tài liệu Technician cũ làm backlog.

## 1. Semantic image-quality gate

Self Dev yêu cầu: nếu request có ảnh, ảnh phải được kiểm tra là đủ đọc/đủ xác định vấn đề **trước khi insert ticket chính thức**. Nếu không đạt, trả `IMAGE_UNREADABLE` và không tạo ticket.

Hiện backend mới có:

- signed upload riêng tư;
- kiểm tra ownership;
- MIME type;
- kích thước;
- expiry;
- one-time consumption;
- xác minh object tồn tại trên Storage.

Các kiểm tra này không tương đương semantic image readability. Không được ghi nhận feature này là hoàn thành cho đến khi có validator/vision pipeline thực tế.

## 2. Product AI pipeline và worker

Schema Agent đã khóa đúng ranh giới Self Dev, nhưng còn thiếu execution pipeline production:

```text
create ticket
-> enqueue job/outbox
-> AI analyze
-> validate AgentResult
-> resolve red flag / category matching
-> backend scoring
-> persist ai_analysis_runs
-> update ticket
-> rebuild incident/density nếu cần
-> notification event
```

Các internal endpoints/job equivalents trong Self Dev chưa được public ra runtime hiện tại.

## 3. Multi-label Category matching

Self Dev ghi rõ chưa chốt cách so sánh `text_categories` và `image_categories` khi cả hai có nhiều nhãn:

- exact-set match; hay
- chỉ cần có ít nhất một nhãn giao nhau.

Không triển khai heuristic production trước khi lead chốt.

## 4. Duplicate blocking cho Density

Density query đã dùng `COUNT(DISTINCT source_unit_id)` cho WATER_LEAK/ELECTRICAL_SHORT trong cửa sổ ba ngày và tầng liền kề.

Còn thiếu rule chặn cùng unit + Category + location trong cửa sổ ba ngày. Vì Category chỉ có sau AI/manual review, cần chốt điểm kiểm tra/reject/merge trong pipeline trước khi triển khai để không tự suy đoán hành vi FE.

## 5. Scoring rule version trong AI pipeline

Runtime Coordinator đã đọc đúng row `scoring_rule_versions.is_active=true`, validate `config` và dùng config đó cho recalculation. Canonical constants trong `ScoringService` chỉ còn là fallback bootstrap/test khi database test chưa seed rule.

Phần còn thiếu nằm ở worker AI production: mỗi `ai_analysis_runs` phải ghi `rule_version_id` của rule đã dùng, và môi trường production nên fail-closed nếu không có đúng một active scoring rule.

## 6. Idempotency và optimistic locking transport

`tickets.version` đã có và mutation dùng row lock/transaction. Self Dev yêu cầu idempotency/optimistic locking nhưng chưa quy định đầy đủ:

- bảng/persistence của `Idempotency-Key`;
- TTL;
- response replay rule;
- header/body dùng để gửi expected `version`.

Cần chốt contract trước khi triển khai để tránh API riêng không tương thích Frontend.

## 7. Notification delivery

Database và API notification đã có; coordinator workflow tạo notification IN_APP. Chưa có dispatcher production cho PUSH/SMS và retry/error handling.

## 8. Physical PostgreSQL schema split

Self Dev đề xuất logical namespaces:

```text
app
ai_private
audit
```

Migration `a7b8c9d0e1f2` hiện giữ physical tables ở `public` để thực hiện forward cutover an toàn từ schema legacy và tương thích test SQLite. Nếu lead yêu cầu tách namespace vật lý, phải làm bằng migration forward riêng sau khi cutover v2 ổn định.

## 9. Production/live validation

Migration `a7b8c9d0e1f2` chưa được chạy lên Supabase. Nó có preflight fail-closed nếu phát hiện dữ liệu operational legacy. Trước khi chạy thật cần:

1. backup;
2. kiểm tra row count legacy;
3. quyết định data-mapping cho ticket đang tồn tại;
4. dry review SQL;
5. chỉ bật live migration gate trên development/test đã xác nhận;
6. không sửa `f6a7b8c9d0e1` đã tồn tại.


## 10. Transport tạo ticket multipart

Self Dev DB/API v2 mô tả `POST /tickets` là `multipart/form-data` với `location_id`, `description` và `image`. Backend hiện dùng signed-upload session một lần rồi gửi `attachment_upload_ids` trong request tạo ticket để bảo vệ private Storage và tránh raw object path.

Đây là khác biệt ở lớp transport, không phải thay đổi domain. Nếu Frontend/WireFrame được khóa theo contract multipart nguyên văn, cần thêm adapter multipart hoặc thay transport hiện tại; không được coi signed-upload extension là contract Self Dev gốc.
