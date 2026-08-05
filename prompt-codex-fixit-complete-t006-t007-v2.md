# CODEX FIX PROMPT — Complete FixIt T-006 and T-007

## 0. Mission

Work inside the existing repository:

```text
C:\TEAM PROJECT\P-092
```

The current repository already contains an initial implementation of:

```text
T-006 — Main FixIt FastAPI endpoints
T-007 — Supabase Database, Auth, Storage, and RLS integration
```

The latest reviewed implementation was based on commit:

```text
6bf7608 — API done
```

Do not rebuild the project from scratch.

Review the actual current working tree and improve the existing implementation until T-006 and T-007 are genuinely complete, tested, and documented.

The current implementation has a useful structure, but it still contains security, migration, Storage, JWT, and testing gaps.

Do not claim completion based only on static source-string tests.

Do not commit or push.

---

# 1. Strict scope

Complete only:

```text
T-006
- FixIt API routing
- Supabase Bearer authentication dependency
- resident unit/ticket API
- coordinator ticket-read API
- private attachment upload/download flow
- transaction boundaries
- stable errors
- actual unit/API/service tests

T-007
- Supabase-compatible user schema
- Auth user → public profile mapping
- PostgreSQL/Alembic migrations
- Supabase JWT verification
- RLS identity binding
- private Storage integration
- safe privileged-user provisioning
- live development/test validation when credentials allow
```

Do not implement:

```text
Formula H
Scoring algorithm
LangGraph internals
OpenAI calls
P0/manual review
Category override
Priority override
Technician assignment workflow
Technician work queue
Notification delivery
Frontend
Railway production deployment
Vercel production deployment
Production migration
```

The repository may contain `OPENAI_API_KEY` in `.env`.

It is unrelated to T-006/T-007.

Do not read, print, validate, or use the OpenAI key.

Do not call OpenAI.

---

# 2. Existing architecture decisions to preserve

Preserve these accepted decisions:

```text
Frontend authenticates directly with Supabase Auth.
FastAPI receives Authorization: Bearer <Supabase access token>.
FastAPI validates the token.
public.users.id = auth.users.id = JWT sub.

RESIDENT:
phone + SMS OTP
unknown valid Auth users may be provisioned only as resident

COORDINATOR:
email + password
trusted backend provisioning only
system-wide ticket read access for MVP

TECHNICIAN:
email + password
trusted backend provisioning only
workflow remains deferred

ADMIN:
enum may remain for compatibility
no ADMIN permission implementation in this scope
```

Storage architecture:

```text
private Supabase bucket
→ Backend creates signed upload target
→ Frontend uploads directly
→ Backend stores stable private object path and verified metadata
→ Backend creates short-lived signed download URLs after ticket authorization
```

Business data is accessed through FastAPI.

RLS is defense-in-depth.

Direct authenticated mutations of business tables remain denied.

---

# 3. Environment and secret rules

A local `.env` already exists and may contain:

```text
SUPABASE_URL
DATABASE_URL
Supabase keys
OPENAI_API_KEY
other development credentials
```

## 3.1 Never expose secrets

Codex must never:

```text
cat .env
print complete environment values
print access tokens
print database passwords
print Supabase secret/publishable keys
print OpenAI keys
copy secrets into documentation
copy secrets into tests
copy secrets into command output
commit .env
```

Only check whether required variable names are present.

Create or improve a safe environment-check script:

```text
scripts/check_t006_t007_environment.py
```

It may print only:

```text
VARIABLE_NAME: PRESENT
VARIABLE_NAME: MISSING
```

It must never print values.

## 3.2 Required variables

Static/unit work must not require live credentials.

Live Supabase work requires the relevant subset of:

```text
APP_ENV
DATABASE_URL
SUPABASE_URL
SUPABASE_PUBLISHABLE_KEY
SUPABASE_SECRET_KEY
SUPABASE_STORAGE_BUCKET
ALLOW_LIVE_MIGRATION
RUN_SUPABASE_INTEGRATION_TESTS
```

Optional live test tokens:

```text
SUPABASE_TEST_RESIDENT_ACCESS_TOKEN
SUPABASE_TEST_COORDINATOR_ACCESS_TOKEN
SUPABASE_TEST_TECHNICIAN_ACCESS_TOKEN
```

Do not automate or intercept SMS OTP.

For phone Auth integration testing, use only a manually supplied test access token.

## 3.3 Safety gate

Run live migration only when:

```text
APP_ENV is test or development
ALLOW_LIVE_MIGRATION is true
DATABASE_URL is present
target is explicitly confirmed as non-production
```

Run live Supabase integration tests only when:

```text
APP_ENV is test or development
RUN_SUPABASE_INTEGRATION_TESTS is true
all variables required by the selected scenarios are present
```

Do not change safety flags from false to true automatically.

If the flags or credentials are missing:

```text
complete all static/unit implementation
do not run unsafe commands
report the exact missing variable names
mark live validation BLOCKED
```

Never run against production.

---

# 4. Initial inspection

Before editing, run:

```powershell
git status
git --no-pager diff
git log --oneline -10
python -c "import sys; print(sys.executable)"
python scripts/check_t006_t007_environment.py
```

The Python path must be:

```text
C:\TEAM PROJECT\P-092\.venv\Scripts\python.exe
```

Inspect all relevant files, including:

```text
requirements.txt
.env.example
.gitignore
README.md
src/config.py
src/main.py
src/api/
src/security/supabase_jwt.py
src/repositories/
src/services/
src/models/api/
src/database/
src/database/models/
alembic/
tests/
scripts/
docs/backend/
.github/workflows/
Dockerfile
docker-compose.yml
```

Specifically inspect:

```text
src/api/routes.py
src/api/routes/
```

because both currently exist and can cause confusion.

Do not delete unrelated work.

---

# 5. Baseline commands

Before making changes, run:

```powershell
python -m pip check
python -m ruff check src tests scripts alembic
python -m pytest tests -v
python -m alembic heads
python -m alembic history
```

Record failures before fixing them.

Do not hide existing failures.

---

# 6. Dependency management

The repository uses:

```text
requirements.txt
```

Current runtime code uses:

```text
httpx
PyJWT[crypto]
```

Ensure every package imported by runtime, tests, migration helpers, and scripts is declared in `requirements.txt`.

Rules:

- Do not leave a package installed only in `.venv`.
- Do not run `pip freeze > requirements.txt`.
- Keep direct dependencies only.
- Keep runtime dependencies under a runtime-appropriate section.
- `httpx` is a runtime dependency, not merely a dev dependency.
- `PyJWT[crypto]` is a runtime dependency.
- Do not add the full Supabase Python SDK unless the final implementation actually imports it.
- Avoid multiple JWT libraries.
- Run:
  ```powershell
  python -m pip install -r requirements.txt
  python -m pip check
  ```

In the final report, list every dependency added, removed, or moved and explain why.

---

# 7. Fix JWT verification completely

Files involved:

```text
src/security/supabase_jwt.py
src/api/dependencies/auth.py
src/config.py
tests/test_security/test_supabase_jwt.py
tests/test_auth/
```

## 7.1 Correct auto-mode behavior

Supabase projects may use:

```text
asymmetric signing:
RS256 / ES256
→ verify through JWKS

shared-secret signing:
HS256
→ verify directly with Supabase Auth server
```

The current `auto` implementation rejects HS256 before fallback.

Fix it.

Required behavior:

```text
mode=jwks
- accept only approved asymmetric algorithms
- reject HS256
- never perform Auth-server fallback

mode=auth_server
- validate through /auth/v1/user
- reject invalid, expired, malformed, or unauthorized token

mode=auto
- inspect unverified token header safely
- HS256 → Auth-server verification
- supported asymmetric algorithm → JWKS verification
- missing/empty compatible JWKS for a shared-secret project → Auth-server verification
- invalid asymmetric signature → reject, do not fallback
- wrong issuer → reject, do not fallback
- wrong audience → reject, do not fallback
- expired token → reject, do not fallback
- malformed token → reject, do not fallback
```

Do not trust the token header algorithm without an allowlist.

Reject:

```text
alg=none
missing alg
unknown algorithm
missing sub
invalid UUID sub
missing exp
expired token
wrong iss
wrong aud
missing kid for asymmetric token
unknown signing key
```

## 7.2 Auth-server verification

For:

```text
GET <SUPABASE_URL>/auth/v1/user
```

send:

```text
apikey: SUPABASE_PUBLISHABLE_KEY
Authorization: Bearer <token>
```

Never use `SUPABASE_SECRET_KEY` for normal user-token verification.

Handle status codes explicitly:

```text
200 → valid
401/403 → AUTH_TOKEN_INVALID
429 → AUTH_SERVICE_UNAVAILABLE
5xx → AUTH_SERVICE_UNAVAILABLE
network timeout/error → AUTH_SERVICE_UNAVAILABLE
invalid response JSON → AUTH_SERVICE_UNAVAILABLE
```

Add:

```text
AUTH_SERVICE_UNAVAILABLE
```

to the stable error contract.

Do not pass raw Supabase response bodies to clients.

After the Auth server confirms the token:

- safely decode unverified claims only to obtain `exp`, `iss`, and `aud`,
- require that JWT `sub` matches the user ID returned by Supabase,
- require a real expiry,
- do not invent `expires_at = now + 300`,
- reject inconsistent token/user information.

## 7.3 Shared verifier cache

The current dependency creates a new verifier on each request, which defeats JWKS caching.

Implement a cached dependency, for example:

```python
@lru_cache
def get_supabase_jwt_verifier() -> SupabaseJWTVerifier:
    return SupabaseJWTVerifier(get_settings())
```

Inject the verifier into `get_current_principal()`.

Tests must be able to override it.

Implement key refresh behavior for unknown `kid` without creating unbounded network requests.

## 7.4 JWT tests

Add real tests for:

```text
valid RS256 token
valid ES256 token when supported
alg=none rejected
HS256 auto mode calls Auth server
HS256 jwks mode rejected
expired token
wrong issuer
wrong audience
missing sub
invalid UUID sub
missing exp
missing kid
unknown kid with one refresh
invalid signature does not fallback
empty JWKS allows only correct auto fallback
Auth server 200
Auth server 401
Auth server 403
Auth server 429
Auth server 500
Auth server timeout
Auth server sub mismatch
cached verifier dependency reused
```

Use generated test keys and HTTP mocks.

Never use a real access token in unit tests.

---

# 8. Fix current-user provisioning and phone normalization

Files involved:

```text
src/api/dependencies/auth.py
src/repositories/user_repository.py
src/services/auth_service.py
src/database/models/user.py
tests/test_auth/
```

## 8.1 Phone format

Normalize phone numbers before persistence.

Use strict E.164 semantics:

```text
leading +
country code cannot begin with 0
7–15 digits after +
no spaces
no dashes
no parentheses
```

Do not guess a country code.

Do not silently convert a local Vietnamese number such as `09...` to `+84...` without an approved country context.

A Supabase phone claim that is not valid normalized E.164 must be rejected as:

```text
AUTH_PROFILE_INVALID
```

Add a database check constraint for normalized phone format when PostgreSQL is used.

## 8.2 Safe resident auto-provision

Unknown valid Auth users may be provisioned only as:

```text
Role.RESIDENT
```

Never trust role from:

```text
request body
user_metadata
raw_user_meta_data
JWT postgres role
email domain
phone prefix
```

Use safe concurrent insertion.

Do not call `db.rollback()` in a helper in a way that can discard unrelated request work.

Use one of:

```text
PostgreSQL INSERT ... ON CONFLICT DO NOTHING
nested transaction/savepoint
safe flush + recovery without corrupting outer transaction
```

After a race, re-query and return the existing user.

Do not silently overwrite conflicting email/phone values.

Do not auto-promote an existing user.

## 8.3 Tests

Test actual dependency behavior, not only model construction:

```text
existing resident
new email resident
new phone resident
new user always becomes resident
metadata role=coordinator ignored
metadata role=technician ignored
inactive user rejected
missing both email and phone rejected
invalid E.164 phone rejected
email conflict rejected
phone conflict rejected
concurrent insert returns one profile
database error rolls back safely
```

---

# 9. Correct Supabase user migration

Current migration:

```text
a1b2c3d4e5f6_align_users_with_supabase_auth.py
```

Review whether it has been applied on any development database.

Do not assume.

## 9.1 Migration-history rule

If a migration has already been applied to a shared database:

```text
do not rewrite it
create an additive corrective migration
```

If it has never been applied anywhere and there is explicit evidence that it is still unpublished migration code:

```text
it may be corrected in place
but document why
```

Prefer additive correction when uncertain.

## 9.2 Required database guarantees

Final schema must guarantee:

```text
public.users.id is supplied by Supabase Auth UUID
email nullable
phone_number nullable
full_name nullable
email unique when non-null
phone unique when non-null
email or phone must exist
phone must be normalized E.164 when non-null
no password/OTP/token columns
```

## 9.3 Auth foreign key

The current migration adds:

```text
public.users.id → auth.users.id
NOT VALID
```

Do not leave the project falsely claiming the FK is fully active.

Implement a safe validation process:

1. Detect whether `auth.users` exists.
2. Detect orphan application profiles:
   ```sql
   SELECT public.users.id
   FROM public.users
   LEFT JOIN auth.users ON auth.users.id = public.users.id
   WHERE auth.users.id IS NULL;
   ```
3. Do not delete orphan rows automatically.
4. If orphans exist:
   - stop FK validation,
   - report the orphan count only,
   - provide a remediation document,
   - mark live migration BLOCKED.
5. If there are no orphans:
   ```sql
   ALTER TABLE public.users
   VALIDATE CONSTRAINT fk_users_id_auth_users;
   ```

Create:

```text
docs/backend/supabase-user-migration-remediation.md
```

Do not include user PII or IDs in the report.

## 9.4 Downgrade safety

Phone-only residents make a downgrade to non-null email unsafe.

Do not provide a downgrade that unexpectedly fails or destroys user data.

Use one of:

```text
safe precondition and explicit failure message
or
documented irreversible boundary for the contact-model downgrade
```

Never fill fake emails to make downgrade pass.

Add migration tests covering upgrade and downgrade behavior.

---

# 10. Repair RLS migration integrity

Current migration:

```text
b2c3d4e5f6a7_bind_supabase_auth_identity_policies.py
```

The current `upgrade()` drops old policies and creates new ones, but its `downgrade()` only removes new policies and does not restore the previous state.

Fix migration integrity.

## 10.1 History rule

As with every migration:

- if already applied in a shared environment, do not rewrite history;
- create a corrective migration;
- if proven unpublished/unapplied, correcting in place is acceptable.

Document the decision.

## 10.2 Final forward RLS behavior

Keep:

```text
TO authenticated
(select auth.uid())
active membership ownership
active technician assignment ownership
coordinator system-wide read for MVP
client mutation denied
AI/scoring direct client access denied
audit direct client access denied
security_invoker views
```

Add explicit unauthenticated protection where useful:

```sql
(select auth.uid()) IS NOT NULL
```

Ensure columns used by RLS predicates are indexed.

## 10.3 Attachment upload-session policies

The new upload-session table introduced later in this prompt must:

```text
have RLS enabled
deny direct anon/authenticated access by default
be written/read through trusted Backend only
```

Do not expose backend upload-session state directly through Supabase table APIs.

## 10.4 Downgrade

The final migration chain must return to the exact expected prior policy state.

Tests must verify:

```text
upgrade creates expected policies
downgrade removes new policies
downgrade restores required previous deny-by-default policies when applicable
no pending_identity remains in final head
no NULL::uuid remains in final head
no anonymous business-table access
```

Do not use string-only assertions as the sole evidence.

When a safe PostgreSQL test database is available, execute migration upgrade/downgrade there.

---

# 11. Replace raw attachment paths with upload sessions

The current API accepts:

```text
attachment_storage_paths: list[str]
```

This loses MIME/size metadata and permits forged paths when Storage verification is unavailable.

Replace the public flow with upload sessions.

## 11.1 New table

Create an ORM model and additive migration for:

```text
ticket_attachment_upload_sessions
```

Recommended fields:

```text
id UUID primary key
owner_user_id UUID not null → users.id
storage_path string not null unique
original_filename string nullable
mime_type string not null
file_size integer not null
status string/check constraint:
    pending
    consumed
    expired
expires_at timestamptz not null
object_verified_at timestamptz nullable
consumed_at timestamptz nullable
created_at timestamptz not null
updated_at timestamptz not null
```

Constraints:

```text
file_size > 0
valid supported MIME type
pending session not reusable after consumption
expires_at > created_at
storage_path length bounded
```

Indexes:

```text
owner_user_id + status
expires_at
storage_path unique
```

Do not store:

```text
signed URL
signed token
service key
access token
file bytes
```

## 11.2 Signed upload endpoint

Keep:

```text
POST /api/v1/storage/ticket-attachments/upload-url
```

The endpoint must:

1. authenticate a resident;
2. validate metadata;
3. generate a server-owned object path;
4. request a Supabase signed upload target;
5. create an upload-session row;
6. return:
   ```text
   upload_id
   signed upload URL or upload token
   expires_in
   required headers
   ```
7. not require the client to later submit the raw path.

Do not create an upload-session row if Supabase fails to create the signed target.

Use a transaction.

## 11.3 Signed upload expiry

Supabase signed upload URLs are currently fixed at:

```text
2 hours
```

The current code returns a configurable 300-second expiry without sending that TTL to Supabase.

Remove this false behavior.

Use:

```text
SIGNED_UPLOAD_EXPIRY_SECONDS = 7200
```

or derive an explicit expiry returned by Supabase if the API provides one.

Do not expose a configurable signed-upload TTL unless the Supabase endpoint actually honors it.

Update:

```text
src/config.py
.env.example
schemas
tests
README
Storage docs
```

Signed download TTL may remain configurable because the download-signing endpoint accepts expiry.

## 11.4 Ticket creation request

Replace:

```text
attachment_storage_paths
```

with:

```text
attachment_upload_ids: list[UUID]
```

Bound the count.

Reject duplicates.

Do not accept raw object paths from the public request.

## 11.5 Consume upload sessions transactionally

During ticket creation:

1. lock selected upload-session rows;
2. verify every session:
   ```text
   belongs to current resident
   status=pending
   not expired
   not already consumed
   path has expected owner prefix
   object exists in Storage
   metadata is still acceptable
   ```
3. create the ticket;
4. create initial status history;
5. create `ticket_attachments` with:
   ```text
   storage path
   mime_type
   file_size
   meaningful file_type
   ```
6. mark upload sessions consumed;
7. commit all database changes in one transaction.

On any failure:

```text
rollback ticket
rollback status history
rollback attachments
do not mark sessions consumed
```

Do not silently skip object verification when attachment IDs are supplied.

If Storage is not configured:

```text
return STORAGE_NOT_CONFIGURED
```

## 11.6 Expired sessions

Add a safe maintenance command:

```text
scripts/expire_attachment_upload_sessions.py
```

It may mark expired pending sessions as expired.

It must not delete objects automatically unless explicitly requested and safely scoped.

Support:

```text
--dry-run
```

---

# 12. Fix Supabase Storage HTTP behavior

Files:

```text
src/services/storage_service.py
src/api/routes/storage.py
src/models/api/storage.py
tests/test_services/test_storage_service.py
```

## 12.1 HTTP client

Use an injectable HTTP client.

Do not call module-level `httpx.post()` and `httpx.head()` directly in ways that are difficult to test.

Handle:

```text
timeouts
DNS/network errors
401/403
404
409
429
5xx
invalid JSON
missing signedURL/token
```

Map them to stable safe domain errors.

Do not return `"None"` as a signed URL.

## 12.2 Upload response

Accept the Supabase response field names actually returned by the API.

Require at least one usable upload credential:

```text
signed URL
or
upload token
```

If neither exists, return a safe Storage failure.

Never return a secret key.

## 12.3 Object verification

Use a Supabase Storage API operation that is actually supported for object existence/metadata verification.

Do not assume `HEAD` is supported without evidence.

The verification implementation must be:

```text
injectable
mockable
covered by tests
strict when attachments are submitted
```

Do not treat missing configuration as successful verification.

## 12.4 Bucket configuration

Create or improve a backend-only idempotent setup script:

```text
scripts/setup_supabase_storage.py
```

It must:

```text
require SUPABASE_SECRET_KEY
support --dry-run
create the configured bucket if missing
ensure the bucket is private
set maximum file size
set allowed MIME types:
    image/jpeg
    image/png
    image/webp
never print secrets
never make the bucket public
not overwrite unrelated bucket settings blindly
```

Document exact manual Dashboard steps when automated configuration cannot safely determine current state.

---

# 13. Add authorized signed-download API

The current service contains a download signer but no authorized route.

Add:

```text
GET /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url
```

Allowed roles in this scope:

```text
RESIDENT:
only when active membership grants access to the ticket

COORDINATOR:
system-wide read for MVP
```

Technician access remains deferred.

The route must:

1. authenticate;
2. authorize the parent ticket;
3. verify the attachment belongs to the ticket;
4. generate a short-lived signed download URL;
5. return:
   ```text
   attachment_id
   signed_download_url
   expires_in
   mime_type
   file_size
   ```
6. never return Storage secret values.

Unauthorized or nonexistent attachment must return:

```text
404 ATTACHMENT_NOT_FOUND
```

Do not reveal that another resident's attachment exists.

Add the stable error code:

```text
ATTACHMENT_NOT_FOUND
```

## 13.1 Public ticket response

Do not expose raw private storage paths in normal API responses.

Change attachment response to include:

```text
id
mime_type
file_size
download_url_endpoint or downloadable flag
```

The frontend obtains a signed download URL through the authorized endpoint.

Update schemas, tests, docs, and README.

---

# 14. Fix ticket service and repository tests

Current repository tests mostly inspect source strings.

Replace or supplement them with real behavior tests.

## 14.1 Ticket service tests

Add tests for:

```text
one active unit → automatically selected
multiple active units without unit_id → UNIT_SELECTION_REQUIRED
multiple units with owned unit → success
submitted unowned unit → 404 UNIT_NOT_FOUND
no active unit → NO_ACTIVE_UNIT
resident_id derived from current user
status always NEW
initial status history created
upload sessions locked and validated
wrong owner upload rejected
expired upload rejected
consumed upload rejected
missing upload rejected
Storage not configured with attachments → STORAGE_NOT_CONFIGURED
object missing → INVALID_ATTACHMENT
attachment metadata persisted
upload sessions consumed after commit
failure before commit rolls back all records
duplicate upload IDs rejected
no AI call
no OpenAI call
no scoring result created
ETA remains null / "Đang phân tích"
```

Use mocks/fakes where a real database is unnecessary.

Use PostgreSQL integration tests for actual transaction and locking behavior.

## 14.2 Repository tests

Test executed SQLAlchemy behavior for:

```text
active membership filtering
inactive membership exclusion
resident ticket isolation
created_at descending resident order
coordinator priority P1 → P4, null last
coordinator created_at ascending within same priority
pagination total
date/status/category filters
attachment eager loading
attachment belongs-to-ticket lookup
upload-session lock/select behavior
```

Source-text assertions may remain as supplementary checks, not primary evidence.

---

# 15. Complete API tests

Existing API tests currently verify mainly route existence and authorization failures.

Add actual success and failure tests for:

```text
GET /api/v1/auth/me
GET /api/v1/units/my
POST /api/v1/storage/ticket-attachments/upload-url
POST /api/v1/tickets
GET /api/v1/tickets/my
GET /api/v1/tickets/{ticket_id}
GET /api/v1/coordinator/tickets
GET /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url
GET /health
```

Test:

```text
valid resident success
valid coordinator success
wrong role
missing token
invalid token
inactive user
stable error format
request ID returned
pagination
filters
404 masking unauthorized tickets
no raw path in ticket response
no secrets in any response
```

Use FastAPI dependency overrides.

Do not make network calls in default API unit tests.

---

# 16. Make Supabase integration tests real

The current integration guard skips when the integration flag is enabled.

Replace it.

## 16.1 Required behavior

When:

```text
RUN_SUPABASE_INTEGRATION_TESTS=false
```

integration tests may skip with a clear reason.

When:

```text
RUN_SUPABASE_INTEGRATION_TESTS=true
```

they must not silently skip all scenarios.

If required variables are missing:

```text
fail fast with a list of missing variable names
do not print values
```

## 16.2 Live scenarios

On a development/test Supabase project, verify as available:

```text
Alembic upgrade reaches head
Alembic current equals head
expected schemas/tables exist
users phone/email constraints exist
auth FK is validated or explicitly blocked by orphan profiles
RLS is enabled
final policies exist
anonymous business-table access denied
resident token → /auth/me
coordinator token → /auth/me
resident active membership isolation
resident cannot read another unit's ticket
coordinator can read MVP ticket list
private bucket exists
signed upload target works
small test PNG upload works
upload session created
ticket creation consumes upload session
signed download works after authorization
unauthorized download denied
```

Use uniquely prefixed test data.

Clean up only data created by the tests.

Do not delete shared data.

Do not call OpenAI.

Do not use production.

## 16.3 Test access tokens

Do not automate SMS OTP.

If:

```text
SUPABASE_TEST_RESIDENT_ACCESS_TOKEN
```

is missing, mark the phone-token scenario blocked.

Do not display the token.

The same applies to coordinator test tokens.

---

# 17. Secret scanner repair

Current script:

```text
scripts/scan_secrets.py
```

can skip a real database URL when a placeholder also appears in the same file.

Fix it.

## 17.1 Match-level allowlisting

Evaluate every regex match independently.

Allow only the exact approved placeholder match.

Do not exempt an entire file merely because it contains one placeholder.

## 17.2 Tests

Create temporary tracked-like test content and verify:

```text
known placeholder accepted
real OpenAI-like secret detected
real JWT-like secret detected
real database URL with password detected
file containing both placeholder and real URL still fails
.env skipped
.venv skipped
binary files skipped
secret values never printed
only file path and pattern type printed
```

Run the scanner in CI.

Do not scan the real local `.env`.

---

# 18. Remove legacy route ambiguity and raw errors

The repository currently contains both:

```text
src/api/routes.py
src/api/routes/
```

Inspect imports.

If `src/api/routes.py` is unused:

```text
remove it
```

Do not keep two route implementations with the same semantic name.

## 18.1 Legacy Agent route

The legacy Agent route currently returns:

```text
detail=str(exception)
```

This can leak internal errors.

Fix it.

Preferred approach:

```text
ENABLE_LEGACY_AGENT_ROUTES=false by default
mount legacy routes only when explicitly enabled in development
```

When enabled:

- return a safe error contract;
- log the exception server-side;
- do not expose raw exception strings;
- do not call OpenAI in tests.

The FixIt T-006 API must not depend on legacy Agent routes.

---

# 19. Improve application error logging

Current global exception handler hides details from the client, which is good, but it does not log the exception.

Add safe structured logging:

```text
request_id
method
route/path
exception type
safe message
```

Do not log:

```text
Authorization header
JWT
cookies
database URL
request secrets
Supabase keys
OpenAI key
full sensitive payload
```

Keep client response:

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Internal server error.",
    "details": null,
    "request_id": "..."
  }
}
```

Ensure request ID is included even on errors.

---

# 20. Update CI

Current CI runs:

```text
ruff check src/ tests/
pytest tests/
```

Update it to run:

```powershell
python -m pip install -r requirements.txt
python -m pip check
python -m ruff check src tests scripts alembic
python scripts/scan_secrets.py
python -m pytest tests -v --tb=short
```

Set:

```text
APP_ENV=test
```

Do not add real credentials to GitHub Actions.

Do not run live Supabase integration tests in normal CI.

Integration tests remain separately gated.

---

# 21. Documentation truthfulness

Update:

```text
README.md
docs/backend/t006-t007-gap-analysis.md
docs/backend/t006-t007-api-contract.md
docs/backend/supabase-auth-setup.md
docs/backend/supabase-storage-setup.md
docs/backend/t006-t007-live-validation.md
```

Do not label something `COMPLETE` solely because code exists.

Use:

```text
COMPLETE
IMPLEMENTED — UNIT TESTED
IMPLEMENTED — NOT LIVE TESTED
BLOCKED — MISSING SAFE ENVIRONMENT
BLOCKED — MISSING TEST TOKEN
DEFERRED BY SCOPE
```

## 21.1 Completion status

Only mark T-006 complete when:

```text
all required APIs work
authorization is enforced
service/API tests cover success and failure
attachment upload/download is secure
transactions are tested
full default test suite passes
```

Only mark T-007 complete when:

```text
schema is correct
JWT modes are correct
RLS final head is correct
Storage is private
migration reaches head on safe Supabase
Auth mapping is tested
live RLS/Auth/Storage evidence exists
```

When live environment requirements are missing, state:

```text
T-007 code complete, live validation blocked
```

Do not falsely report production readiness.

---

# 22. Required final API contract

Final routes in this scope:

```text
GET  /health

GET  /api/v1/auth/me
GET  /api/v1/units/my

POST /api/v1/storage/ticket-attachments/upload-url

POST /api/v1/tickets
GET  /api/v1/tickets/my
GET  /api/v1/tickets/{ticket_id}
GET  /api/v1/tickets/{ticket_id}/attachments/{attachment_id}/download-url

GET  /api/v1/coordinator/tickets
```

Deferred:

```text
assignment
status update
P0
override
Formula H
technician list
notifications
```

---

# 23. Validation commands

Run all applicable commands.

## 23.1 Environment safety

```powershell
python scripts/check_t006_t007_environment.py
```

## 23.2 Dependencies

```powershell
python -m pip install -r requirements.txt
python -m pip check
```

## 23.3 Static quality

```powershell
python -m ruff check src tests scripts alembic
python scripts/scan_secrets.py
```

## 23.4 Focused tests

```powershell
python -m pytest tests/test_security/test_supabase_jwt.py -v
python -m pytest tests/test_auth -v
python -m pytest tests/test_repositories -v
python -m pytest tests/test_services -v
python -m pytest tests/test_api -v
python -m pytest tests/test_migrations -v
python -m pytest tests/test_database -v
python -m pytest tests/test_security -v
```

## 23.5 Full suite

```powershell
python -m pytest tests -v
```

## 23.6 App and routes

```powershell
python -c "from src.main import app; print(app.title)"
```

Expected:

```text
FixIt Agent API
```

Verify OpenAPI contains all required routes.

## 23.7 Alembic static

```powershell
python -m alembic heads
python -m alembic history
```

## 23.8 Safe live migration

Only when all safety conditions pass:

```powershell
python -m alembic current
python -m alembic upgrade head
python -m alembic current
```

Do not run:

```text
alembic downgrade base
DROP DATABASE
DROP SCHEMA
TRUNCATE
```

against shared Supabase.

A downgrade test is allowed only on a disposable/local PostgreSQL database.

## 23.9 Live integration

Only when explicitly enabled:

```powershell
python -m pytest tests/integration -v
```

## 23.10 Git review

```powershell
git status
git --no-pager diff
```

Do not commit or push.

---

# 24. Completion checklist

## T-006

- [ ] Auth dependency works.
- [ ] `/auth/me` works.
- [ ] `/units/my` works.
- [ ] Signed upload endpoint works.
- [ ] Ticket creation works transactionally.
- [ ] Resident ticket list works.
- [ ] Resident/coordinator ticket detail works.
- [ ] Coordinator ticket list works.
- [ ] Authorized attachment download signing works.
- [ ] Raw private paths are not returned publicly.
- [ ] Stable errors work.
- [ ] Real service tests exist.
- [ ] Real API success tests exist.
- [ ] Full default suite passes.

## T-007

- [ ] User schema supports phone-only residents.
- [ ] `users.id = auth.users.id`.
- [ ] Phone normalized as E.164.
- [ ] Auth FK is validated or honestly blocked.
- [ ] JWT JWKS verification works.
- [ ] HS256 Auth-server verification works.
- [ ] Auto mode behaves correctly.
- [ ] JWT verifier caching works.
- [ ] Resident auto-provision is concurrency-safe.
- [ ] Privileged self-promotion is impossible.
- [ ] Final RLS uses real identity.
- [ ] Migration downgrade/history is coherent.
- [ ] Private bucket setup exists.
- [ ] Signed upload expiry is accurate.
- [ ] Upload sessions prevent forged paths.
- [ ] Signed download is authorization-bound.
- [ ] Secret scanner is effective.
- [ ] Live Supabase validation runs when safe credentials are available.
- [ ] No credentials are exposed.

---

# 25. Final report format

At completion, report:

## A. Repository state

```text
initial commit/HEAD
initial git status
files inspected
unrelated changes preserved
```

## B. Dependencies

```text
dependency
version constraint
purpose
declaration file
pip check result
```

## C. JWT/Auth

```text
JWKS behavior
HS256 behavior
auto fallback behavior
cached verifier
phone normalization
resident auto-provision
privileged provisioning
test results
```

## D. Database/migrations

```text
migrations created or corrected
whether old migrations were rewritten and why
Auth FK validation status
orphan-profile status count only
RLS policy status
upgrade result
downgrade result on disposable database
Alembic head
```

## E. Storage

```text
bucket status
signed upload expiry
upload-session table
object verification method
signed download endpoint
metadata persistence
Storage tests
```

## F. API

```text
routes created/changed
authorization rules
transaction boundaries
error codes
API test results
```

## G. Live validation

For each item use:

```text
PASS
FAIL
BLOCKED — MISSING VARIABLES
BLOCKED — SAFE ENVIRONMENT NOT CONFIRMED
NOT RUN
```

Report:

```text
Supabase migration
Auth resident token
Auth coordinator token
RLS isolation
private bucket
signed upload
ticket with attachment
signed download
```

Never show secret values.

## H. Quality

```text
Ruff result
secret scan result
focused pytest results
full pytest result
CI changes
```

## I. Final status

Use only:

```text
T-006 COMPLETE
T-006 PARTIAL

T-007 COMPLETE
T-007 IMPLEMENTED — LIVE VALIDATION BLOCKED
T-007 PARTIAL
```

Do not claim `T-007 COMPLETE` without successful safe live evidence.

## J. Final Git state

```text
git status
files created
files modified
no commit performed
no push performed
```
