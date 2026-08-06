# T-006/T-007 Gap Analysis

Implemented final actor refactor:

- Resident and BQL profiles replace generic users/roles.
- `/api/v1/bql/tickets` replaces the old Coordinator route.
- Technician workflow is removed.
- Attachment privacy, ticket transaction behavior, and resident membership checks are preserved.

Remaining limitation: legacy ticket status enum values `waiting_assignment` and `assigned` await approved lifecycle migration.
