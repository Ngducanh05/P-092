"""Alembic configuration tests."""

from pathlib import Path

from alembic.config import Config

import src.database.models  # noqa: F401
from src.database.base import Base

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = {
    "users",
    "units",
    "tickets",
    "ticket_attachments",
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
    assert "get_settings().database_url" in env_text
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
