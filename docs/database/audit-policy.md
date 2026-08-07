# Audit Policy

Audit logs are backend-controlled append-only operational records.

- `audit_logs.actor_auth_user_id` stores the Supabase Auth UUID for Resident, BQL, or Technician actions.
- System/AI actions may store null.
- Assignment creation and Technician assignment-state changes write old/new state evidence.
- Audit payloads must never contain passwords, OTPs, access tokens, service keys, authorization headers, or private Storage URLs.

Audit values and metadata are not exposed directly to clients.
