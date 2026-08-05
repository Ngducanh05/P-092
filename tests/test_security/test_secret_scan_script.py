"""Tests for repository secret scanner."""

from scripts.scan_secrets import main


def test_secret_scan_script_passes_for_tracked_files():
    assert main() == 0
