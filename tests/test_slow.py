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
