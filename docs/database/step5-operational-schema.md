# Step 5 Operational Schema

## Overview

The original six tables captured users, units, tickets, attachments, AI analysis history, and scoring history. They were insufficient for day-to-day operations because they did not represent resident unit membership, technician availability and skills, coordinator assignment history, ticket status history, durable notifications, or audit logs for sensitive changes.

Step 5 adds structural ownership and workflow history only. Authorization enforcement, API behavior, RLS policies, notification delivery, and assignment automation remain out of scope.

## Table Dictionary

### `user_unit_memberships`

- Purpose: links user accounts to units so resident access can be derived from active memberships.
- Primary key: `id`.
- Foreign keys: `user_id -> users.id RESTRICT`, `unit_id -> units.id RESTRICT`.
- Important fields: `is_active`, `linked_at`, `unlinked_at`, `created_at`, `updated_at`.
- Constraints: unique `(user_id, unit_id)`.
- Indexes: `(user_id, is_active)` for resident unit lookup; `(unit_id, is_active)` for unit resident lookup.
- Deletion behavior: user and unit deletion is restricted to avoid silently losing ownership history.
- Data owner: backend account and residency-management workflow.
- Sensitive-data classification: operational ownership link; no secrets or credentials.

### `technician_profiles`

- Purpose: stores technician operational state separately from generic `users`.
- Primary key: `user_id`.
- Foreign keys: `user_id -> users.id RESTRICT`.
- Important fields: `is_active`, `is_available`, `created_at`, `updated_at`.
- Constraints: one row per technician user through primary key.
- Indexes: primary-key index only.
- Deletion behavior: user deletion is restricted while a technician profile exists.
- Data owner: coordinator/operations workflow.
- Sensitive-data classification: operational availability; no HR, payroll, password, or credential data.

### `technician_skills`

- Purpose: maps technician profiles to supported incident categories.
- Primary key: `id`.
- Foreign keys: `technician_id -> technician_profiles.user_id RESTRICT`.
- Important fields: `category`, `created_at`.
- Constraints: unique `(technician_id, category)`.
- Indexes: `category` supports finding technicians for a ticket category.
- Deletion behavior: technician profile deletion is restricted by default; skills are profile-owned in the ORM.
- Data owner: coordinator/operations workflow.
- Sensitive-data classification: operational capability metadata.

### `ticket_assignments`

- Purpose: records coordinator assignment of tickets to technicians and preserves assignment history.
- Primary key: `id`.
- Foreign keys: `ticket_id -> tickets.id CASCADE`, `technician_id -> technician_profiles.user_id RESTRICT`, `assigned_by_user_id -> users.id RESTRICT`.
- Important fields: `assigned_at`, `accepted_at`, `ended_at`, `is_active`, `created_at`, `updated_at`.
- Constraints: PostgreSQL partial unique index allows at most one active assignment per ticket.
- Indexes: `(ticket_id, assigned_at)` for ticket assignment history; `(technician_id, is_active)` for technician workload.
- Deletion behavior: ticket deletion cascades to ticket-owned assignment rows; technician/coordinator deletion is restricted to preserve history.
- Data owner: coordinator assignment workflow.
- Sensitive-data classification: operational routing history.

### `ticket_status_history`

- Purpose: preserves ticket status transitions.
- Primary key: `id`.
- Foreign keys: `ticket_id -> tickets.id CASCADE`, `changed_by_user_id -> users.id SET NULL`.
- Important fields: `from_status`, `to_status`, `change_reason`, `created_at`.
- Constraints: `to_status` is required; `from_status` is nullable for initial creation.
- Indexes: `(ticket_id, created_at)` supports chronological ticket history.
- Deletion behavior: ticket deletion cascades to ticket-owned status rows; actor deletion sets nullable actor reference to null.
- Data owner: resident, coordinator, technician, and system workflows.
- Sensitive-data classification: operational history; no chain-of-thought or internal AI reasoning.

### `notifications`

- Purpose: stores resident, coordinator, and technician notification records.
- Primary key: `id`.
- Foreign keys: `recipient_user_id -> users.id RESTRICT`, `ticket_id -> tickets.id SET NULL`.
- Important fields: `event_type`, `title`, `body`, `is_read`, `read_at`, `created_at`.
- Constraints: bounded string `event_type`; no provider secrets or push tokens.
- Indexes: `(recipient_user_id, is_read, created_at)` for unread inbox lookup; `ticket_id` for ticket-related notification lookup.
- Deletion behavior: user deletion is restricted; ticket deletion preserves notification rows and clears ticket reference.
- Data owner: system notification workflow.
- Sensitive-data classification: user-facing operational messages; no delivery credentials.

### `audit_logs`

- Purpose: append-only record of sensitive coordinator and system changes with old/new values.
- Primary key: `id`.
- Foreign keys: `actor_user_id -> users.id SET NULL`.
- Important fields: `entity_type`, `entity_id`, `action`, `old_values`, `new_values`, database column `metadata`.
- Constraints: required entity/action fields; JSONB audit payloads.
- Indexes: `(entity_type, entity_id)` for entity audit trail; `(actor_user_id, created_at)` for actor audit review.
- Deletion behavior: actor deletion sets nullable actor reference to null; audit rows are not cascaded from users.
- Data owner: system audit workflow.
- Sensitive-data classification: sensitive operational audit data. Do not store API keys, access tokens, OTP values, passwords, or raw authorization headers.

## Relationship Summary

- `User` to `Unit` is many-to-many over time through `user_unit_memberships`.
- `User` to `TechnicianProfile` is one-to-one through `technician_profiles.user_id`.
- `TechnicianProfile` to `Category` is represented through `technician_skills`.
- `Ticket` to technician assignment history is represented through `ticket_assignments`.
- `Ticket` to status changes is represented through `ticket_status_history`.
- `User` to notifications is represented through `notifications.recipient_user_id`.
- `User` or system to audit logs is represented through nullable `audit_logs.actor_user_id`.

## Ownership Notes

- Resident access basis: active `user_unit_memberships` rows matched to ticket `unit_id`.
- Technician access basis: active `ticket_assignments` rows for the technician profile.
- Coordinator authority: role and management scope, enforced later by backend authorization and RLS.
- System/AI access basis: service identity and minimum required ticket, analysis, status, notification, and audit data.

Actual authorization enforcement and RLS policies belong to the next step.
