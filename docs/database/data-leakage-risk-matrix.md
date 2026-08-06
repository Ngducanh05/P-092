# Data Leakage Risk Matrix

| Risk | Impacted Data | Mitigation |
| --- | --- | --- |
| `unit_id` tampering | Ticket ownership | Backend derives Resident from token and verifies active membership. |
| unassigned UUID probing | Tickets/attachments | Unauthorized detail and download return 404. |
| notification recipient mismatch | Notifications | RLS uses `recipient_auth_user_id = auth.uid()`. |
| scoring breakdown exposure | AI scores | Internal score columns are not returned in API/view contracts. |
| Public attachment | Private media | Supabase Storage bucket remains private; signed URLs only. |
| Service-role key exposure | Full backend access | Secrets are backend-only and never printed by scripts. |
| Secrets written to audit | Credentials | Public tables do not store passwords, OTPs, JWTs, keys, or authorization headers. |
| Excessive PII | Profiles/audit | Resident/BQL profiles contain minimal contact fields. |
| AI receives | Ticket text | Internal AI access remains backend-controlled. |
| SQL injection | Provisioning | Administrative scripts use parameterized SQL. |
| IDOR | Tickets/attachments | Resident ownership through memberships and 404 hiding. |
| BQL system-wide MVP read | All tickets | Intentional MVP scope, restricted to active `bql_staff`. |
| View owner | RLS bypass | Views use `security_invoker = true`. |
| Deactivated users | Stale access | Inactive Resident/BQL profiles return 403. |
| Unlinked membership | Ticket read | RLS and backend require active resident membership. |
| RLS denies service | Backend jobs | Service-role execution remains backend-only. |
| Service role bypasses | All data | Use only backend infrastructure, never frontend. |
| Migration runs on production | Live data | Live migrations are gated and not executed by default. |
| Test data contains real PII | Logs/tests | Use synthetic fixtures and never print tokens. |
