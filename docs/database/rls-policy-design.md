# RLS Policy Design

RLS uses the verified Supabase identity from `auth.uid()` and remains defense in depth. Backend authorization is still mandatory.

## Resident

An authenticated Resident may select:

- Their own active `residents` profile.
- Their own active `resident_unit_memberships` rows.
- Active Units reached through those memberships.
- Tickets whose `unit_id` has an active membership for `auth.uid()`.
- Attachments and status history only through an accessible parent Ticket.
- Notifications only when `recipient_auth_user_id = auth.uid()`.

Resident ticket ownership never comes from a client-supplied Resident or Unit owner ID.

## BQL

An authenticated active BQL staff member may select:

- Their own `bql_staff` profile.
- All Tickets for the current MVP.
- Attachments and status history through the accessible parent Ticket.
- Their own notifications through `recipient_auth_user_id = auth.uid()`.

BQL status is resolved from the backend-provisioned `bql_staff` table, not JWT role metadata or frontend input.

## Backend-only tables

Direct `anon` and `authenticated` access is explicitly denied for:

- `ticket_attachment_upload_sessions`
- `ai_analysis_runs`
- `ticket_scoring_results`
- `audit_logs`

Private Storage object paths, internal model fields, scoring breakdowns, and audit payloads are not exposed through normal client APIs.

## Mutations

No direct client INSERT, UPDATE, or DELETE policy is granted for backend-controlled business workflows. Ticket creation, attachment consumption, profile provisioning, status changes, notifications, and audit writes remain backend operations.

All final business tables have RLS enabled and forced, and broad `PUBLIC` privileges are revoked.
