# FixIt Agent API

Backend API for apartment maintenance reporting with Supabase Auth, FastAPI, SQLAlchemy, Alembic, private Supabase Storage, and resident ticket workflows.

## Actors

- Resident: Supabase phone OTP identity with a `public.residents` profile.
- BQL: Supabase email/password identity with a backend-provisioned `public.bql_staff` profile.

There is no final runtime Technician actor, `public.users` table, or `role_enum`.

## Architecture

Frontend authenticates directly with Supabase Auth, then sends `Authorization: Bearer <access_token>` to FastAPI. FastAPI verifies the JWT, resolves exactly one profile from `residents` or `bql_staff`, runs authorization/business logic, and writes to PostgreSQL/Supabase. RLS remains defense in depth.

Unknown valid Supabase users may be auto-provisioned as Residents only when the token contains a valid normalized E.164 phone claim. Email-only tokens are rejected unless a BQL staff profile already exists. BQL profiles are created with `scripts/provision_bql_staff.py`.

## API

- `GET /health`
- `GET /ready`
- `GET /api/v1/auth/me`
- `GET /api/v1/units/my`
- `POST /api/v1/storage/ticket-attachments/upload-url`
- `POST /api/v1/tickets`
- `GET /api/v1/tickets/my`
- `GET /api/v1/tickets/{ticket_id}`
- `GET /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url`
- `GET /api/v1/bql/tickets`

`/api/v1/auth/me` returns an actor-discriminated response with `actor_type` of `resident` or `bql`. No persisted role is exposed.

## Security

The backend never receives OTPs or passwords, never trusts client-sent ownership IDs, and never returns private Storage object paths in normal API responses. Signed upload and download URLs are short lived. Supabase secret keys stay backend-only. Audit data and internal AI scoring fields remain restricted.

Legacy ticket statuses `waiting_assignment` and `assigned` remain in the PostgreSQL enum for migration safety, but new Technician assignment transitions are not generated pending an approved lifecycle migration.

## Development

```powershell
python -m pip install -r requirements-dev.txt
python -m uvicorn src.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`
OpenAPI JSON: `http://localhost:8000/openapi.json`
