# Supabase Auth Setup

Residents authenticate directly with Supabase Auth using phone number and SMS OTP. Enable the Phone provider, configure an SMS provider, set OTP expiry/rate limits, and have the frontend send the resulting access token to FastAPI as `Authorization: Bearer <access_token>`.

Coordinators and technicians authenticate with Supabase email/password. Create or invite these users through a trusted admin process, then provision the matching `public.users` row with `scripts/provision_supabase_user.py`. Do not expose role selection in frontend metadata or request bodies.

FastAPI validates tokens in `jwks`, `auth_server`, or `auto` mode. The issuer is `<SUPABASE_URL>/auth/v1`, the JWKS URL is `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`, and the default audience is `authenticated`. Auto mode tries JWKS first and falls back to the Auth user endpoint only when no compatible JWKS is available.

`public.users.id` is the Supabase Auth user UUID from JWT `sub`. ADMIN remains in the enum for compatibility only; ADMIN permissions are deferred.
