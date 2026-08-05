# Prompt triển khai FixIt Agent — Bước 1: Enums và Pydantic Schemas

You are working inside the existing repository `P-092`.

Implement **Step 1: FixIt Agent shared enums and Pydantic schemas**.


## Virtual environment requirement

All implementation and validation work must run inside the repository's Python virtual environment:

```text
P-092/.venv
```

Before editing any code, verify the active Python interpreter:

```powershell
python -c "import sys; print(sys.executable)"
```

The output must point to the repository virtual environment, for example:

```text
C:\TEAM PROJECT\P-092\.venv\Scripts\python.exe
```

If the virtual environment is not active, activate it in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

Then verify the interpreter again:

```powershell
python -c "import sys; print(sys.executable)"
```

Rules:

- Do not install dependencies globally.
- Do not use the system Python for this task.
- Use the currently activated `.venv` for every Python-related command.
- Prefer `python -m pip`, `python -m pytest`, and `python -m ruff`.
- If dependencies are missing, install them inside `.venv` with:

```powershell
python -m pip install -r requirements.txt
```

- Do not delete or recreate `.venv` unless the existing environment is unusable.
- In the final report, include the exact Python interpreter path used during implementation and validation.


Before editing anything, inspect the current repository tree and read these existing files:

- `src/models/__init__.py`
- `src/models/schemas.py`
- `src/api/routes.py`
- `src/main.py`
- `requirements.txt`
- `ruff.toml`

## Architecture constraint

The project already uses this structure:

```text
src/
├── agents/
├── api/
├── models/
├── services/
├── config.py
└── main.py
```

You must follow the existing `src/` structure.

Do **not** create a new `app/` directory.

Do **not** create Database, repository, API, migration, or scoring-service code in this task.

Do not modify AI logging files, hooks, scripts, Docker files, documentation, or unrelated modules.

## Existing compatibility requirement

`src/models/schemas.py` currently contains the existing:

- `ChatRequest`
- `ChatResponse`

Keep that file and its current classes unchanged so the existing API continues working.

## Files to create

Create:

```text
src/models/enums.py
src/models/agent_schemas.py
src/models/scoring_schemas.py
```

Update:

```text
src/models/__init__.py
```

---

## 1. Create `src/models/enums.py`

Define the following string enums using:

```python
class Example(str, Enum):
    ...
```

### Role

```python
RESIDENT = "resident"
COORDINATOR = "coordinator"
TECHNICIAN = "technician"
ADMIN = "admin"
```

### TicketStatus

```python
NEW = "new"
ANALYZING = "analyzing"
WAITING_ASSIGNMENT = "waiting_assignment"
ASSIGNED = "assigned"
IN_PROGRESS = "in_progress"
RESOLVED = "resolved"
CLOSED = "closed"
REJECTED = "rejected"
```

### Category

```python
ELECTRICITY = "electricity"
WATER = "water"
ELEVATOR = "elevator"
SECURITY = "security"
SANITATION = "sanitation"
FIRE_SAFETY = "fire_safety"
INFRASTRUCTURE = "infrastructure"
OTHER = "other"
```

### Severity

```python
LOW = "low"
MEDIUM = "medium"
HIGH = "high"
CRITICAL = "critical"
```

### Priority

```python
P1 = "p1"
P2 = "p2"
P3 = "p3"
P4 = "p4"
```

Add concise docstrings explaining the purpose of each enum.

---

## 2. Create `src/models/agent_schemas.py`

Use Pydantic v2.

Import:

```python
from pydantic import BaseModel, ConfigDict, Field
from src.models.enums import Category, Severity
```

Create:

```python
class AgentResult(BaseModel):
```

Use this model configuration:

```python
model_config = ConfigDict(
    extra="forbid",
    str_strip_whitespace=True,
)
```

Fields:

```python
category: Category
severity: Severity
summary: str
red_flags: list[str]
text_categories: list[Category]
image_category: Category | None
confidence: float
recommended_department: str | None
```

Validation requirements:

- `summary`: required, minimum 5 characters, maximum 500 characters.
- `red_flags`: default empty list using `default_factory=list`.
- `text_categories`: default empty list using `default_factory=list`.
- `image_category`: default `None`.
- `confidence`: required, from `0.0` to `1.0`, inclusive.
- `recommended_department`: default `None`, maximum 100 characters.
- Do not use mutable list literals as defaults.
- Add useful `Field` descriptions for Swagger/OpenAPI and future integration.

The model must reject unknown fields because `extra="forbid"` is required.

---

## 3. Create `src/models/scoring_schemas.py`

Use Pydantic v2.

Import:

```python
from pydantic import BaseModel, ConfigDict, Field, model_validator
from src.models.enums import Priority
```

Create:

```python
class ScoringResult(BaseModel):
```

Use:

```python
model_config = ConfigDict(
    extra="forbid",
    str_strip_whitespace=True,
)
```

Fields and allowed ranges:

```python
severity_score: float   # 0 to 40
red_flag_score: float   # 0 to 30
impact_score: float     # 0 to 15
density_score: float    # 0 to 10
age_score: float        # 0 to 5
total_score: float      # 0 to 100
priority: Priority
scoring_reasons: list[str]
```

Requirements:

- `scoring_reasons` must use `default_factory=list`.
- Add a Pydantic v2 `model_validator(mode="after")`.
- The validator must ensure that `total_score` equals:

```text
severity_score
+ red_flag_score
+ impact_score
+ density_score
+ age_score
```

- Use a small floating-point tolerance instead of direct float equality.
- Raise a clear `ValueError` when the total is inconsistent.
- Do not automatically recalculate or silently replace `total_score`; invalid input must be rejected.

Do not validate the `Priority` threshold mapping yet. That logic belongs to the future `scoring_service.py`, not this schema task.

---

## 4. Update `src/models/__init__.py`

Export the new public contracts:

```python
AgentResult
ScoringResult
Role
TicketStatus
Category
Severity
Priority
```

Use explicit imports and define `__all__`.

Do not remove or alter `src/models/schemas.py`.

---

## 5. Code quality requirements

- Python 3.11 compatible.
- Pydantic v2 compatible.
- Full type hints.
- Clean imports.
- Ruff-compatible formatting.
- Maximum line length must follow the repository's `ruff.toml`.
- No unnecessary abstraction.
- No duplicate enum definitions in different files.
- No business logic inside schemas except validation of schema consistency.

---

## 6. Validation

After implementation, run:

```powershell
python -c "from src.models import AgentResult, ScoringResult, Role, TicketStatus, Category, Severity, Priority; print('FixIt contracts import successfully')"
```

Run Ruff:

```powershell
python -m ruff check src/models
```

Run the existing test suite:

```powershell
python -m pytest tests -v
```

Also perform a small manual validation or temporary Python command confirming:

1. A valid `AgentResult` can be created.
2. `severity="urgent"` is rejected.
3. `confidence=1.5` is rejected.
4. An unknown field in `AgentResult` is rejected.
5. A valid `ScoringResult` is accepted.
6. A `ScoringResult` whose `total_score` does not equal the component sum is rejected.

Do not leave temporary validation files in the repository.

## Final response

After finishing, report:

1. Files created.
2. Files modified.
3. Important validation rules implemented.
4. Exact commands executed.
5. Ruff and pytest results.
6. Any existing unrelated failures found.

Do not commit or push changes unless explicitly requested.
