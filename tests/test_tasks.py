import subprocess
import sys
from pathlib import Path

from .conftest import generate


def git(out: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=out, capture_output=True, text=True, check=True
    ).stdout


def test_generated_project_is_committed(tmp_path: Path) -> None:
    out = generate(tmp_path, run_tasks=True, preset="lib")
    assert git(out, "log", "--oneline").strip()
    assert git(out, "status", "--porcelain") == ""


def test_copier_update_runs(tmp_path: Path) -> None:
    out = generate(tmp_path, run_tasks=True, preset="lib")
    subprocess.run(
        [sys.executable, "-m", "copier", "update", "--defaults", "--trust", str(out)],
        check=True,
    )
