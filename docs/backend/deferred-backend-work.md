# Deferred Backend Work

| Item | Reason | Required source/decision | Expected owner | Future integration point |
|---|---|---|---|---|
| Formula H and component scores | No approved formula in T-006/T-007 | Lead scoring spec | Lead/scoring owner | `TicketService` after create |
| P0/manual review | Explicitly out of scope | Product workflow decision | Lead/backend | Ticket status/category workflow |
| Category/Priority override | Explicitly out of scope | Coordinator rules | Backend owner | Coordinator routes |
| Technician assignment/work list/status updates | Explicitly out of scope | Assignment workflow | Backend owner | Ticket assignment service/routes |
| Notification delivery | Explicitly out of scope | Channel/provider choices | Backend owner | Notifications table/service |
| LangGraph nodes and LLM calls | Owned by Lead | Agent graph design | Lead agent owner | Async AI processing pipeline |
| Frontend | Separate owner | UI requirements | Frontend owner | Supabase Auth and API clients |
| Railway/Vercel production deploy | Deferred | Deployment runbook | DevOps owner | Environment and CI/CD |
| SLA/ETA formula | Not approved | SLA policy | Product/ops | `estimated_resolution_*` fields |
