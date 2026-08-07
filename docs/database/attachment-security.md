# Attachment Security

Ticket attachment objects are stored in a private Supabase Storage bucket. API responses return approved metadata and short-lived signed download URLs; raw Storage paths remain internal.

Authorization follows the parent Ticket:

- Resident: active membership for the Ticket unit.
- BQL: active BQL system-wide MVP read.
- Technician: active assignment to the parent Ticket.

Existing signed upload sessions are Resident-owned. Technician completion evidence requires a separate Technician-owned upload contract and remains intentionally blocked until implemented.
