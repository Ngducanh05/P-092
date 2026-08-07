# FixIt — Source-of-Truth Alignment Audit

Audit date: 2026-08-06
Repository: `P-092`, branch `main`, HEAD `90701f9b57fbb8b9f4769cc827b99b85c0596a7a`
Interpreter: `C:\TEAM PROJECT\P-092\.venv\Scripts\python.exe`
Alembic head at audit time: `e5f6a7b8c9d0` (single head)
Baseline validation: `277 passed, 29 skipped, 1 warning`; Ruff passed; `pip check` passed; secret scan passed.

> **Baseline audit snapshot.** The evidence and `missing/conflicting` statuses below describe the repository before the Technician-restoration implementation. They are retained for traceability, not as current execution evidence. Current implementation status and validation results are recorded in `implementation-progress.md`.

## Source authority order

1. `dac_ta_tinh_nang_luong_nghiep_vu (1)(1).md` — actors, permissions, business rules, lifecycle, priority, flows. Cited below as **SPEC §n**.
2. `PRD (1)(1).md` — scope, personas, feature inventory, tech stack. Cited as **PRD §n**.
3. `brief (1)(1).md` — problem, solution intent, audience, value. Cited as **BRIEF**.
4. `WireFrame và UI Flow(1).html` — screen behaviour, actor presentation, field requirements. Cited as **WF <screen-id>** (e.g. `WF 2d`).
5. Existing repository code/docs — implementation evidence only, never product truth.

The four documents were read completely. The wireframe is a self-contained bundler
document; its screen content was extracted from the embedded `__bundler/template`
payload and read in full (screens `1a`–`1h`, `2a`–`2j`, `3a`–`3d`, flow diagrams
`4a`–`4c`).

## Reference tables recovered from the sources

### Priority and committed handling time (SPEC §0.1)

| Priority | Meaning | Committed handling time |
| --- | --- | --- |
| P3 | Life-threatening | 5 minutes |
| P2 | Serious disruption | 3 hours |
| P1 | Normal issue | 72 hours |
| P0 | **Not a danger level** — "cannot yet be determined" | Waits for BQL manual review |

### Category priority ceiling (SPEC §0.2)

| Category (source label) | Ceiling |
| --- | --- |
| Rò nước (water leak) | none |
| Chập điện (electrical short) | none |
| Thang máy (elevator) | none |
| An ninh nghiêm trọng / gây rối trật tự (serious security / public disorder) | none |
| Hỏng khóa / cửa (lock / door) | P2 |
| Điều hòa / thông gió (air conditioning / ventilation) | P2 |
| Mất điện cục bộ (local power outage) | P2 |
| Kết cấu — nứt tường, thấm dột (structural crack / seepage) | P2 |
| Hỏng đèn khu vực chung (common-area lighting) | P2 |
| Mùi hôi / vệ sinh (odor / sanitation) | P1 |
| Tiếng ồn / hàng xóm thông thường (normal noise / neighbour) | P1 |

### Permission matrix (SPEC §0.3)

| Action | Resident | BQL Coordinator | Technician |
| --- | --- | --- | --- |
| Submit new ticket | yes | no | no |
| View tickets | own unit only | all | assigned only |
| Review P0 ticket | no | yes | no |
| Update ticket status | no | yes | assigned only |
| View original images | own tickets only | yes | assigned only |

### Scoring pipeline (SPEC §4.1–4.5)

```
raw = Category base + (Location × Category) + Density + Severity
raw < 30 -> P1 ; 30 <= raw < 60 -> P2 ; raw >= 60 -> P3
final = MIN(threshold priority, category ceiling)
```

Red flag in text **or** image forces P3 and skips steps 4–6 entirely (SPEC §4.2).
Image/text category mismatch stops scoring and enters P0 manual review (SPEC §4.5).
Density applies only to water-leak and electrical-short categories, 3-day window,
same or immediately adjacent floor (SPEC §4.3). P1 batching groups same-category
tickets within 3 days and does **not** change score or priority (SPEC §4.4).

## Traceability matrix

Status legend: `aligned` / `partial` / `missing` / `conflicting`.

### A. Actors and identity

| # | Source requirement | Source file and section | Current implementation evidence | Status | Risk | Planned corrective action | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A1 | Three human actors: Resident, BQL Coordinator, Technician | SPEC §0.3, §1–§3; PRD §2 personas 1–3, §3 features 16–21; BRIEF "Target Audience"; WF §3, WF 4c | `CurrentActor.actor_type` is `Literal["resident","bql"]` in `src/api/dependencies/auth.py:42`; only `require_resident` / `require_bql` exist (`auth.py:104,110`); `src/api/dependencies/roles.py` re-exports two guards | conflicting | Critical — one third of the product has no runtime representation | Add `technician` actor type, `TechnicianProfile` model/repo, `require_technician` guard, technician route group | `tests/test_auth/*`, `/api/v1/auth/me` variant tests |
| A2 | Repository must not assert Technician is out of scope | SPEC §0.3, §3; PRD §3 | `README.md:10` — "There is no final runtime Technician actor"; `README.md:37` — "new Technician assignment transitions are not generated" | conflicting | Documentation encodes a decision that contradicts all four sources | Rewrite README actor/security sections; update `docs/backend/deferred-backend-work.md` | `git grep -i "no final runtime technician"` returns nothing |
| A3 | Technician authenticates with email + password | SPEC §3 (group heading), PRD §5 Auth row, WF 3a | No technician auth path exists | missing | Technician cannot log in | Resolve technician profile by verified email claim, mirroring BQL | Auth dependency unit tests |
| A4 | Technician account is created by BQL, not self-registered | WF 3a ("Tài khoản do BQL tạo"), SPEC §2.9 | `scripts/provision_bql_staff.py` provisions BQL only | missing | No trusted provisioning path | Add technician support to a backend-only provisioning script | `tests/test_scripts/*` |
| A5 | One Auth UUID must map to exactly one actor profile | Implied by SPEC §0.3 separation; existing security model | `prevent_actor_profile_conflict()` in `alembic/versions/d4e5f6a7b8c9_...py:83-111` covers only `residents` + `bql_staff` | partial | A technician UUID could also hold a resident profile → privilege confusion | Extend trigger function and add triggers to `technician_profiles` (three-way) | Static migration test asserting three-way exclusivity |
| A6 | Resident identity derived from verified phone token; no client-supplied role | SPEC §1.1; existing security model | `get_current_actor` derives from token (`auth.py:66-101`) — correct and must be preserved | aligned | — | Preserve; extend to three profiles | Existing auth tests must keep passing |
| A7 | Email-only users must not auto-become privileged | Security invariant; SPEC §1.1 restricts auto-provisioning to phone OTP | `auth.py:93-101` auto-provisions residents only when a valid E.164 phone claim exists | aligned | — | Preserve unchanged when adding technician resolution | Auth dependency test |
| A8 | No generic `public.users` / `role_enum` | Repository refactor already applied; not contradicted by sources | Dropped in `e5f6a7b8c9d0:255-257` | aligned | — | Do not restore | Static migration test |

### B. Priority, category, severity contracts

| # | Source requirement | Source file and section | Current implementation evidence | Status | Risk | Planned corrective action | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | Danger priorities are exactly P1, P2, P3 | SPEC §0.1, §4.1 step 5; BRIEF "Solution" bullet 4 | `Priority` enum includes `P4` (`src/models/enums.py:45`); `TicketRepository.list_bql_tickets` orders `Priority.P4` (`ticket_repository.py:162`) | conflicting | P4 is an invented priority with no source and no SLA | Remove `P4` from the active application contract; migration preflight counts persisted `p4` rows and fails safely if any exist | Enum unit test; migration preflight test |
| B2 | P0 is a manual-review state, not a danger priority | SPEC §0.1 (explicit parenthetical), §2.3, §4.5; WF 2b row `TK-1039` shows Priority column `P0` with score `—` | No P0 representation anywhere | missing | BQL cannot triage mismatched tickets at all | Introduce a separate `ManualReviewState` (`none`/`pending`/`waiting_resident`/`resolved`); never add P0 to `Priority` | Unit test asserting `P0` not in `Priority`; review-state transition tests |
| B3 | Full 11-category taxonomy with ceilings | SPEC §0.2 | `Category` enum has 8 generic values (`electricity`, `water`, `infrastructure`, `fire_safety`, …) that do not map 1:1 (`src/models/enums.py:20-27`) | conflicting | Ceilings cannot be applied; routing to technician skills is wrong | Replace with explicit source-derived machine codes + Vietnamese presentation mapping + ceiling table; migration preflight refuses ambiguous legacy values (`electricity`, `water`, `infrastructure`, `other`) | Category/ceiling unit tests; migration preflight test |
| B4 | Severity has exactly three levels: low / medium / high | SPEC §4.1 step 1 ("Thấp/Vừa/Cao"); WF 2d ("Độ nghiêm trọng: Cao") | `Severity` includes `CRITICAL` (`src/models/enums.py:36`) | conflicting | `critical` duplicates red-flag semantics as an additive score | Restrict active contract to three levels; danger handled by red-flag override; preflight counts persisted `critical` | Severity unit test; migration preflight test |
| B5 | Vietnamese labels must not be database keys | Engineering constraint; SPEC uses display labels only | Current enum values are already stable ASCII machine codes | aligned | — | Keep machine codes; add presentation layer | Presentation-mapping test |

### C. Scoring and AI pipeline

| # | Source requirement | Source file and section | Current implementation evidence | Status | Risk | Planned corrective action | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | Formula = Category base + (Location × Category) + Density + Severity | SPEC §4.1 step 4; BRIEF "Solution" bullet 3 | `ScoringResult` uses `severity_score + red_flag_score + impact_score + density_score + age_score` (`src/models/scoring_schemas.py:14-39`); DB check constraint enforces the same sum (`src/database/models/scoring_result.py:33-44`) | conflicting | The implemented formula is not the product formula; red flag is modelled as additive instead of an override | Replace active scoring contract with `category_base_score`, `location_category_score`, `density_score`, `severity_score`, `raw_total_score`, `priority_before_ceiling`, `priority_ceiling`, `final_priority`, `red_flag_override`, `manual_review_state`, `reasons` | Scoring unit tests including threshold boundaries |
| C2 | Red flag forces P3 and bypasses scoring | SPEC §4.2; PRD §4 last user story; BRIEF bullet 2 | `red_flag_score` is an additive 0–30 component | conflicting | A red-flag ticket could still score below P3 → safety-critical defect | Model red flag as control flow that short-circuits to P3 | Unit test: red flag ⇒ P3 regardless of other components |
| C3 | Category mismatch stops scoring, enters P0 | SPEC §4.5, §2.3; WF 2d | No mismatch logic; `AIAnalysisRun` stores `image_category` and `text_categories` but nothing compares them | missing | Misrouted work orders | Implement `compare_categories` node → manual review, no score written | Unit test: mismatch ⇒ no score, review pending |
| C4 | Thresholds `<30 → P1`, `30–59 → P2`, `≥60 → P3` | SPEC §4.1 step 5 | Not implemented | missing | — | Implement deterministic threshold function | Boundary tests at 29.999 / 30 / 59.999 / 60 |
| C5 | Ceiling applied after threshold conversion | SPEC §4.1 step 6, §0.2 | Not implemented | missing | Non-life-threatening categories could be inflated to P3 | Implement `MIN(threshold priority, ceiling)` | Ceiling unit tests per category |
| C6 | Density: water-leak/electrical-short only, 3 days, same or adjacent floor, unique source | SPEC §4.3, §1.1 (one unit = one account so a household counts once) | `density_score` column exists but no query logic | missing | Density can be gamed or mis-scoped | Implement repository query with category allow-list, 3-day window, floor adjacency, distinct-unit counting | Density unit tests incl. duplicate-household case |
| C7 | P1 batching: same category within 3 days, no score/priority effect | SPEC §4.4; WF 3b ("Nhóm gộp BG-14") | Not implemented | missing | — | Implement batch grouping that never mutates score/priority | Unit test asserting score/priority unchanged |
| C8 | Numeric Category-base and Location×Category matrices | SPEC "Ghi chú áp dụng" — deferred to pipeline technical document **section H**, which was **not supplied** | Not implemented | **blocked** | Inventing numbers would silently fabricate product behaviour | Implement a `ScoringRuleProvider` boundary; production config must fail loudly when matrices are absent; tests inject deterministic fixtures | Test asserting a clear failure when rules are unavailable |
| C9 | LangGraph pipeline classify → prioritize → route → notify | PRD §5 Agent Orchestration; SPEC §4.1 | `src/agents/graph.py` is starter `analyze → respond`; `src/agents/nodes/example_node.py` and `tools/example_tool.py` are generic boilerplate | conflicting | Placeholder code could be mistaken for the FixIt pipeline | Build the FixIt domain graph; keep starter assets isolated behind the existing `enable_legacy_agent_routes` development flag | Graph node/route tests |
| C10 | Only structured, auditable AI output persisted | BRIEF "Core Value" (auditable explicit layer); privacy constraint | `AIAnalysisRun` persists structured fields only — no chain-of-thought | aligned | — | Preserve; extend with `red_flag_text`, `red_flag_signal`, `image_readable`, `model_version` | Model metadata test |
| C11 | Multimodal LLM calls run asynchronously to avoid blocking | PRD §5 Task Queue (Celery + Redis); SPEC §1.2 step 5 "Đang phân tích…" | No Celery/Redis; no task boundary | missing | — | Define a task-dispatch adapter with an eager/fake implementation for tests; enqueue only after commit | Adapter unit tests |

### D. Resident flows

| # | Source requirement | Source file and section | Current implementation evidence | Status | Risk | Planned corrective action | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | First login links a BQL-issued `unit_id`; resident cannot choose freely | SPEC §1.1 steps 2–4; WF 1a step 3/3 | No link endpoint; memberships must be pre-seeded out of band | missing | Residents cannot onboard | Add `POST /api/v1/units/link` deriving resident identity from token | API test |
| D2 | One `unit_id` binds to exactly one primary account | SPEC §1.1 "Quy tắc nghiệp vụ quan trọng"; WF 1a error state | Only `uq_resident_unit_memberships_resident_unit` on `(resident_id, unit_id)` (`d4e5f6a7b8c9:251-255`) — two residents may both hold the same unit | conflicting | Density inflation — the exact abuse the rule exists to prevent | Add partial unique index on `unit_id WHERE is_active` plus a migration preflight counting existing duplicates | Static migration test + duplicate-link API test |
| D3 | Location always required; structured floor + location type | SPEC §1.2 steps 1, 3; WF 1c (two required dropdowns) | `location_description` is optional free text (`src/models/api/tickets.py:73`) and nullable in DB (`ticket.py:60`) | conflicting | Location×Category scoring is impossible without structured location | Require location on create; add structured floor + location-type fields | Create-ticket validation tests |
| D4 | At least one of text or image; either alone is valid | SPEC §1.2 step 3; WF 1c footnote | `title` (min 3) and `description` (min 10) are both mandatory (`tickets.py:57-68`); image-only submission is impossible | conflicting | A core submission mode is unsupported | Make text optional, require `text OR image`, derive/omit title | Text-only, image-only, and neither-provided tests |
| D5 | Unreadable image without sufficient text ⇒ no official ticket, ask to retry | SPEC §1.2 "Trường hợp đặc biệt"; WF 1d ("Chưa tạo ticket") | No such path; every create produces an official ticket | conflicting | Unusable tickets enter the BQL queue | Introduce an explicit draft/submission lifecycle so an unreadable submission never becomes an official ticket; never silently delete records | Unreadable-image unit test |
| D6 | Cancel allowed only while status is New | SPEC §1.6; WF 1b ("có thể huỷ"), WF 1e | No cancel endpoint | missing | — | `POST /api/v1/tickets/{id}/cancel` guarded by a central transition table | Transition unit + API tests |
| D7 | Resident can add information/images when BQL requests it | SPEC §2.3 option 2; WF 1f ("Bổ sung ngay") | Missing | missing | P0 review loop cannot complete | `POST /api/v1/tickets/{id}/additional-information` | API test |
| D8 | Friendly category label, urgency wording, expected handling time | SPEC §1.4; WF 1e | `TicketResponse` returns raw `priority`, and `estimated_resolution_text` is hardcoded `"Đang phân tích"` (`tickets.py:151-154`) | conflicting | Raw P codes leak to residents, explicitly forbidden | Add a resident-specific projection with friendly labels and SLA text derived from SPEC §0.1 | Response-projection leak tests |
| D9 | Resident must not see "SLA", raw P codes, or score breakdown | SPEC §1.4; WF 1e annotation | `TicketResponse.priority` is returned to residents (`tickets.py:142`, used by `/tickets/my` and `/tickets/{id}`) | conflicting | Direct contract violation | Separate Resident / BQL / Technician response models | Explicit "no raw P code" assertions |
| D10 | Ticket history filterable by time and category | SPEC §1.7; WF 1h | `/tickets/my` supports status, category, and created-at range filters (`src/api/routes/tickets.py:112-131`) | aligned | — | Preserve; re-point to the resident projection | Existing route tests |
| D11 | Resident receives notifications on progress changes | SPEC §1.5; WF 1f | `notifications` table exists; no service, no endpoint | missing | — | Notification service + inbox/read endpoints | Idempotency and inbox tests |
| D12 | Resident rating after completion | WF 1g referenced in flow `4a`; SPEC §2.8 references "mục 1.6" for rating data | **Screen `1g` has no definition in the wireframe**, and SPEC §1.6 is "Hủy ticket" (cancel), not rating | **conflicting / unresolved** | Implementing an invented rating model would fabricate product behaviour | Do **not** implement rating. Recorded as an open gap; see "Unresolved source conflicts" below | n/a — documented as blocked |

### E. BQL Coordinator flows

| # | Source requirement | Source file and section | Current implementation evidence | Status | Risk | Planned corrective action | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E1 | See all tickets, filter by category/priority/status/time | SPEC §2.1; WF 2b | `GET /api/v1/bql/tickets` implements all four filters (`src/api/routes/bql.py:31-51`) | aligned | — | Re-point to a BQL projection | Route test |
| E2 | Default sort by Priority **descending** (P3 first) | SPEC §2.1; WF 2b ("Sắp xếp: Priority ↓", P3 rows first) | `list_bql_tickets` orders `P1→1, P2→2, P3→3` ascending, i.e. **P1 first** (`src/repositories/ticket_repository.py:158-168`) | conflicting | The most urgent tickets sort last — an operational safety defect | Invert to P3-first ordering | Ordering unit test |
| E3 | Detail shows original text/image, location, category, priority, **total score** | SPEC §2.2; WF 2c | No BQL detail endpoint; the shared `/tickets/{id}` returns no score at all | missing | — | `GET /api/v1/bql/tickets/{id}` with total score | Projection test |
| E4 | Detail must **not** show component breakdown | SPEC §2.2 (explicit); WF 2c annotation | n/a | missing | — | BQL projection exposes `total_score` only | Leak test asserting no component fields |
| E5 | Review P0: choose image category, text category, or another category | SPEC §2.3; WF 2d | Missing | missing | Mismatched tickets are permanently stuck | `POST /api/v1/bql/tickets/{id}/manual-review/resolve` → recompute score with the approved category | Recalculation test |
| E6 | Request more information from resident | SPEC §2.3 option 2; WF 2d | Missing | missing | — | `POST /api/v1/bql/tickets/{id}/request-information` | API test |
| E7 | Override category/priority with mandatory reason | SPEC §2.4; WF 2e ("LÝ DO SỬA ĐỔI*") | Missing | missing | — | `POST /api/v1/bql/tickets/{id}/override` requiring a non-empty reason | Reason-required test |
| E8 | Every review/override audited: actor, time, old→new, reason | SPEC §2.4, §2.10; WF 2j | `audit_logs` table exists with `actor_auth_user_id`, `old_values`, `new_values`; no writer | partial | Unauditable decisions | Write append-only audit rows in the same transaction as the decision | Audit-write test |
| E9 | Assign ticket to a suitable active technician by skill and workload | SPEC §2.5; WF 2f (filter by skill + busy/free, "Khớp"/"Bận") | `ticket_assignments` was dropped by `e5f6a7b8c9d0:252` | missing | Core routing capability absent | Recreate assignment tables in a new migration; add assignment endpoint and skill/workload matching | Assignment tests |
| E10 | Manage technician roster and skills | SPEC §2.9; WF 2i | Missing | missing | — | `GET/POST/PATCH /api/v1/bql/technicians` (profile only, never passwords) | API tests |
| E11 | View append-only audit log | SPEC §2.10; WF 2j ("Bản ghi chỉ đọc · không xoá được") | No endpoint | missing | — | `GET /api/v1/bql/audit-logs` | API test |
| E12 | Export periodic reports/statistics | SPEC §2.8; WF 2h | Missing | missing | — | `GET /api/v1/bql/reports` (counts by category/priority, actual vs committed time) | Report aggregation test |
| E13 | BQL API must never accept or store passwords | Security invariant; WF 2i form has no password field | n/a | aligned | — | Keep Auth provisioning in the trusted admin script, separate from profile editing | Test asserting no password field in technician schemas |

### F. Technician flows

| # | Source requirement | Source file and section | Current implementation evidence | Status | Risk | Planned corrective action | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F1 | See only tickets assigned to self, sorted by priority | SPEC §3.1; WF 3b ("Chỉ hiện ticket được gán cho tôi") | Nothing exists | missing | — | `GET /api/v1/technician/assignments` scoped by authenticated technician | Cross-technician isolation test |
| F2 | Detail shows text, image, location, category — **no score** | SPEC §3.2; WF 3c ("không hiện điểm số") | Nothing | missing | — | Technician projection without any score field | Leak test |
| F3 | Accept assignment | SPEC §3.3; WF 3d ("Đã nhận việc") | Nothing | missing | — | `POST .../accept` | Transition test |
| F4 | Update status: accepted → in progress → completed, or unable-to-handle | SPEC §3.3; WF 3d | Nothing | missing | — | `POST .../status` via the central transition table | Transition tests |
| F5 | Unable-to-handle requires a reason | SPEC §3.3 ("kèm bắt buộc nhập lý do"); WF 3d | Nothing | missing | — | Validation requiring a non-empty reason | Reason-required test |
| F6 | Work notes (cause, parts replaced) | SPEC §3.4; WF 3d | Nothing | missing | — | Work-log persistence | Persistence test |
| F7 | Completion photo required when completing | SPEC §3.5; WF 3d ("Bắt buộc khi Hoàn thành") | Nothing | missing | — | `POST .../completion` requiring a completion attachment | Evidence-required test |
| F8 | Notified when assigned | SPEC §3.6, §2.5; WF 2f annotation | Nothing | missing | — | Notification emitted in the assignment transaction | Notification test |
| F9 | Technician must never reach unassigned tickets | SPEC §0.3; WF 3b | No RLS policy or guard exists | missing | Confidentiality breach | Backend scoping **and** assignment-scoped RLS policies | RLS static test + API 404 test |
| F10 | Technician roster fields: name, phone, skills, active status, open workload | SPEC §2.9; WF 2i table, WF 2f | Nothing | missing | — | `technician_profiles` (id = Auth UUID, email, phone, full name, active/available) + `technician_skills` | Model metadata test |

### G. Cross-cutting: persistence, security, state, presentation

| # | Source requirement | Source file and section | Current implementation evidence | Status | Risk | Planned corrective action | Verification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| G1 | Ticket lifecycle covering new → analyzing → manual review → waiting resident → approved → assigned → accepted → in progress → completed / unable / cancelled | SPEC §1.3, §2.3, §2.5, §3.3; WF 1b, 2b, 3d | `TicketStatus` has 8 values (`new`, `analyzing`, `waiting_assignment`, `assigned`, `in_progress`, `resolved`, `closed`, `rejected`) — no `cancelled`, no `unable_to_handle`, no waiting-resident state (`src/models/enums.py:4-14`) | partial | Cancellation and unable-to-handle cannot be represented | Extend the lifecycle; keep historical PostgreSQL enum values for migration safety; centralise transitions | Transition table tests |
| G2 | Status changes are append-only history | SPEC §2.10; WF 1e timeline | `ticket_status_history` exists; only the creation row is written (`ticket_repository.py:35-45`) | partial | — | Write history on every transition | History tests |
| G3 | Status changes generate notifications | SPEC §1.5, §4.6; WF 1f | No generation | missing | — | Emit notifications transactionally, idempotently | Idempotency test |
| G4 | RLS as defense in depth, forced, PUBLIC revoked | Existing security model, not contradicted by sources | `e5f6a7b8c9d0:445-461` enables + forces RLS and revokes PUBLIC on 12 tables | aligned | — | Extend the same treatment to new technician/workflow tables | Static RLS test |
| G5 | Backend-only tables deny client access | Existing security model | Deny-all policies on upload sessions, AI runs, scoring results, audit logs (`e5f6a7b8c9d0:415-441`) | aligned | — | Add the same for new internal tables (review/override/outbox) | Static RLS test |
| G6 | Private storage paths never returned; signed URLs short-lived | Existing security model | `TicketAttachmentResponse` exposes only a download endpoint (`src/models/api/tickets.py:107`); TTL is bounded 30–3600 s (`src/config.py:38`) | aligned | — | Preserve for completion attachments too | Existing storage tests |
| G7 | Shared auth identity columns reused for cross-actor records | Engineering direction | `notifications.recipient_auth_user_id`, `ticket_status_history.changed_by_auth_user_id`, `audit_logs.actor_auth_user_id` already exist | aligned | — | Reuse for technician events | Model metadata test |
| G8 | Stable error envelope | Existing API contract | `DomainError` + handler in `src/main.py:96-108` | aligned | — | Add codes for invalid transition, assignment conflict, manual review, missing info, actor mismatch, unavailable scoring rules | Error-contract tests |
| G9 | Next.js frontend | PRD §5 Frontend | Backend-only repository; no frontend workspace | missing | — | Do **not** create a frontend inside the Python backend. Record as a separate deliverable; ensure OpenAPI covers every wireframe screen | Documented in deferred work |
| G10 | Celery + Redis | PRD §5 Task Queue | Absent from `requirements.in`, `docker-compose.yml`, `src/config.py` | missing | — | Introduce a task-dispatch port with an eager adapter; add Celery/Redis only if wired end-to-end | Adapter tests |

## Unresolved source conflicts

### CONFLICT-1 — Resident rating feature (screen `1g`)

- **Evidence.** Wireframe flow `4a` and `4c` both route to a screen labelled `1g Đánh giá`,
  and WF 1b/1f contain "Đánh giá xử lý →" and "mời đánh giá" affordances.
  SPEC §2.8 requires reports to include "điểm đánh giá trung bình từ cư dân (dữ liệu từ mục 1.6)".
- **Contradiction.** The wireframe contains **no screen definition for `1g`**, and SPEC §1.6
  is "Hủy ticket" (cancel a ticket), not rating. The cross-reference in SPEC §2.8 points at
  a section that does not describe ratings. PRD §3 lists no rating feature for the resident group.
- **Resolution under the authority order.** The detailed specification is the primary authority
  and does not define a rating feature, its scale, its timing, or its storage.
- **Safest implementation boundary.** Do not implement resident ratings. Do not add a
  rating column, endpoint, or report metric. The report endpoint will expose only the metrics
  the sources define unambiguously (ticket counts by category and priority, actual versus
  committed handling time per SPEC §0.1).
- **Blocking?** No. This does not block any other work. Clarification is desirable but not required.

### CONFLICT-2 — Cluster screen `2g` (Cụm ticket)

- **Evidence.** WF 2c/2d/2h/2i/2j sidebars list "Cụm ticket"; WF 2c shows "Thuộc cụm — Cụm lan rộng
  #C-07 · 3 ticket"; WF 3b/3c show cluster and batch references (`#C-07`, `BG-14`).
  Flow `4b` routes Dashboard → "Cụm ticket 2g" → "Gán KTV 2f" ("gán 1 lượt").
- **Contradiction.** No screen `2g` is defined in the wireframe, and SPEC §4.3/§4.4 describe
  clustering and batching only as **scoring/scheduling** concepts, never as a bulk-assignment UI.
- **Resolution.** Implement the SPEC §4.3 density case and §4.4 batching group as
  persisted domain concepts and expose their identifiers on BQL and Technician projections
  (which the wireframe clearly requires). Do **not** invent a bulk-assign-a-whole-cluster API,
  since neither its rules nor its audit semantics are specified.
- **Blocking?** No.

### CONFLICT-3 — Assignment status transition wording

- **Evidence.** SPEC §2.5 step 3 says assignment moves the ticket `Đã duyệt` → `Đang xử lý`.
  SPEC §3.3 says the technician moves `Đã nhận việc` → `Đang xử lý` → `Hoàn thành`.
  WF 3b shows an assigned ticket in state "Mới nhận" before "Đã nhận việc".
- **Contradiction.** SPEC §2.5 implies assignment alone sets *in progress*, while SPEC §3.3 and
  WF 3b require an intermediate assigned/accepted step owned by the technician.
- **Resolution under the authority order.** Both statements are in the primary document, so the
  hierarchy does not settle it. The safest boundary is the more conservative reading: assignment
  sets an `assigned` state, and only the technician's explicit acceptance produces `accepted`,
  then `in_progress`. This preserves SPEC §3.3's technician-owned transitions and WF 3b's
  "Mới nhận" state, and loses nothing from SPEC §2.5 except an imprecise label.
- **Blocking?** No — it changes no persisted data contract beyond the lifecycle enum, which is
  additive.

### BLOCKER-1 — Missing numeric scoring matrices (pipeline document, section H)

- **Evidence.** SPEC "Ghi chú áp dụng" explicitly defers the numeric values for
  Category base, the Location × Category matrix, Density, and the conversion thresholds
  to a separate technical pipeline document, **section H**, which was not supplied.
- **Impact.** The thresholds (`<30`, `30–59`, `≥60`) *are* stated in SPEC §4.1 step 5 and can be
  implemented. Red-flag override, category-mismatch behaviour, ceilings, density scope, and
  batching are all fully specified and can be implemented. Only the **Category base** and
  **Location × Category** numeric tables are missing.
- **Planned boundary from the baseline audit.** A future `ScoringRuleProvider` port should accept approved
  matrices; production must fail clearly when they are absent rather than substituting invented values.
- **Blocking?** Partially — it blocks only end-to-end numeric score production in production
  configuration. Every other rule is implementable and testable.

## Migration constraint recorded

Migrations through `e5f6a7b8c9d0` are already applied to the development Supabase database.
`d4e5f6a7b8c9` and `e5f6a7b8c9d0` must not be edited. All corrective schema work must be new
revisions whose first `down_revision` is `e5f6a7b8c9d0`. Historical intent for the technician
tables is recoverable from `alembic/versions/c7a3f2d9e105_add_operational_workflow_tables.py:77-175`,
but its foreign keys targeted the removed `public.users` table and must not be reused as-is.
