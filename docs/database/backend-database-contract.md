> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Backend Database Contract

The backend derives the current actor from the verified Supabase JWT subject and exactly one profile table: `residents`, `bql_staff`, or `technician_profiles`.

Never trust client-sent Resident IDs, BQL IDs, Technician IDs for authorization, actor type, role, unit ownership, or Storage paths.

- Resident ticket creation verifies active `resident_unit_memberships`.
- BQL ticket operations require an active `bql_staff` profile.
- Technician work operations derive Technician ID from the token and query only own active assignments.
- Assignment creation verifies ticket state, Category, Technician activity/availability, matching skill, and one-active-assignment uniqueness.
- Shared operational references use Supabase Auth UUID columns rather than `public.users`.
