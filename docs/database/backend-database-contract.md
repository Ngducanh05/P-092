# Backend Database Contract

Backend code derives the current actor from the verified Supabase JWT subject and exactly one profile table: `residents` or `bql_staff`.

Never trust client-sent resident IDs, BQL IDs, actor type, role, unit owner IDs, attachment paths, or Storage paths.

Resident ticket creation verifies active `resident_unit_memberships`. BQL ticket listing uses active `bql_staff`. Shared operational references use Supabase auth UUID columns, not `public.users`.
