# FixIt Agent API

FixIt Agent is a FastAPI backend for resident incident reporting and ticket operations. This repository keeps the AI20K deliverable structure and starter LangGraph code, but the implemented backend scope here is limited to T-006 and T-007.

## Actors

- Resident: authenticates with Supabase phone OTP and creates/views own unit tickets.
- Coordinator: authenticates with Supabase email/password and has system-wide ticket read access for this MVP.
- Technician: authenticates with Supabase email/password; provisioning exists, technician workflow is deferred.

## Implemented In T-006/T-007

- Supabase Bearer JWT verification via JWKS, Auth server, or auto mode.
- `public.users.id = auth.users.id` profile mapping.
- Resident profile auto-provisioning only as `resident`.
- Backend-only coordinator/technician provisioning helper.
- Private Supabase Storage signed upload flow for ticket images.
- Resident ticket creation/list/detail and coordinator ticket list.
- Additive Alembic migrations for Supabase-compatible users and RLS identity policies.
- Stable API error contract.

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

Never expose `SUPABASE_SECRET_KEY` to the frontend.

## Migrations

```powershell
python -m alembic heads
python -m alembic history
python -m alembic upgrade head
python -m alembic current
```

Live Supabase migration must be limited to development/test and gated with `ALLOW_LIVE_MIGRATION=1`. See `docs/backend/t006-t007-live-validation.md`.

## Run

```powershell
python -m uvicorn src.main:app --reload --port 8000
```

Swagger UI: `http://localhost:8000/docs`

## API

Core paths:

- `GET /health`
- `GET /api/v1/auth/me`
- `GET /api/v1/units/my`
- `POST /api/v1/storage/ticket-attachments/upload-url`
- `POST /api/v1/tickets`
- `GET /api/v1/tickets/my`
- `GET /api/v1/tickets/{ticket_id}`
- `GET /api/v1/coordinator/tickets`

Legacy starter agent routes are still mounted as `/api/v1/chat` and `/api/v1/status`, tagged as Agent Legacy.

## Tests

```powershell
python -m ruff check src tests scripts alembic
python -m pytest tests -v
python -m alembic heads
python -m alembic history
python -c "from src.main import app; print(app.title)"
```

Integration tests that touch Supabase are skipped unless `RUN_SUPABASE_INTEGRATION_TESTS=1`; migration actions also require `ALLOW_LIVE_MIGRATION=1`.

## Security Notes

- FastAPI never receives user passwords or OTPs.
- Role authorization uses `public.users.role`, not editable JWT metadata.
- Unknown Auth users are auto-provisioned only as residents.
- Storage buckets are private; signed URLs are short-lived.
- Database stores private storage paths, not permanent public URLs.
- `estimated_resolution_at` is currently `null` and `estimated_resolution_text` is `Đang phân tích` until an approved SLA formula exists.
