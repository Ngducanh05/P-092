# FixIt Agent API

FixIt Agent is a FastAPI backend for resident incident reporting and ticket operations. This repository keeps the AI20K deliverable structure and starter LangGraph code, but the implemented backend scope here is limited to T-006 and T-007.

## Actors

- Resident: authenticates with Supabase phone OTP and creates/views own unit tickets.
- Coordinator: authenticates with Supabase email/password and has system-wide ticket read access for this MVP.
- Technician: authenticates with Supabase email/password; provisioning exists, technician workflow is deferred.

## T-006/T-007 Status

- T-006 COMPLETE. The FastAPI routes, role checks, stable errors, upload-session ticket creation, `/health`, `/ready`, and authorized attachment download flow are covered by default tests.
- T-007 IMPLEMENTED — LIVE VALIDATION BLOCKED. Supabase-compatible user schema, JWT verification modes, live-migration safety, private Storage helpers, RLS migrations, and gated live integration tests are implemented. T-007 is not COMPLETE until migration, Auth, RLS, and Storage pass on a confirmed Supabase development/test project.

## Out Of Scope

Formula H, P0/manual review, category/priority override, technician assignment/work list/status updates, notification delivery, report export, LangGraph internals, frontend, production migration, Railway deployment, and Vercel deployment are deferred. See `docs/backend/deferred-backend-work.md`.

## Architecture

Frontend authenticates directly with Supabase Auth, then sends `Authorization: Bearer <access_token>` to FastAPI. FastAPI verifies the token, loads `public.users` by JWT `sub`, and performs authorization/business operations. Business data is accessed through FastAPI; RLS is defense-in-depth.

Target deployment shape:

- Frontend: Vercel
- Backend: Railway
- Auth/Database/Storage: Supabase

## Local Setup

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
copy .env.example .env
```

Fill `.env` with development/test credentials only. `DATABASE_URL` must point to PostgreSQL/Supabase outside tests.

## Environment

Important settings:

- `APP_NAME=FixIt Agent API`
- `APP_ENV=development`
- `DATABASE_URL=postgresql://user:password@host:5432/database`
- `SUPABASE_URL=https://your-project-ref.supabase.co`
- `SUPABASE_PUBLISHABLE_KEY=your-publishable-key`
- `SUPABASE_SECRET_KEY=your-backend-secret-key`
- `SUPABASE_JWT_AUDIENCE=authenticated`
- `SUPABASE_JWT_VERIFICATION_MODE=auto`
- `SUPABASE_STORAGE_BUCKET=ticket-attachments`
- `SUPABASE_SIGNED_DOWNLOAD_TTL_SECONDS=300`
- `MAX_TICKET_IMAGE_BYTES=10485760`
- `ALLOWED_TICKET_IMAGE_MIME_TYPES=image/jpeg,image/png,image/webp`
- `ENABLE_LEGACY_AGENT_ROUTES=false`
- `ALLOW_LIVE_MIGRATION=false`
- `RUN_SUPABASE_INTEGRATION_TESTS=false`

Never expose `SUPABASE_SECRET_KEY` to the frontend. It may be a current `sb_secret_*` key or a legacy service-role JWT; backend admin clients send `sb_secret_*` keys only as `apikey`, while legacy JWTs also keep Bearer compatibility.

## Migrations

```powershell
python -m alembic heads
python -m alembic history
```

Online migration is blocked unless `APP_ENV` is `development` or `test` and `ALLOW_LIVE_MIGRATION=true`. Never enable the gate for production. See `docs/backend/t006-t007-live-validation.md`.

## Run

```powershell
python -m uvicorn src.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

## API

Core paths:

- `GET /health`
- `GET /ready`
- `GET /api/v1/auth/me`
- `GET /api/v1/units/my`
- `POST /api/v1/storage/ticket-attachments/upload-url`
- `POST /api/v1/tickets`
- `GET /api/v1/tickets/my`
- `GET /api/v1/tickets/{ticket_id}`
- `GET /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url`
- `GET /api/v1/coordinator/tickets`

Ticket creation accepts `attachment_upload_ids`, not raw private object paths. Ticket responses expose attachment metadata and a download URL endpoint, not private storage paths.

Legacy starter Agent routes are disabled by default. They can be mounted only in development with `ENABLE_LEGACY_AGENT_ROUTES=true`; T-006/T-007 does not depend on them.

## Tests

```powershell
python scripts/check_t006_t007_environment.py
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
python -m pip check
python -m ruff check src tests scripts alembic
python scripts/scan_secrets.py
python -m pytest tests -v
python -m alembic heads
python -m alembic history
python -c "from src.main import app; print(app.title)"
```

Integration tests that touch Supabase are skipped unless `RUN_SUPABASE_INTEGRATION_TESTS=true`; migration actions also require `ALLOW_LIVE_MIGRATION=true`.

## Security Notes

- FastAPI never receives user passwords or OTPs.
- Role authorization uses `public.users.role`, not editable JWT metadata.
- Unknown Auth users are auto-provisioned only as residents.
- Storage buckets are private; signed upload targets are fixed at 7200 seconds and signed download URLs use the configured short TTL.
- `/ready` checks local database connectivity, current Alembic revision where practical, and Supabase Auth/Storage configuration presence. It is not a full Supabase end-to-end validation.
- Upload sessions prevent clients from forging raw object paths during ticket creation.
- Database stores private storage paths only in trusted attachment records, not in normal public ticket responses.
- `estimated_resolution_at` is currently `null` and `estimated_resolution_text` is `Đang phân tích` until an approved SLA formula exists.
