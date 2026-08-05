"""Static tests for the initial FixIt schema migration."""

import importlib.util
from collections.abc import Callable
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = PROJECT_ROOT / "alembic" / "versions"
EXPECTED_TABLES = [
    "users",
    "units",
    "tickets",
    "ticket_attachments",
    "ai_analysis_runs",
    "ticket_scoring_results",
]
ENUM_NAMES = {
    "role_enum",
    "ticket_status_enum",
    "category_enum",
    "severity_enum",
    "priority_enum",
}
EXPECTED_FOREIGN_KEYS = {
    ("tickets", "resident_id", "users.id", "RESTRICT"),
    ("tickets", "unit_id", "units.id", "RESTRICT"),
    ("ticket_attachments", "ticket_id", "tickets.id", "CASCADE"),
    ("ai_analysis_runs", "ticket_id", "tickets.id", "CASCADE"),
    ("ticket_scoring_results", "ticket_id", "tickets.id", "CASCADE"),
    ("ticket_scoring_results", "ai_analysis_run_id", "ai_analysis_runs.id", "SET NULL"),
}
EXPECTED_CHECK_CONSTRAINTS = {
    "ck_ai_analysis_runs_confidence_range",
    "ck_ticket_scoring_severity_range",
    "ck_ticket_scoring_red_flag_range",
    "ck_ticket_scoring_impact_range",
    "ck_ticket_scoring_density_range",
    "ck_ticket_scoring_age_range",
    "ck_ticket_scoring_total_range",
    "ck_ticket_scoring_total_equals_components",
}


def test_exactly_one_initial_fixit_migration_exists():
    assert len(_migration_files()) == 1


def test_initial_migration_defines_upgrade_and_downgrade():
    module = _load_initial_migration()

    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_initial_migration_creates_expected_tables_in_dependency_order():
    operations = _record_operations(_load_initial_migration().upgrade)
    create_tables = [operation["table"] for operation in operations if operation["op"] == "create_table"]

    assert create_tables == EXPECTED_TABLES


def test_initial_migration_drops_tables_in_reverse_dependency_order():
    operations = _record_operations(_load_initial_migration().downgrade)
    drop_tables = [operation["table"] for operation in operations if operation["op"] == "drop_table"]

    assert drop_tables == list(reversed(EXPECTED_TABLES))


def test_initial_migration_uses_stable_postgresql_enum_names():
    migration_text = _migration_files()[0].read_text(encoding="utf-8")

    for enum_name in ENUM_NAMES:
        assert f'name="{enum_name}"' in migration_text
    assert "postgresql.ENUM" in migration_text


def test_initial_migration_contains_expected_foreign_keys():
    operations = _record_operations(_load_initial_migration().upgrade)
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


def test_initial_migration_contains_expected_check_constraints():
    migration_text = _migration_files()[0].read_text(encoding="utf-8")

    for constraint_name in EXPECTED_CHECK_CONSTRAINTS:
        assert constraint_name in migration_text


def test_initial_migration_uses_postgresql_jsonb():
    migration_text = _migration_files()[0].read_text(encoding="utf-8")

    assert migration_text.count("postgresql.JSONB") == 3
    assert "red_flags" in migration_text
    assert "text_categories" in migration_text
    assert "scoring_reasons" in migration_text


def test_initial_migration_has_no_credentials_or_startup_side_effects():
    migration_text = _migration_files()[0].read_text(encoding="utf-8").lower()

    assert "postgresql://" not in migration_text
    assert "password" not in migration_text
    assert "create_all" not in migration_text
    assert "src.database" not in migration_text


def _migration_files() -> list[Path]:
    return sorted(VERSIONS_DIR.glob("*_create_initial_fixit_schema.py"))


def _load_initial_migration():
    migration_file = _migration_files()[0]
    spec = importlib.util.spec_from_file_location("initial_fixit_migration", migration_file)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Unable to load migration module from {migration_file}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record_operations(migration_function: Callable[[], None]) -> list[dict[str, object]]:
    operations: list[dict[str, object]] = []

    class Recorder:
        def get_bind(self):
            return None

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
    enum_names = ["role_enum", "ticket_status_enum", "category_enum", "severity_enum", "priority_enum"]
    original_enums = {enum_name: migration_globals[enum_name] for enum_name in enum_names}
    original_enum_methods = {
        enum_name: (enum_object.create, enum_object.drop) for enum_name, enum_object in original_enums.items()
    }

    migration_globals["op"] = Recorder()
    for enum_name, enum_object in original_enums.items():
        enum_object.create = lambda bind, checkfirst=False, name=enum_name: operations.append(
            {"op": "create_enum", "enum": name, "checkfirst": checkfirst}
        )
        enum_object.drop = lambda bind, checkfirst=False, name=enum_name: operations.append(
            {"op": "drop_enum", "enum": name, "checkfirst": checkfirst}
        )
    try:
        migration_function()
    finally:
        migration_globals["op"] = original_op
        for enum_name, enum_object in original_enums.items():
            enum_object.create, enum_object.drop = original_enum_methods[enum_name]

    return operations
