> [!WARNING]
> **TÀI LIỆU LỊCH SỬ / LEGACY.** `Self_Dev_Docs` v2/v3 là source of truth hiện hành của P-092. Nội dung bên dưới về Technician, assignment, `bql_staff`, `residents` hoặc schema cũ chỉ dùng để truy vết lịch sử và **không được dùng làm chuẩn triển khai mới**. Xem `docs/source-of-truth/README.md` và `docs/audit/spec-alignment.md`.

# RLS Policy Design

RLS uses the verified Supabase identity from `auth.uid()` as defense in depth. Backend authorization remains mandatory and direct client mutations are not used for business workflows.

## Resident

An authenticated active Resident may select:

- the Resident's own `residents` profile;
- own active `resident_unit_memberships` rows;
- active Units reached through those memberships;
- Tickets in the Resident's active unit scope;
- attachments and status history through an authorized parent Ticket;
- notifications where `recipient_auth_user_id = auth.uid()`.

Resident ownership never comes from a client-supplied Resident or Unit owner ID.

## BQL

An authenticated active BQL staff member may select:

- the BQL user's own `bql_staff` profile;
- the current MVP system-wide Ticket queue;
- parent-authorized attachments and status history;
- active Technician profiles and skills required for routing;
- assignment rows required for operations;
- own notifications.

BQL status is resolved from `bql_staff`, not JWT role metadata or frontend input.

## Technician

An authenticated active Technician may select:

- the Technician's own active `technician_profiles` row;
- own skills;
- own active `ticket_assignments` rows;
- only Tickets referenced by those active assignments;
- attachments and status history through an assigned parent Ticket;
- own notifications.

A Technician cannot read another Technician's assignment or an unassigned Ticket. Technician identity is always derived from `auth.uid()`.

## Backend-only or restricted data

Direct `anon` and `authenticated` mutation remains denied for backend-controlled workflows. Internal tables and payloads include:

- `ticket_attachment_upload_sessions`
- `ai_analysis_runs`
- `ticket_scoring_results`
- `audit_logs`
- assignment mutations and status transitions

Private Storage paths, internal model fields, score breakdowns, and audit payloads are not exposed through ordinary client APIs.

## Hardening

Final business tables have RLS enabled and forced where appropriate, and broad `PUBLIC` privileges are revoked. No INSERT, UPDATE, or DELETE policy is granted to direct clients for Technician profile provisioning, assignment, status history, notifications, or audit writes.
