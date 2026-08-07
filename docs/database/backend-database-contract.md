# Backend Database Contract

The backend derives the current actor from the verified Supabase JWT subject and exactly one profile table: `residents`, `bql_staff`, or `technician_profiles`.

Never trust client-sent Resident IDs, BQL IDs, Technician IDs for authorization, actor type, role, unit ownership, or Storage paths.

- Resident ticket creation verifies active `resident_unit_memberships`.
- BQL ticket operations require an active `bql_staff` profile.
- Technician work operations derive Technician ID from the token and query only own active assignments.
- Assignment creation verifies ticket state, Category, Technician activity/availability, matching skill, and one-active-assignment uniqueness.
- Shared operational references use Supabase Auth UUID columns rather than `public.users`.
