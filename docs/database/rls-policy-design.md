# RLS Policy Design

RLS uses Supabase `auth.uid()`.

- Residents select own profile, own active memberships, active units through membership, and tickets through active membership.
- BQL staff select own profile and, for the MVP, all tickets when active.
- Attachments and status history derive read access from the parent ticket.
- Notifications use `recipient_auth_user_id = auth.uid()`.
- Audit logs, AI analysis, scoring, and upload sessions remain client-denied.

RLS is defense in depth; backend authorization remains required.
