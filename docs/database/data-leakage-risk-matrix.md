# Data Leakage Risk Matrix

Scale: Likelihood Low/Medium/High. Impact Low/Medium/High/Critical. Risk Low/Medium/High/Critical.

| Risk ID | Threat | Example attack or failure | Affected data | Likelihood | Impact | Risk level | Existing control | Required control | Owner | Verification method | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | Resident changes `unit_id` | IDOR to another apartment ticket | Tickets | Medium | High | High | Membership table | RLS membership predicate | Backend/DB | Static + integration | PARTIAL |
| R2 | Technician accesses unassigned UUID | Direct object lookup | Tickets | Medium | High | High | Assignment table | Active assignment predicate | Backend/DB | Static + integration | PARTIAL |
| R3 | User reads another notification | Query by notification id | Notifications | Medium | Medium | Medium | Recipient column | Recipient RLS | DB | Static + integration | PARTIAL |
| R4 | Technician sees scoring breakdown | Over-broad SELECT/view | Scores | Medium | High | High | Security views | Column projection | Backend/DB | View tests | COMPLETE |
| R5 | Public attachment URL | In-home images exposed | Attachments | Medium | Critical | Critical | Metadata table | Private storage + signed URLs | DevOps | Storage review | REQUIRES BUSINESS CLARIFICATION |
| R6 | Service-role key exposed | Frontend env leak | All data | Low | Critical | Critical | No service key config | Secret management | DevOps | Config review | PARTIAL |
| R7 | Secrets written to audit | JWT/API key in JSONB | Secrets | Medium | Critical | Critical | Audit policy docs | Backend redaction | Backend | Tests + review | PARTIAL |
| R8 | Excessive PII in audit | Full profile snapshots | PII | Medium | High | High | Audit allowlist docs | Payload allowlist | Backend | Code review | PARTIAL |
| R9 | AI receives profile data | LLM prompt leaks PII | PII | Medium | High | High | AI tables scoped | Minimum-data contract | Backend/AI | Prompt review | PARTIAL |
| R10 | SQL injection | Dynamic SQL from client | All data | Low | Critical | High | SQLAlchemy | Parameterized queries | Backend | Code review | PARTIAL |
| R11 | IDOR direct lookup | `WHERE id = requested_id` only | Tickets | Medium | High | High | Ownership docs | Relationship predicates | Backend/DB | Tests | PARTIAL |
| R12 | Missing coordinator scope | Role grants all rows | All operational data | Medium | Critical | Critical | No broad policy | Scope decision | Product | Docs | REQUIRES BUSINESS CLARIFICATION |
| R13 | View owner bypasses RLS | Security definer view leaks | Tickets | Low | High | Medium | `security_invoker` views | PG version validation | DevOps/DB | Integration | NOT TESTED ON LIVE POSTGRESQL |
| R14 | Deactivated users retain access | `is_active` ignored | User-owned rows | Medium | High | High | Active flags | Predicate must check activity | Backend/DB | Integration | PARTIAL |
| R15 | Ended assignment still grants access | `ended_at` ignored | Tickets | Medium | High | High | `is_active` index | Active assignment predicate | DB | Static + integration | PARTIAL |
| R16 | Unlinked membership grants access | `unlinked_at` ignored | Tickets | Medium | High | High | `is_active` index | Active membership predicate | DB | Static + integration | PARTIAL |
| R17 | RLS denies service unexpectedly | No policy after enabling RLS | Availability | Medium | Medium | Medium | Static migration | Service access design | Backend/DB | Integration | REQUIRES BUSINESS CLARIFICATION |
| R18 | Service role bypasses checks | Backend skips authorization | All data | Medium | Critical | Critical | Docs | Backend authorization | Backend | Code review | PARTIAL |
| R19 | Migration runs on production | Accidental destructive change | Database | Low | Critical | High | Migration guide | Approval gates | DevOps | Runbook | PARTIAL |
| R20 | Test data contains real PII | Fixtures leak resident info | PII | Low | High | Medium | No prod seed data | Synthetic fixtures | QA | Test review | PARTIAL |

