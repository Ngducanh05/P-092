"""Static tests for the Step 5 operational workflow migration."""

import importlib.util
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = PROJECT_ROOT / "alembic" / "versions"
INITIAL_REVISION = "b82bd2680082"
EXPECTED_TABLES = [
    "user_unit_memberships",
    "technician_profiles",
    "audit_logs",
    "notifications",
    "technician_skills",
    "ticket_assignments",
    "ticket_status_history",
]
EXPECTED_FOREIGN_KEYS = {
    ("user_unit_memberships", "user_id", "users.id", "RESTRICT"),
    ("user_unit_memberships", "unit_id", "units.id", "RESTRICT"),
    ("technician_profiles", "user_id", "users.id", "RESTRICT"),
    ("technician_skills", "technician_id", "technician_profiles.user_id", "RESTRICT"),
    ("ticket_assignments", "ticket_id", "tickets.id", "CASCADE"),
    ("ticket_assignments", "technician_id", "technician_profiles.user_id", "RESTRICT"),
    ("ticket_assignments", "assigned_by_user_id", "users.id", "RESTRICT"),
    ("ticket_status_history", "ticket_id", "tickets.id", "CASCADE"),
    ("ticket_status_history", "changed_by_user_id", "users.id", "SET NULL"),
    ("notifications", "recipient_user_id", "users.id", "RESTRICT"),
    ("notifications", "ticket_id", "tickets.id", "SET NULL"),
    ("audit_logs", "actor_user_id", "users.id", "SET NULL"),
}
EXPECTED_UNIQUE_CONSTRAINTS = {
    ("user_unit_memberships", ("user_id", "unit_id"), "uq_user_unit_memberships_user_unit"),
    ("technician_skills", ("technician_id", "category"), "uq_technician_skills_technician_category"),
}
EXPECTED_INDEXES = {
    ("user_unit_memberships", "ix_user_unit_memberships_user_active", ("user_id", "is_active"), False),
    ("user_unit_memberships", "ix_user_unit_memberships_unit_active", ("unit_id", "is_active"), False),
    ("technician_skills", "ix_technician_skills_category", ("category",), False),
    ("ticket_assignments", "ix_ticket_assignments_ticket_assigned_at", ("ticket_id", "assigned_at"), False),
    ("ticket_assignments", "ix_ticket_assignments_technician_active", ("technician_id", "is_active"), False),
    ("ticket_assignments", "uq_ticket_assignments_one_active_per_ticket", ("ticket_id",), True),
    ("ticket_status_history", "ix_ticket_status_history_ticket_created_at", ("ticket_id", "created_at"), False),
    ("notifications", "ix_notifications_recipient_unread_created_at", ("recipient_user_id", "is_read", "created_at"), False),
    ("notifications", "ix_notifications_ticket_id", ("ticket_id",), False),
    ("audit_logs", "ix_audit_logs_entity", ("entity_type", "entity_id"), False),
    ("audit_logs", "ix_audit_logs_actor_created_at", ("actor_user_id", "created_at"), False),
}


def test_exactly_one_operational_workflow_migration_exists():
    assert len(_migration_files()) == 1


def test_operational_migration_points_to_initial_revision():
    module = _load_operational_migration()

    assert module.down_revision == INITIAL_REVISION


def test_operational_migration_defines_upgrade_and_downgrade():
    module = _load_operational_migration()

    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_operational_migration_creates_expected_tables_in_dependency_order():
    operations = _record_operations(_load_operational_migration().upgrade)
    create_tables = [operation["table"] for operation in operations if operation["op"] == "create_table"]

    assert create_tables == EXPECTED_TABLES


def test_operational_migration_drops_tables_in_reverse_dependency_order():
    operations = _record_operations(_load_operational_migration().downgrade)
    drop_tables = [operation["table"] for operation in operations if operation["op"] == "drop_table"]

    assert drop_tables == list(reversed(EXPECTED_TABLES))


def test_operational_migration_reuses_existing_postgresql_enum_names():
    migration_text = _migration_files()[0].read_text(encoding="utf-8")

    assert 'name="category_enum"' in migration_text
    assert 'name="ticket_status_enum"' in migration_text
    assert "create_type=False" in migration_text
    assert ".create(" not in migration_text
    assert ".drop(" not in migration_text


def test_operational_migration_contains_expected_foreign_keys():
    operations = _record_operations(_load_operational_migration().upgrade)
    actual = set()

    for operation in operations:
        if operation["op"] != "create_table":
            continue
        for element in operation["elements"]:
            if element.__class__.__name__ != "ForeignKeyConstraint":
                continue
            constrained_column = element.column_keys[0]
            referred_column = element.elements[0]._colspec
            actual.add((operation["table"], constrained_column, referred_column, element.ondelete))

    assert EXPECTED_FOREIGN_KEYS <= actual


def test_operational_migration_contains_unique_constraints():
    operations = _record_operations(_load_operational_migration().upgrade)
    actual = set()

    for operation in operations:
        if operation["op"] != "create_table":
            continue
        for element in operation["elements"]:
            if element.__class__.__name__ != "UniqueConstraint":
                continue
            column_names = tuple(element.columns.keys()) or tuple(element._pending_colargs)
            actual.add((operation["table"], column_names, element.name))

    assert EXPECTED_UNIQUE_CONSTRAINTS <= actual


def test_operational_migration_contains_important_indexes():
    operations = _record_operations(_load_operational_migration().upgrade)
    actual = {
        (operation["table"], operation["index"], tuple(operation["columns"]), operation["unique"])
        for operation in operations
        if operation["op"] == "create_index"
    }

    assert EXPECTED_INDEXES <= actual


def test_operational_migration_contains_partial_active_assignment_index():
    operations = _record_operations(_load_operational_migration().upgrade)
    partial_index = next(
        operation
        for operation in operations
        if operation["op"] == "create_index" and operation["index"] == "uq_ticket_assignments_one_active_per_ticket"
    )

    assert str(partial_index["kwargs"]["postgresql_where"]) == "is_active"


def test_operational_migration_uses_postgresql_jsonb_for_audit_fields():
    migration_text = _migration_files()[0].read_text(encoding="utf-8")

    assert migration_text.count("postgresql.JSONB") == 3
    assert "old_values" in migration_text
    assert "new_values" in migration_text
    assert '"metadata"' in migration_text


def test_operational_migration_has_no_credentials_or_startup_side_effects():
    migration_text = _migration_files()[0].read_text(encoding="utf-8").lower()

    assert "postgresql://" not in migration_text
    assert "password" not in migration_text
    assert "access_token" not in migration_text
    assert "create_all" not in migration_text
    assert "src.database" not in migration_text
    assert "fastapi" not in migration_text


def _migration_files() -> list[Path]:
    return sorted(VERSIONS_DIR.glob("*_add_operational_workflow_tables.py"))


def _load_operational_migration():
    migration_file = _migration_files()[0]
    spec = importlib.util.spec_from_file_location("operational_workflow_migration", migration_file)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load migration module from {migration_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record_operations(migration_function: Callable[[], None]) -> list[dict[str, object]]:
    operations: list[dict[str, object]] = []

    class Recorder:
        def create_table(self, table_name: str, *elements, **kwargs):
            operations.append({"op": "create_table", "table": table_name, "elements": elements, "kwargs": kwargs})

        def create_index(self, index_name: str, table_name: str, columns: list[str], unique: bool = False, **kwargs):
            operations.append(
                {
                    "op": "create_index",
                    "index": index_name,
                    "table": table_name,
                    "columns": columns,
                    "unique": unique,
                    "kwargs": kwargs,
                }
            )

        def drop_table(self, table_name: str, **kwargs):
            operations.append({"op": "drop_table", "table": table_name, "kwargs": kwargs})

    migration_globals = migration_function.__globals__
    original_op = migration_globals["op"]
    migration_globals["op"] = Recorder()
    try:
        migration_function()
    finally:
        migration_globals["op"] = original_op

    return operations
