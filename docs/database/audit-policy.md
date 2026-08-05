# Audit Policy

Audit events should cover:

- category override,
- priority override,
- assignment and reassignment,
- status transition or correction,
- technician activation/deactivation,
- unit membership link/unlink,
- security-sensitive configuration changes.

Required audit fields already exist in `audit_logs`: `actor_user_id`, `entity_type`, `entity_id`, `action`, `old_values`, `new_values`, `metadata`, `created_at`.

## Protection

- Client SELECT is denied by RLS.
- Client UPDATE and DELETE are denied by RLS.
- Client INSERT is denied until service identity binding is approved.
- Audit rows are append-only by design.

## Never Store

Do not store passwords, OTP values, JWTs, refresh tokens, access tokens, API keys, service-role keys, authorization headers, database passwords, raw request headers, raw LLM chain-of-thought, or unredacted secret-bearing environment variables.

Database triggers are not introduced because backend audit handling has not been specified.

