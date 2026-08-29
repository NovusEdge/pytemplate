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


def test_license_year_is_answerable(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib", year="2031")
    assert "2031" in (out / "LICENSE").read_text()


def test_settings_present_when_pydantic(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="api")
    assert (out / "src/demo_proj/settings.py").exists()
    assert (out / ".env.example").exists()
    assert "pydantic-settings" in (out / "pyproject.toml").read_text()


def test_settings_absent_when_none(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    assert not (out / "src/demo_proj/settings.py").exists()
    assert not (out / ".env.example").exists()


def test_aws_module_and_dep(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="api", cloud="aws")
    assert (out / "src/demo_proj/aws.py").exists()
    assert not (out / "src/demo_proj/gcp.py").exists()
    assert "boto3" in (out / "pyproject.toml").read_text()
    assert "aws_region" in (out / "src/demo_proj/settings.py").read_text()


def test_gcp_module_and_dep(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="api", cloud="gcp")
    assert (out / "src/demo_proj/gcp.py").exists()
    assert "google-cloud-core" in (out / "pyproject.toml").read_text()


def test_mypy_strict_off_for_cloud(tmp_path: Path) -> None:
    plain = generate(tmp_path / "a", preset="api")
    cloudy = generate(tmp_path / "b", preset="api", cloud="aws")
    assert "strict = true" in (plain / "pyproject.toml").read_text()
    assert "strict = true" not in (cloudy / "pyproject.toml").read_text()


def test_container_files(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="api")
    assert (out / "Dockerfile").exists()
    assert (out / "compose.yaml").exists()


def test_no_container_for_lib(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    assert not (out / "Dockerfile").exists()


def test_compose_carries_emulator(tmp_path: Path) -> None:
    aws = generate(tmp_path / "a", preset="api", cloud="aws")
    plain = generate(tmp_path / "b", preset="api")
    assert "localstack" in (aws / "compose.yaml").read_text()
    assert "localstack" not in (plain / "compose.yaml").read_text()


def test_lib_can_opt_into_container(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib", container=True)
    assert (out / "Dockerfile").exists()
