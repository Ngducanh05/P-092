"""Supabase integration tests are opt-in only."""

import pytest

from src.config import get_settings


def test_supabase_integration_guard_is_off_by_default():
    settings = get_settings()
    if settings.run_supabase_integration_tests:
        pytest.skip("Live Supabase tests require external project-specific fixtures.")
    assert settings.run_supabase_integration_tests is False
