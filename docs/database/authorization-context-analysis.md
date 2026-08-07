# Authorization Context Analysis

Authorization is derived from the verified Supabase JWT subject plus exactly one application profile:

- Resident: `auth.users.id -> residents.id`
- BQL: `auth.users.id -> bql_staff.id`
- Technician: `auth.users.id -> technician_profiles.id`

The same Auth UUID is rejected if it appears in more than one actor profile. Unknown phone identities may be provisioned only as Residents; unknown email-only identities are never promoted to BQL or Technician.

Never trust client-provided actor type, profile IDs, BQL/Technician IDs for authorization, role metadata, unit owner IDs, attachment paths, or bypass flags.
