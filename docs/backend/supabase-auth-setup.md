> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# Supabase Auth Setup

Supabase Auth is the authentication provider. The application does not use `public.users`, `role_enum`, frontend role selection, or editable JWT metadata for authorization.

## Business profiles

```text
auth.users
├── public.residents
├── public.bql_staff
└── public.technician_profiles
```

- Residents authenticate with phone OTP and resolve to `public.residents`.
- BQL staff authenticate with email/password and resolve to backend-provisioned `public.bql_staff`.
- Technicians authenticate with email/password and resolve to backend-provisioned `public.technician_profiles`.
- One Auth UUID may exist in only one business-profile table; database triggers and backend conflict checks enforce this.

Unknown valid Auth users are auto-created as Residents only when the verified token contains a valid normalized E.164 phone claim. Email-only unknown identities are rejected and never auto-provisioned as BQL or Technician. BQL and Technician profiles must be provisioned by trusted backend scripts after the corresponding Supabase Auth user exists.

## Request flow

```text
Frontend -> Supabase Auth -> Bearer token -> FastAPI
         -> residents | bql_staff | technician_profiles
         -> actor-specific authorization/business logic
         -> PostgreSQL/Supabase
```

The backend never receives OTPs or passwords and never exposes Supabase secret/service-role keys. Token email must case-insensitively match the BQL or Technician profile email; inactive profiles are denied.
