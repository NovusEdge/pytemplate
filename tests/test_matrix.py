import compileall
import subprocess
from pathlib import Path

from .conftest import generate


def test_generates_readme(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    assert (out / "README.md").read_text().startswith("# demo-proj")


def test_lib_base_tree(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    for rel in (
        "pyproject.toml",
        "justfile",
        ".gitignore",
        "LICENSE",
        "src/demo_proj/__init__.py",
        "src/demo_proj/py.typed",
        "tests/test_smoke.py",
    ):
        assert (out / rel).exists(), rel


def test_gitignore_covers_env(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    body = (out / ".gitignore").read_text()
    assert ".env" in body
    assert ".venv/" in body


def test_generated_python_compiles_and_lints(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    assert compileall.compile_dir(str(out), quiet=2)
    assert subprocess.run(["uv", "run", "ruff", "check", str(out)]).returncode == 0


def test_computed_values_reach_pyproject(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="cli")
    body = (out / "pyproject.toml").read_text()
    assert 'target-version = "py313"' in body
    assert '"typer",' in body
