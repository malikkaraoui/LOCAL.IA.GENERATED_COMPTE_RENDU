#!/usr/bin/env python3
"""Met à jour automatiquement le fichier VERSION à partir de l'état Git."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "VERSION"


def _run_git(*args: str) -> str:
    return (
        subprocess.check_output(["git", *args], cwd=ROOT, text=True)
        .strip()
        .replace("\n", "")
    )


def compute_version() -> str:
    timestamp = datetime.now(UTC).strftime("%Y.%m.%d-%H%M")
    try:
        describe = _run_git("describe", "--tags", "--always")
    except subprocess.CalledProcessError:
        describe = _run_git("rev-parse", "--short", "HEAD")
    try:
        commit_count = _run_git("rev-list", "--count", "HEAD")
    except subprocess.CalledProcessError:
        commit_count = "0"
    return f"{describe}+build.{commit_count}.{timestamp}"


def main() -> None:
    version = compute_version()
    VERSION_FILE.write_text(version + "\n", encoding="utf-8")
    print(f"VERSION mise à jour -> {version}")


if __name__ == "__main__":
    main()
