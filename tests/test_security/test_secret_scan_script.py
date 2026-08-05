"""Tests for repository secret scanner."""

from pathlib import Path

from scripts.scan_secrets import main, scan_paths


def test_secret_scan_script_passes_for_tracked_files():
    assert main() == 0


def test_known_database_placeholder_is_allowed(tmp_path):
    path = tmp_path / "example.txt"
    placeholder = "postgresql://user:" + "password@host:5432/database"
    path.write_text(f"DATABASE_URL={placeholder}\n", encoding="utf-8")

    assert scan_paths([path]) == []


def test_real_openai_like_secret_detected_without_value(tmp_path):
    secret = "sk-" + ("a" * 40)
    path = tmp_path / "openai.txt"
    path.write_text(f"OPENAI_API_KEY={secret}\n", encoding="utf-8")

    findings = scan_paths([path])

    assert findings == [f"{path.name}: openai_key"]
    assert secret not in findings[0]


def test_real_jwt_like_secret_detected_without_value(tmp_path):
    secret = "eyJ" + ("a" * 24) + "." + ("b" * 24) + "." + ("c" * 24)
    path = tmp_path / "jwt.txt"
    path.write_text(secret, encoding="utf-8")

    findings = scan_paths([path])

    assert findings == [f"{path.name}: supabase_jwt"]
    assert secret not in findings[0]


def test_real_database_url_with_password_detected_without_value(tmp_path):
    secret = "postgresql://real_user:" + "real_password@db.example:5432/app"
    path = tmp_path / "database.txt"
    path.write_text(secret, encoding="utf-8")

    findings = scan_paths([path])

    assert findings == [f"{path.name}: database_url_with_password"]
    assert secret not in findings[0]


def test_file_with_placeholder_and_real_database_url_still_fails(tmp_path):
    path = tmp_path / "mixed.txt"
    placeholder = "postgresql://user:" + "password@host:5432/database"
    secret = "postgresql://real_user:" + "real_password@db.example:5432/app"
    path.write_text(
        "\n".join(
            [
                f"DATABASE_URL={placeholder}",
                f"OTHER_URL={secret}",
            ]
        ),
        encoding="utf-8",
    )

    assert scan_paths([path]) == [f"{path.name}: database_url_with_password"]


def test_env_venv_and_binary_files_are_skipped(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=" + "sk-" + ("a" * 40), encoding="utf-8")
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    venv_file = venv_dir / "secret.txt"
    venv_file.write_text("OPENAI_API_KEY=" + "sk-" + ("a" * 40), encoding="utf-8")
    binary_file = tmp_path / "image.png"
    binary_file.write_bytes(b"\xff\xfe\x00\x00")

    assert scan_paths([env_file, venv_file, binary_file]) == []


def test_findings_print_only_path_and_pattern_type(capsys, monkeypatch, tmp_path):
    secret = "sk-" + ("a" * 40)
    path = tmp_path / "tracked.txt"
    path.write_text(secret, encoding="utf-8")
    monkeypatch.setattr("scripts.scan_secrets.tracked_files", lambda: [Path(path)])

    assert main() == 1
    output = capsys.readouterr().out

    assert f"- {path.name}: openai_key" in output
    assert secret not in output
