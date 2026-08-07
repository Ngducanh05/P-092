# Data Leakage Risk Matrix

| Risk | Impacted Data | Mitigation |
| --- | --- | --- |
| `unit_id` tampering | Ticket ownership | Backend derives Resident from token and verifies active membership. |
| unassigned UUID probing | Tickets/attachments | Unauthorized detail and download return 404. |
| cross-Technician probing | Assignments/tickets | Backend derives Technician from token; own-active-assignment filter and RLS mask foreign records. |
| notification recipient mismatch | Notifications | RLS uses `recipient_auth_user_id = auth.uid()`. |
| scoring breakdown exposure | AI scores | Internal score columns are not returned in normal actor API/view contracts. |
| Public attachment | Private media | Supabase Storage bucket remains private; signed URLs only. |
| completion-path spoofing | Completion evidence | Completion is blocked until Technician-owned signed upload sessions exist; raw paths are rejected. |
| Service-role key exposure | Full backend access | Secrets are backend-only and never printed by scripts. |
| Secrets written to audit | Credentials | Public tables do not store passwords, OTPs, JWTs, keys, or authorization headers. |
| Excessive PII | Profiles/audit | Resident, BQL, and Technician profiles contain only required contact/operational fields. |
| AI receives unnecessary data | Ticket text/media | Internal AI access remains backend-controlled and should use the minimum required payload. |
| SQL injection | Provisioning | Administrative scripts use parameterized SQL and validate inputs. |
| IDOR | Tickets/attachments/assignments | Membership or assignment ownership plus 404 masking. |
| duplicate active assignment | Work routing | Partial unique index allows at most one active assignment per ticket. |
| actor-profile conflict | Authorization | Database conflict trigger and backend profile-count guard enforce one actor per Auth UUID. |
| BQL system-wide MVP read | All tickets | Intentional operational scope, restricted to active `bql_staff`. |
| View owner | RLS bypass | Views use `security_invoker = true`. |
| Deactivated users | Stale access | Inactive Resident, BQL, and Technician profiles return 403; Technician RLS also requires active profile. |
| Unlinked membership | Ticket read | RLS and backend require active Resident membership. |
| RLS denies service | Backend jobs | Service-role execution remains backend-only. |
| Service role bypasses | All data | Service credentials are used only by trusted backend infrastructure, never frontend code. |
| Migration runs on production | Live data | Live migrations are gated and are not executed by default. |
| Test data contains real PII | Logs/tests | Use synthetic fixtures and never print access tokens. |
