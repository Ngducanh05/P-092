# FixIt Agent API

FastAPI backend for apartment issue intake, AI-assisted triage, BQL coordination, and Technician assignment workflows. Authentication is delegated to Supabase Auth; PostgreSQL/Supabase stores business profiles and tickets; Row Level Security remains defense in depth.

## Source-of-truth product model

The runtime supports three human actors:

- **Resident** — signs in with Supabase phone OTP and uses a `public.residents` profile.
- **BQL Coordinator** — signs in with Supabase email/password and uses a backend-provisioned `public.bql_staff` profile.
- **Technician** — signs in with Supabase email/password and uses a backend-provisioned `public.technician_profiles` profile.

Identity is normalized as:

```text
auth.users
├── public.residents
├── public.bql_staff
└── public.technician_profiles
```

A Supabase Auth UUID may belong to exactly one business profile. The application does **not** restore `public.users` or `role_enum`, and it never trusts a client-supplied role.

## Implemented Technician restoration

Alembic revision `f6a7b8c9d0e1` follows the already-applied `e5f6a7b8c9d0` revision and restores:

- `technician_profiles`
- `technician_skills`
- `ticket_assignments`
- `assignment_status_enum`
- one-active-assignment-per-ticket enforcement
- three-profile conflict prevention
- assignment-scoped Technician RLS
- Auth foreign keys to `auth.users`

The revision is additive and has not been executed automatically against a live Supabase database.

## Assignment lifecycle

BQL can assign only a ticket in `waiting_assignment` with a valid Category to an active, available Technician whose skills match that Category.

```text
Ticket: waiting_assignment -> assigned -> in_progress
Assignment: assigned -> accepted -> in_progress
Assignment: assigned|accepted|in_progress -> unable_to_handle
Ticket after unable_to_handle -> waiting_assignment
```

Each assignment writes status history, an audit event, and notifications. Technician work lists are ordered by product urgency: P3, then P2, then P1. Legacy P4 remains only because Priority cleanup is outside this migration phase.

Secure Technician completion-photo uploads are not yet implemented. A `completed` request is rejected with `COMPLETION_EVIDENCE_REQUIRED` rather than accepting a raw object path or reusing Resident-owned upload sessions.

## API

Public health endpoints:

- `GET /health`
- `GET /ready`

Authenticated actor endpoint:

- `GET /api/v1/auth/me`

Resident endpoints:

- `GET /api/v1/units/my`
- `POST /api/v1/storage/ticket-attachments/upload-url`
- `POST /api/v1/tickets`
- `GET /api/v1/tickets/my`
- `GET /api/v1/tickets/{ticket_id}`
- `GET /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url`

BQL endpoints:

- `GET /api/v1/bql/tickets`
- `GET /api/v1/bql/technicians`
- `POST /api/v1/bql/tickets/{ticket_id}/assign`

Technician endpoints:

- `GET /api/v1/technician/assignments`
- `GET /api/v1/technician/assignments/{assignment_id}`
- `GET /api/v1/technician/assignments/{assignment_id}/attachments/{attachment_id}/download-url`
- `POST /api/v1/technician/assignments/{assignment_id}/accept`
- `POST /api/v1/technician/assignments/{assignment_id}/status`

Technician authorization is derived from the verified token subject. Another Technician's assignment and an unassigned ticket are masked as `404`.

## Trusted profile provisioning

BQL and Technician profiles are never auto-provisioned from unknown email-only tokens.

```powershell
python scripts/provision_bql_staff.py --help
python scripts/provision_technician.py --help
```

Technician provisioning requires an existing Supabase Auth UUID and matching email, uses parameterized SQL, refuses Resident/BQL profile conflicts, supports `--dry-run`, and never accepts a password.

## Security

- The backend receives Supabase access tokens, not OTPs or passwords.
- Resident ownership is derived from the verified profile and active unit membership.
- BQL identity is derived from an active `bql_staff` profile.
- Technician access is limited to the Technician's own active assignments and their parent tickets.
- Private Storage paths, score breakdowns, audit payloads, and service keys are not exposed in ordinary API responses.
- Direct client mutations of assignment, audit, AI, and scoring workflows are denied; FastAPI performs backend-controlled transactions.
- Signed Storage URLs remain short-lived.

## Configuration

Copy `.env.example` to `.env` locally and provide development credentials. Never commit `.env`.

Opt-in live tests support:

```text
SUPABASE_TEST_RESIDENT_ACCESS_TOKEN
SUPABASE_TEST_BQL_ACCESS_TOKEN
SUPABASE_TEST_TECHNICIAN_ACCESS_TOKEN
```

Token values must never be printed or committed.

## Development

```powershell
python -m pip install -r requirements-dev.txt
python -m uvicorn src.main:app --reload --port 8000
```

Documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

Validation commands:

```powershell
python -m pip check
python -m ruff check src tests scripts alembic
python scripts/scan_secrets.py
python -m pytest tests -q
python -m alembic heads
python -m alembic history
git diff --check
```

Do not run a live migration until `DATABASE_URL` is confirmed as a safe development/test target and `ALLOW_LIVE_MIGRATION=true` is set deliberately.

## Scope note

This change completes the Technician restoration phase. The lead specifications also define broader P0/Priority/Category/Severity alignment, the final AI scoring pipeline, Density, batching, reporting, Celery/Redis, and frontend behavior. Those areas are separate implementation phases and are not falsely claimed as complete here.
