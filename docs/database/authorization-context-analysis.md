# Authorization Context Analysis

Authorization context is derived from verified Supabase JWT identity plus exactly one profile table.

- Resident context: `auth.users.id -> residents.id`
- BQL context: `auth.users.id -> bql_staff.id`

Do not invent or trust client-provided actor type, profile IDs, role metadata, unit owner IDs, attachment paths, or admin bypass flags.
