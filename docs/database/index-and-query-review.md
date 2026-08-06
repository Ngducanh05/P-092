# Index and Query Review

Final hot-path indexes:

- `ix_resident_unit_memberships_resident_active`
- `ix_resident_unit_memberships_unit_active`
- `ix_ticket_attachment_upload_sessions_resident_status`
- `ix_ticket_attachment_upload_sessions_expires_at`
- `ix_ticket_status_history_ticket_created_at`
- `ix_notifications_recipient_auth_unread_created_at`
- `ix_audit_logs_actor_auth_created_at`

BQL system-wide MVP ticket reads use ticket filters and priority ordering.
