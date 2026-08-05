# Backend-Database Contract

## Trusted Identity

Backend must derive `current_user_id`, role, resident membership, unit ownership, technician profile, active assignment, and coordinator scope from authenticated context plus database relationships. This repository does not yet define that authentication context.

## Untrusted Request Fields

Treat these as untrusted for authorization: `user_id`, `resident_id`, `unit_id`, `source_unit_id`, `technician_id`, `assigned_by_user_id`, `role`, `owner_id`, `recipient_user_id`.

## Transaction Boundaries

- Create ticket: insert ticket, create initial `ticket_status_history`, optionally create notification.
- Assign ticket: end prior assignment, create new assignment, create audit log, create notification.
- Status transition: update ticket status, append `ticket_status_history`, create audit log, create notification.
- Category/priority override: update ticket controlled field and create audit log.
- Link/unlink membership: update membership state and create audit log.

These services are not implemented in this database phase.

## Restricted Field Exposure

Backend must not expose service-role keys, database credentials, audit secrets, raw authorization headers, internal scoring breakdown to unauthorized actors, raw AI system prompts, or raw chain-of-thought.

