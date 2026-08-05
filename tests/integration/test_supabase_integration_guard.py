"""Supabase integration tests are opt-in and fail fast when misconfigured."""

from __future__ import annotations

import os

import pytest

from src.config import get_settings

BASE_REQUIRED = (
    "APP_ENV",
    "DATABASE_URL",
    "SUPABASE_URL",
    "SUPABASE_PUBLISHABLE_KEY",
    "SUPABASE_SECRET_KEY",
    "SUPABASE_STORAGE_BUCKET",
)


def test_supabase_integration_guard_is_off_by_default():
    settings = get_settings()
    if settings.run_supabase_integration_tests:
        pytest.skip("Live Supabase integration flag is enabled; environment gate test covers safety.")
    assert settings.run_supabase_integration_tests is False


def test_supabase_integration_environment_fails_fast_when_enabled():
    settings = get_settings()
    if not settings.run_supabase_integration_tests:
        pytest.skip("RUN_SUPABASE_INTEGRATION_TESTS is not enabled.")
    missing = [name for name in BASE_REQUIRED if not os.getenv(name)]
    if settings.app_env not in {"development", "test"}:
        missing.append("APP_ENV development/test")
    if missing:
        pytest.fail("Missing safe Supabase integration variables: " + ", ".join(missing))


def test_live_resident_token_scenario_is_explicitly_gated():
    settings = get_settings()
    if not settings.run_supabase_integration_tests:
        pytest.skip("RUN_SUPABASE_INTEGRATION_TESTS is not enabled.")
    if not os.getenv("SUPABASE_TEST_RESIDENT_ACCESS_TOKEN"):
        pytest.skip("BLOCKED - MISSING TEST TOKEN: SUPABASE_TEST_RESIDENT_ACCESS_TOKEN")
    pytest.fail("Live resident token scenario requires project-specific fixtures before execution.")


def test_live_coordinator_token_scenario_is_explicitly_gated():
    settings = get_settings()
    if not settings.run_supabase_integration_tests:
        pytest.skip("RUN_SUPABASE_INTEGRATION_TESTS is not enabled.")
    if not os.getenv("SUPABASE_TEST_COORDINATOR_ACCESS_TOKEN"):
        pytest.skip("BLOCKED - MISSING TEST TOKEN: SUPABASE_TEST_COORDINATOR_ACCESS_TOKEN")
    pytest.fail("Live coordinator token scenario requires project-specific fixtures before execution.")
