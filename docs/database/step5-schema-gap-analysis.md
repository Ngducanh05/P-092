# Schema Gap Analysis

The prior operational schema included generic users and assignment workflow structures. The final approved architecture closes that gap by splitting business profiles into `residents` and `bql_staff`, replacing generic memberships with `resident_unit_memberships`, and removing unsupported assignment workflow tables.

Remaining planned work is a dedicated ticket lifecycle migration for legacy enum values once approved.
