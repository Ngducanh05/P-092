"""Scan tracked text files for obvious credential patterns without printing values."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {".git", ".venv", ".pytest_cache", ".ruff_cache", "__pycache__", ".env", ".ai-log"}
PATTERNS = {
    "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "ai_log_key": re.compile(r"AI_LOG_API_KEY=[A-Za-z0-9_-]{30,}"),
    "supabase_secret_key": re.compile(r"sb_secret_[A-Za-z0-9_-]{20,}"),
    "supabase_jwt": re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
    "database_url_with_password": re.compile(r"postgres(?:ql)?://[^:\s]+:[^@\s]+@"),
}
ALLOWLISTED_MATCHES = {
    "supabase_secret_key": {
        "sb_secret_xxxxxxxxxxxxxxxxxxxx",
        "sb_secret_yourbackendsecretplaceholder",
    },
    "database_url_with_password": {
        "postgresql://user:password@",
    },
}


def tracked_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True)
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in _skip_parts(path))


def scan_paths(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if is_skipped(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError:
            continue
        for name, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                if match.group(0) in ALLOWLISTED_MATCHES.get(name, set()):
                    continue
                findings.append(f"{_display_path(path)}: {name}")
    return findings


def _display_path(path: Path) -> Path:
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return Path(path.name)


def _skip_parts(path: Path) -> tuple[str, ...]:
    try:
        return path.relative_to(ROOT).parts
    except ValueError:
        return path.parts


def main() -> int:
    findings = scan_paths(tracked_files())
    if findings:
        for finding in findings:
            print(finding)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
