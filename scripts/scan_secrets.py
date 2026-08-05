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
    "supabase_jwt": re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
    "database_url_with_password": re.compile(r"postgres(?:ql)?://[^:\s]+:[^@\s]+@"),
}


def tracked_files() -> list[Path]:
    result = subprocess.run(["git", "ls-files"], cwd=ROOT, text=True, capture_output=True, check=True)
    return [ROOT / line for line in result.stdout.splitlines() if line.strip()]


def is_skipped(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.relative_to(ROOT).parts)


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if is_skipped(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        except OSError:
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(text) and "postgresql://user:password@host:5432/database" not in text:
                findings.append(f"{path.relative_to(ROOT)}: {name}")
    if findings:
        print("Potential secrets detected:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("No obvious committed credentials detected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
