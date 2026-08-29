from pathlib import Path

import pytest

from .conftest import generate


def answers_of(out: Path) -> dict[str, object]:
    import yaml

    return yaml.safe_load((out / ".copier-answers.yml").read_text())


def test_package_name_derived_from_project_name(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib", project_name="my-cool-proj")
    assert answers_of(out)["package_name"] == "my_cool_proj"


def test_preset_defaults_differ(tmp_path: Path) -> None:
    lib = answers_of(generate(tmp_path / "a", preset="lib"))
    api = answers_of(generate(tmp_path / "b", preset="api"))
    assert lib["settings"] == "none"
    assert lib["container"] is False
    assert api["settings"] == "pydantic"
    assert api["container"] is True


def test_cloud_requires_settings(tmp_path: Path) -> None:
    # copier 9.17.2 raises the validator failure as a plain ValueError, not
    # UserMessageError, from Question.validate_answer.
    with pytest.raises(ValueError, match="cloud requires settings=pydantic"):
        generate(tmp_path, preset="lib", cloud="aws", settings="none")
