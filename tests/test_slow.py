import subprocess
from pathlib import Path

import pytest

from .conftest import generate

PRESETS = ["lib", "cli", "api", "pipeline"]


@pytest.mark.slow
@pytest.mark.parametrize("preset", PRESETS)
def test_generated_project_passes_check(tmp_path: Path, preset: str) -> None:
    out = generate(tmp_path, run_tasks=True, preset=preset)
    result = subprocess.run(["just", "check"], cwd=out, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


# The async and sync engine branches are separate code paths, and neither is
# type-checked anywhere else. Redis rides along to cover its own import.
DB_CASES = [
    ("api", "postgres", True),
    ("cli", "sqlite", False),
]


@pytest.mark.slow
@pytest.mark.parametrize(("preset", "db", "redis"), DB_CASES)
def test_db_project_passes_check(tmp_path: Path, preset: str, db: str, redis: bool) -> None:
    out = generate(tmp_path, run_tasks=True, preset=preset, db=db, redis=redis)
    result = subprocess.run(["just", "check"], cwd=out, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
