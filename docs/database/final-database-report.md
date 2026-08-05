# Final Database Report

## 1. Project Database Scope

Status: COMPLETE for static database security design. This phase covers schema preservation, ownership documentation, RLS scaffolding, security views, audit policy, attachment security, leakage risks, retention policy, migration guidance, and handover.

## 2. Completed Schema

Status: COMPLETE. Core tables and Step 5 operational tables are preserved: `users`, `units`, `tickets`, `ticket_attachments`, `ai_analysis_runs`, `ticket_scoring_results`, `user_unit_memberships`, `technician_profiles`, `technician_skills`, `ticket_assignments`, `ticket_status_history`, `notifications`, and `audit_logs`.

## 3. Ownership Model

Status: PARTIAL. Resident ownership is active membership to ticket unit. Technician ownership is active assignment. Coordinator scope is not defined.

## 4. Access-Control Summary

Status: PARTIAL. Deny-by-default RLS is implemented. Runtime identity-dependent grants are intentionally non-granting until identity binding is approved.

## 5. RLS Status

Status: PARTIAL / NOT TESTED ON LIVE POSTGRESQL. RLS is enabled and forced by migration. Policies do not use `auth.uid()` or `auth.jwt()`.

## 6. Security Views

Status: COMPLETE. `resident_ticket_view` and `technician_ticket_view` are created with `security_invoker = true`. Coordinator view is deferred.

## 7. Attachment Security

Status: PARTIAL. Attachment metadata access derives from parent ticket ownership. Private storage bucket policy is a deployment requirement.

## 8. Audit Controls

Status: PARTIAL. Client SELECT/UPDATE/DELETE and INSERT are denied by RLS. Service insert identity remains pending.

## 9. Data-Leakage Risks

Status: COMPLETE. Required risk scenarios are documented in `data-leakage-risk-matrix.md`.

## 10. Retention Policy

Status: REQUIRES BUSINESS CLARIFICATION. No retention durations are defined by authoritative project documents.

## 11. Index Review

Status: COMPLETE. Existing Step 5 indexes are retained. No new performance indexes were added.

## 12. Migration History

Status: COMPLETE. Security migration follows initial and operational migrations.

## 13. Test Evidence

Status: COMPLETE for static tests after validation. Live PostgreSQL integration remains pending until a safe test database is provided.

## 14. Known Limitations

- Runtime user identity in PostgreSQL is not defined.
- Supabase Auth is not confirmed.
- Coordinator management scope is missing.
- Admin behavior is not defined.
- Service-role usage is not configured.
- Storage bucket policies are not implemented.

## 15. Business Clarifications Required

- Authentication provider and PostgreSQL identity binding.
- Whether Supabase Auth, `auth.uid()`, or custom session variables will be used.
- Coordinator management scope.
- Admin permissions.
- Retention durations.
- Attachment storage bucket names and policies.
- Service-role operational model.

## 16. Production-Readiness Checklist

Status: NOT TESTED ON LIVE POSTGRESQL.

- Run migration only on safe target first.
- Replace placeholder non-granting policies only after identity mapping approval.
- Validate views preserve underlying RLS.
- Validate service-role behavior with backend authorization.
- Approve retention and deletion policy.

## 17. Handover For Backend

Backend must derive ownership from authenticated identity and database relationships, never request body owner fields. Backend services must create audit rows inside the same transactions as sensitive changes.

## 18. Handover For DevOps

Keep database credentials and any future service-role keys backend-only. Do not expose service-role keys to frontend variables. Validate migrations on a disposable PostgreSQL target before production.

## 19. Handover For QA

Create live PostgreSQL RLS tests after safe identity binding is approved. Cover resident isolation, technician isolation, notifications, audit immutability, and view column exposure.

## 20. Out Of Scope

Scoring service, LangGraph, LLM calls, API routes, frontend, authentication flow, notification delivery, auto-assignment, status-transition services, production seed data, and production Supabase deployment.

