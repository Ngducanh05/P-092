# Supabase Profile Migration Remediation

Historical migrations aligned `public.users` with Supabase Auth. The final architecture replaces that table with `residents` and `bql_staff`.

For current remediation, verify:

- Resident Auth UUIDs exist in `residents`.
- BQL Auth UUIDs exist in `bql_staff`.
- No Auth UUID appears in both profile tables.
- BQL profiles are provisioned only through backend administrative tooling.
