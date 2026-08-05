# Data Dictionary

Sensitivity: PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED, SECRET - must not be stored.

## `users`

| Column | Type | Nullable | Default | PK | FK | Unique | Index | Sensitive classification | Business meaning | Allowed writer | Retention notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `id` | UUID | No | generated | Yes | No | Yes | PK | INTERNAL | User identifier | Backend/service | Clarification required |
| `email` | String | No | None | No | No | Yes | Yes | CONFIDENTIAL | Contact/login email | Backend/service | Clarification required |
| `full_name` | String | No | None | No | No | No | No | CONFIDENTIAL | Display name | Backend/service | Clarification required |
| `role` | `role_enum` | No | None | No | No | No | No | INTERNAL | Business role | Backend/service | Clarification required |
| `is_active` | Boolean | No | true | No | No | No | No | INTERNAL | Account active flag | Backend/service | Deactivation preferred |
| `created_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Creation time | Database | Clarification required |
| `updated_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Update time | Database | Clarification required |

## `units`

| Column | Type | Nullable | Default | PK | FK | Unique | Index | Sensitive classification | Business meaning | Allowed writer | Retention notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `id` | UUID | No | generated | Yes | No | Yes | PK | INTERNAL | Unit identifier | Backend/service | Clarification required |
| `building_code` | String | No | None | No | No | No | No | CONFIDENTIAL | Building identifier | Backend/service | Deactivation preferred |
| `floor` | String | No | None | No | No | No | No | CONFIDENTIAL | Floor | Backend/service | Clarification required |
| `unit_number` | String | No | None | No | No | No | No | CONFIDENTIAL | Apartment number | Backend/service | Clarification required |
| `is_active` | Boolean | No | true | No | No | No | No | INTERNAL | Unit active flag | Backend/service | Deactivation preferred |
| `created_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Creation time | Database | Clarification required |

## `user_unit_memberships`

| Column | Type | Nullable | Default | PK | FK | Unique | Index | Sensitive classification | Business meaning | Allowed writer | Retention notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `id` | UUID | No | generated | Yes | No | Yes | PK | INTERNAL | Membership id | Backend/service | Clarification required |
| `user_id` | UUID | No | None | No | `users.id` | With `unit_id` | Yes | CONFIDENTIAL | Resident user | Backend/service | Preserve history |
| `unit_id` | UUID | No | None | No | `units.id` | With `user_id` | Yes | CONFIDENTIAL | Linked unit | Backend/service | Preserve history |
| `is_active` | Boolean | No | true | No | No | No | Yes | INTERNAL | Active ownership flag | Backend/service | Use unlink fields |
| `linked_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Link time | Database/backend | Clarification required |
| `unlinked_at` | Timestamp TZ | Yes | None | No | No | No | No | INTERNAL | Unlink time | Backend/service | Clarification required |
| `created_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Creation time | Database | Clarification required |
| `updated_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Update time | Database | Clarification required |

## `technician_profiles`

| Column | Type | Nullable | Default | PK | FK | Unique | Index | Sensitive classification | Business meaning | Allowed writer | Retention notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `user_id` | UUID | No | None | Yes | `users.id` | Yes | PK | INTERNAL | Technician user | Backend/service | Deactivation preferred |
| `is_active` | Boolean | No | true | No | No | No | No | INTERNAL | Technician active state | Backend/service | Clarification required |
| `is_available` | Boolean | No | true | No | No | No | No | INTERNAL | Availability | Backend/service | Clarification required |
| `created_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Creation time | Database | Clarification required |
| `updated_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Update time | Database | Clarification required |

## `technician_skills`

| Column | Type | Nullable | Default | PK | FK | Unique | Index | Sensitive classification | Business meaning | Allowed writer | Retention notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `id` | UUID | No | generated | Yes | No | Yes | PK | INTERNAL | Skill row | Backend/service | Clarification required |
| `technician_id` | UUID | No | None | No | `technician_profiles.user_id` | With `category` | No | INTERNAL | Technician | Backend/service | Clarification required |
| `category` | `category_enum` | No | None | No | No | With `technician_id` | Yes | INTERNAL | Supported category | Backend/service | Clarification required |
| `created_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Creation time | Database | Clarification required |

## `tickets`

| Column | Type | Nullable | Default | PK | FK | Unique | Index | Sensitive classification | Business meaning | Allowed writer | Retention notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `id` | UUID | No | generated | Yes | No | Yes | PK | INTERNAL | Ticket id | Backend/service | Preserve |
| `resident_id` | UUID | No | None | No | `users.id` | No | Yes | CONFIDENTIAL | Reporting resident | Backend/service | Preserve |
| `unit_id` | UUID | No | None | No | `units.id` | No | Yes | CONFIDENTIAL | Affected unit | Backend/service | Preserve |
| `title` | String | No | None | No | No | No | No | CONFIDENTIAL | Issue title | Backend/service | Clarification required |
| `description` | Text | No | None | No | No | No | No | CONFIDENTIAL | Issue details | Backend/service | Clarification required |
| `status` | `ticket_status_enum` | No | new | No | No | No | No | INTERNAL | Current state | Backend/service | Preserve |
| `category` | `category_enum` | Yes | None | No | No | No | No | INTERNAL | Issue category | Backend/service | Preserve |
| `severity` | `severity_enum` | Yes | None | No | No | No | No | INTERNAL | AI/coordinator severity | Backend/service | Restricted exposure |
| `priority` | `priority_enum` | Yes | None | No | No | No | No | INTERNAL | Priority label | Backend/service | Public exposure requires approval |
| `location_description` | String | Yes | None | No | No | No | No | CONFIDENTIAL | Location details | Backend/service | Clarification required |
| `created_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Creation time | Database | Preserve |
| `updated_at` | Timestamp TZ | No | now | No | No | No | No | INTERNAL | Update time | Database | Preserve |
| `resolved_at` | Timestamp TZ | Yes | None | No | No | No | No | INTERNAL | Resolution time | Backend/service | Preserve |

## Remaining Operational Tables

| Table | Key sensitive columns | Allowed writer | Retention notes |
|---|---|---|---|
| `ticket_attachments` | `file_url` CONFIDENTIAL, `mime_type` INTERNAL, `file_size` INTERNAL | Backend/service | Private storage lifecycle requires clarification |
| `ticket_assignments` | `technician_id` INTERNAL, `assigned_by_user_id` INTERNAL, timestamps INTERNAL | Backend/service | Append history; no client mutation |
| `ticket_status_history` | `change_reason` CONFIDENTIAL, actor INTERNAL | Backend/service | Append-only |
| `ai_analysis_runs` | `summary`, `red_flags`, `confidence`, `model_name` RESTRICTED | System/service | Retention requires clarification |
| `ticket_scoring_results` | all scores and `scoring_reasons` RESTRICTED | System/service | Retention requires clarification |
| `notifications` | `title`, `body` CONFIDENTIAL | Backend/service | Retention requires product decision |
| `audit_logs` | `old_values`, `new_values`, `metadata` RESTRICTED | Service only | Append-only; retention requires legal/business decision |

No table may store SECRET values such as passwords, OTPs, JWTs, access tokens, API keys, service-role keys, authorization headers, or raw chain-of-thought.

