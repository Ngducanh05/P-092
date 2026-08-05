# Authorization Context Analysis

## Finding

Status: REQUIRES BUSINESS CLARIFICATION.

The repository does not define a confirmed runtime identity binding between authenticated application users and PostgreSQL RLS. `src/config.py` exposes only `DATABASE_URL`; there is no Supabase URL/key configuration, service-role setting, JWT issuer, PostgreSQL session-variable helper, or direct client database access code.

| Question | Current answer |
|---|---|
| How does PostgreSQL know the current user ID? | Not defined. |
| How does PostgreSQL know the current role? | Not defined. `users.role` exists, but no RLS identity mapping exists. |
| Which JWT claims are available? | None confirmed. |
| Does the frontend connect directly to Supabase? | Not confirmed. Existing app routes use FastAPI template code. |
| Does the backend use a service-role key? | Not configured in repository. |
| Can service-role bypass RLS? | Supabase service role can bypass RLS in general, but Supabase service-role use is not confirmed for this project. |
| Which operations are client-side versus backend-only? | Direct database client writes are not confirmed; database mutations should remain backend-only until clarified. |

## Decisions

- Do not use `auth.uid()` or `auth.jwt()` in migrations because Supabase Auth integration is not confirmed.
- Do not invent JWT claim names, Supabase identity mappings, coordinator scope, or admin bypass.
- The Step 6-8 migration enables and forces RLS, revokes broad public table privileges, and creates non-granting placeholder policies that preserve required predicates without granting access.
- Runtime identity binding must be approved before replacing placeholder `NULL::uuid` identity markers with a real identity source.

