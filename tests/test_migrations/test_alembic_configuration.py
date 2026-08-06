"""Alembic configuration tests."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.config import Config

import src.database.models  # noqa: F401
from src.config import Settings
from src.database.base import Base
from src.database.migration_safety import validate_live_migration_safety

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = {
    "residents",
    "bql_staff",
    "resident_unit_memberships",
    "units",
    "tickets",
    "ticket_attachments",
    "ticket_attachment_upload_sessions",
    "ticket_status_history",
    "notifications",
    "audit_logs",
    "ai_analysis_runs",
    "ticket_scoring_results",
}


def test_alembic_configuration_files_exist():
    assert (PROJECT_ROOT / "alembic.ini").is_file()
    assert (PROJECT_ROOT / "alembic" / "env.py").is_file()


def test_target_metadata_points_to_application_base_metadata():
    env_text = (PROJECT_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert "from src.database.base import Base" in env_text
    assert "target_metadata = Base.metadata" in env_text
    assert Base.metadata.tables.keys() >= EXPECTED_TABLES


def test_alembic_uses_application_settings_for_database_url():
    env_text = (PROJECT_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert "from src.config import get_settings" in env_text
    assert "get_settings().require_database_url()" in env_text
    assert "config.set_main_option(\"sqlalchemy.url\", get_database_url())" in env_text


def test_alembic_ini_has_no_hardcoded_database_secret():
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    ini_text = (PROJECT_ROOT / "alembic.ini").read_text(encoding="utf-8")

    assert config.get_main_option("sqlalchemy.url") == ""
    assert "://" not in config.get_main_option("sqlalchemy.url")
    assert "password" not in ini_text.lower()
    assert "postgresql://" not in ini_text.lower()


def test_autogenerate_compare_options_are_enabled():
    env_text = (PROJECT_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert "compare_type=True" in env_text
    assert "compare_server_default=True" in env_text


@pytest.mark.parametrize(
    ("app_env", "allow_live_migration"),
    [
        ("production", True),
        ("development", False),
        ("test", False),
    ],
)
def test_live_migration_safety_blocks_unsafe_combinations(app_env, allow_live_migration):
    with pytest.raises(RuntimeError):
        validate_live_migration_safety(
            Settings(app_env=app_env, allow_live_migration=allow_live_migration, database_url=_placeholder_database_url())
        )


@pytest.mark.parametrize(("app_env", "allow_live_migration"), [("development", True), ("test", True)])
def test_live_migration_safety_allows_gated_development_and_test(app_env, allow_live_migration):
    validate_live_migration_safety(
        Settings(app_env=app_env, allow_live_migration=allow_live_migration, database_url=_placeholder_database_url())
    )


def test_online_alembic_path_invokes_gate_before_connection():
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        env=_safe_alembic_env(app_env="production", allow_live_migration="true"),
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode != 0
    assert "Online migration is allowed only in development or test." in combined
    assert "connection refused" not in combined.lower()
    assert "could not translate host name" not in combined.lower()


def test_offline_alembic_sql_output_contains_no_credentials():
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        env=_safe_alembic_env(app_env="production", allow_live_migration="false"),
        check=False,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0
    assert "password" not in combined.lower()
    assert _placeholder_database_url() not in combined


def _placeholder_database_url() -> str:
    return "postgresql://user:password@127.0.0.1:1/database"


def _safe_alembic_env(*, app_env: str, allow_live_migration: str) -> dict[str, str]:
    keep = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "PYTHONPATH", "VIRTUAL_ENV"}
    env = {name: value for name, value in os.environ.items() if name.upper() in keep}
    env.update(
        {
            "APP_ENV": app_env,
            "ALLOW_LIVE_MIGRATION": allow_live_migration,
            "DATABASE_URL": _placeholder_database_url(),
            "SUPABASE_URL": "",
            "SUPABASE_PUBLISHABLE_KEY": "",
            "SUPABASE_SECRET_KEY": "",
            "RUN_SUPABASE_INTEGRATION_TESTS": "false",
        }
    )
    return env
