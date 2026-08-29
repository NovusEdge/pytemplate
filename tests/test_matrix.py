from pathlib import Path

from .conftest import generate


def test_generates_readme(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    assert (out / "README.md").read_text().startswith("# demo-proj")
