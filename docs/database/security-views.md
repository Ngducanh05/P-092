# Security Views

`resident_ticket_view` is retained with `security_invoker = true` and excludes internal scoring, AI model, audit, and private Storage fields.

No final Technician view exists. A BQL view may be added later only if it provides meaningful column restriction and preserves underlying RLS.
