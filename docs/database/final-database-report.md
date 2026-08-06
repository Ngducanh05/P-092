# Final Database Report

Status: static final architecture implemented for Resident and BQL profiles. NOT TESTED ON LIVE POSTGRESQL by default.

## Final Actor Model

- `auth.users` stores authentication identity.
- `public.residents` stores Resident business profiles.
- `public.bql_staff` stores BQL staff business profiles.

The final schema removes `public.users`, `role_enum`, Technician profiles, Technician skills, ticket assignments, Technician policies, and Technician views.

## Ownership

Tickets reference `residents.id`. Unit membership uses `resident_unit_memberships`. Upload sessions use `resident_id`. Status history, notifications, and audit logs store Supabase auth UUIDs for mixed Resident/BQL records.

## Security

RLS uses `auth.uid()` and remains defense in depth. Resident access is based on active memberships. BQL has system-wide MVP ticket read when the `bql_staff` profile is active. Audit and internal AI scoring data remain restricted.

Legacy ticket status values `waiting_assignment` and `assigned` remain pending lifecycle approval; no new Technician assignment transitions are generated.
