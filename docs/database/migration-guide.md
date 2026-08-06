# Migration Guide

Existing migrations through `c3d4e5f6a7b8` remain historical and unchanged. The Resident/BQL actor refactor is introduced by two later migrations:

- `d4e5f6a7b8c9`: creates `residents`, `bql_staff`, exclusivity trigger, `resident_unit_memberships`, and copied actor columns.
- `e5f6a7b8c9d0`: validates copied counts, aborts if Technician/assignment rows exist, removes `public.users`, `role_enum`, Technician tables/views/policies, and installs final RLS.

Do not run live Supabase migrations without explicit safe flags and tokens.
