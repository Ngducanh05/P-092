# Supabase Auth Setup

Residents authenticate directly with Supabase Auth using phone number and SMS OTP. Enable the Phone provider, configure an SMS provider, set OTP expiry/rate limits, and have the frontend send the resulting access token to FastAPI as `Authorization: Bearer <access_token>`.

Phone claims must already be normalized E.164 values, for example `+84901234567`. The backend rejects local formats such as `09...`; it does not guess a country code.

Coordinators and technicians authenticate with Supabase email/password. Create or invite these users through a trusted admin process, then provision the matching `public.users` row with `scripts/provision_supabase_user.py`. Do not expose role selection in frontend metadata or request bodies.

The provisioning helper requires backend-only configuration:

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `DATABASE_URL`

`SUPABASE_SECRET_KEY` supports both current `sb_secret_*` keys and legacy service-role JWTs. Current `sb_secret_*` values are sent only as `apikey`; legacy service-role JWTs also use `Authorization: Bearer <key>` for compatibility. The helper never prints secret values.

FastAPI validates tokens in one of three modes:

- `jwks`: accepts only supported asymmetric algorithms and never falls back to the Auth server.
- `auth_server`: calls `<SUPABASE_URL>/auth/v1/user` with the publishable key and the user Bearer token.
- `auto`: routes `HS256` tokens to the Auth server and asymmetric tokens to JWKS verification.

The verifier is cached by the FastAPI dependency so JWKS keys are reused between requests. An unknown asymmetric `kid` triggers one bounded JWKS refresh; invalid signatures, expired tokens, wrong issuer, and wrong audience are rejected without Auth-server fallback.

`public.users.id` is the Supabase Auth user UUID from JWT `sub`. Unknown valid Auth users may be auto-provisioned only as residents. ADMIN remains in the enum for compatibility only; ADMIN permissions are deferred.

The additive migration `c3d4e5f6a7b8` validates `fk_users_id_auth_users` only when `auth.users` exists and there are no orphan application profiles. If orphan profiles exist, the migration stops and reports only the count. Use `docs/backend/supabase-user-migration-remediation.md` before retrying.

Live Auth validation status remains BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED and token-specific scenarios remain BLOCKED — MISSING TEST TOKEN until manually supplied resident/coordinator access tokens are tested against a confirmed development/test Supabase project.
