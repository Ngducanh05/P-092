# Audit Policy

Audit logs are backend-controlled append-only operational records.

Final actor reference:

- `audit_logs.actor_auth_user_id` stores the Supabase auth UUID when a Resident or BQL actor initiated the action.
- System/AI actions may store null.

Audit values and metadata are not exposed to direct clients.
