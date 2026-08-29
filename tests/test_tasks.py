import subprocess
import sys
from pathlib import Path

import copier

from .conftest import DEFAULTS, TEMPLATE_ROOT


def git(out: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=out, capture_output=True, text=True, check=True
    ).stdout


def generate_from_head(dst: Path) -> Path:
    """Like conftest.generate, but pins the answers file to this repo's last
    commit instead of copier's synthetic dirty-tree ref. copier's local-clone
    path only folds uncommitted changes into a wip commit when vcs_ref is the
    literal string "HEAD" (copier/_vcs.py: `if ref == "HEAD" and ...`); an
    explicit commit SHA skips that and checks out the real commit, so
    copier update stays checkoutable even while this repo's own working
    tree is dirty (mid-development is exactly when that's true).
    """
    head = git(TEMPLATE_ROOT, "rev-parse", "HEAD").strip()
    data = {**DEFAULTS, "preset": "lib"}
    out = dst / str(data["project_name"])
    copier.run_copy(
        str(TEMPLATE_ROOT),
        str(out),
        data=data,
        defaults=True,
        unsafe=True,
        quiet=True,
        vcs_ref=head,
    )
    return out


def test_generated_project_is_committed(tmp_path: Path) -> None:
    out = generate_from_head(tmp_path)
    assert git(out, "log", "--oneline").strip()
    assert git(out, "status", "--porcelain") == ""


def test_copier_update_runs(tmp_path: Path) -> None:
    out = generate_from_head(tmp_path)
    subprocess.run(
        [sys.executable, "-m", "copier", "update", "--defaults", "--trust", str(out)],
        check=True,
    )
