# Supabase Auth Setup

Supabase Auth remains the authentication provider. The application no longer uses `public.users`, `role_enum`, Coordinator, Admin, or Technician profiles for final runtime authorization.

## Profiles

- Residents authenticate with phone OTP and resolve to `public.residents`.
- BQL staff authenticate with email/password and resolve to `public.bql_staff`.

BQL profiles are provisioned through backend-only administrative tooling. Do not expose frontend role selection and do not trust editable JWT metadata.

Unknown valid Auth users are auto-created as Residents only when the token has a valid normalized E.164 phone claim. Email-only unknown users are rejected.

## Flow

Frontend -> Supabase Auth -> Bearer token -> FastAPI -> `residents` or `bql_staff` profile resolution -> authorization/business logic -> PostgreSQL/Supabase.

Backend never receives OTPs or passwords and never exposes the Supabase secret key.
