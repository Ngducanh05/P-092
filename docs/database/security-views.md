# Security Views

`resident_ticket_view` is retained with `security_invoker = true` and excludes internal scoring, AI model, audit, and private Storage fields.

Technician access is implemented through assignment-scoped RLS and actor-specific FastAPI response models rather than a broad Technician view. Any future view must use `security_invoker = true`, preserve underlying RLS, and exclude score breakdowns and private Storage paths.
