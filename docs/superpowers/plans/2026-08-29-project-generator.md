# Python project generator implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a copier template that generates Python projects from a preset plus toggles for settings, cloud, container, CI, and publishing.

**Architecture:** One copier template. `copier.yml` holds the question surface, the computed values, and the post-generation tasks. `template/` holds the rendered tree, with optional files carrying a jinja guard in their basename. A `pynew` wrapper supplies the `--trust` flag that `_tasks` requires. The template's own test suite generates projects and asserts on the result.

**Tech Stack:** copier 9.17.2, uv, just, pytest, ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-08-29-project-generator-design.md`

## Global Constraints

- Repository root is `~/Projects/pytemplate`. All paths below are relative to it.
- Copier version floor is 9.17.2. `copier.yml` declares `_min_copier_version: "9.7.0"`.
- Generated projects target Python 3.13 by default, answered by the `python` question.
- Generated house defaults, identical for every preset: ruff line-length 100, lint select `["E", "F", "I", "UP", "B", "SIM", "ARG"]`, ignore `["E501"]`; mypy strict; pytest `asyncio_mode = "auto"` and `testpaths = ["tests"]`; src layout; hatchling build backend.
- A conditional file carries its guard in the basename with `.jinja` outermost: `{% if cond %}name.ext{% endif %}.jinja`. Copier strips `.jinja` before rendering the segment.
- Copier skips a file when any path segment renders empty. Empty parent directories are still created.
- Presets are `lib`, `cli`, `api`, `pipeline`. There is no `custom` preset.
- Commits in this repository use `git commit -s` and carry no co-author trailer.
- Every task ends with `uv run pytest` passing before its commit.

---

### Task 1: Test harness and repository scaffolding

Establishes the TDD loop. Everything after this task is driven by tests that generate a project and assert on the result.

**Files:**
- Create: `pyproject.toml`
- Create: `tests/conftest.py`
- Create: `tests/test_matrix.py`
- Create: `copier.yml`
- Create: `template/README.md.jinja`
- Delete: `new.sh`, `files/config.toml`, `files/justfile`, `files/gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: `generate(tmp_path, **answers) -> Path` in `tests/conftest.py`, a pytest fixture-free helper that every later task's tests call. It returns the generated project root.

- [ ] **Step 1: Write the failing test**

Create `tests/conftest.py`:

```python
from pathlib import Path

import copier

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "project_name": "demo-proj",
    "description": "A demo project",
    "author": "Aliasgar Khimani",
}


def generate(dst: Path, **answers: object) -> Path:
    """Render the template into dst/<project_name> and return that path.

    unsafe=True is required because copier.yml declares _tasks.
    """
    data = {**DEFAULTS, **answers}
    out = dst / str(data["project_name"])
    copier.run_copy(
        str(TEMPLATE_ROOT),
        str(out),
        data=data,
        defaults=True,
        unsafe=True,
        quiet=True,
    )
    return out
```

Create `tests/test_matrix.py`:

```python
from pathlib import Path

from .conftest import generate


def test_generates_readme(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    assert (out / "README.md").read_text().startswith("# demo-proj")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_matrix.py -v`
Expected: FAIL. `copier.yml` does not exist yet, so copier raises before rendering.

- [ ] **Step 3: Write minimal implementation**

Create `pyproject.toml`:

```toml
[project]
name = "pytemplate"
version = "0.1.0"
description = "Copier template for Python projects"
requires-python = ">=3.13"

[dependency-groups]
dev = [
    "copier>=9.17.2",
    "pytest>=8.0",
    "ruff>=0.4",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["slow: generates a project and runs its full check suite"]
```

Create `copier.yml`:

```yaml
_min_copier_version: "9.7.0"
_subdirectory: template
_exclude:
  - "copier.yml"
  - "~*"
  - "*.py[co]"
  - "__pycache__"
  - ".git"
  - ".DS_Store"

preset:
  type: str
  help: Project archetype
  choices: [lib, cli, api, pipeline]
  default: lib

project_name:
  type: str
  help: Project name, used for the directory and the distribution

description:
  type: str
  help: One-line description
  default: ""

author:
  type: str
  help: Author name
  default: ""
```

Create `template/README.md.jinja`:

```jinja
# {{ project_name }}

{{ description }}

## Development

```sh
just check
```
```

Delete the superseded scaffold:

```bash
git rm -q new.sh files/config.toml files/justfile files/gitignore
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv sync && uv run pytest tests/test_matrix.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add copier scaffold and test harness"
```

---

### Task 2: Question surface, computed values, validators

**Files:**
- Modify: `copier.yml`
- Create: `tests/test_questions.py`

**Interfaces:**
- Consumes: `generate()` from Task 1.
- Produces: the full answer set every later task branches on: `preset`, `project_name`, `package_name`, `description`, `author`, `license`, `python`, `settings`, `cloud`, `container`, `ci`, `publish`. Two computed values: `py_tag` (e.g. `py313`) and `runtime_deps` (a list of requirement strings).

- [ ] **Step 1: Write the failing test**

Create `tests/test_questions.py`:

```python
from pathlib import Path

import pytest
from copier.errors import UserMessageError

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
    with pytest.raises(UserMessageError):
        generate(tmp_path, preset="lib", cloud="aws", settings="none")


def test_computed_values(tmp_path: Path) -> None:
    a = answers_of(generate(tmp_path, preset="cli"))
    assert a["py_tag"] == "py313"
    assert "typer" in a["runtime_deps"]
```

Add `pyyaml` to the dev group in `pyproject.toml`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_questions.py -v`
Expected: FAIL. `package_name`, `py_tag`, and `runtime_deps` are absent from the answers file, and no validator rejects the cloud/settings combination.

- [ ] **Step 3: Write minimal implementation**

Replace the question block in `copier.yml` (keep the `_`-prefixed keys from Task 1 at the top):

```yaml
preset:
  type: str
  help: Project archetype
  choices: [lib, cli, api, pipeline]
  default: lib

project_name:
  type: str
  help: Project name, used for the directory and the distribution

package_name:
  type: str
  help: Importable package name
  default: "{{ project_name|lower|replace('-','_')|replace(' ','_') }}"
  validator: >-
    {% if not package_name.isidentifier() %}
    package_name must be a valid Python identifier
    {% endif %}

description:
  type: str
  help: One-line description
  default: ""

author:
  type: str
  help: Author name
  default: ""

license:
  type: str
  choices: [Apache-2.0, MIT, proprietary]
  default: Apache-2.0

python:
  type: str
  help: Target Python version
  default: "3.13"

settings:
  type: str
  choices: [none, pydantic]
  default: "{{ 'none' if preset == 'lib' else 'pydantic' }}"

cloud:
  type: str
  choices: [none, aws, gcp]
  default: none
  validator: >-
    {% if cloud != 'none' and settings == 'none' %}
    cloud requires settings=pydantic
    {% endif %}

container:
  type: bool
  default: "{{ preset in ['api', 'pipeline'] }}"

ci:
  type: str
  choices: [none, github]
  default: github

publish:
  type: bool
  default: false

py_tag:
  type: str
  when: false
  default: "py{{ python|replace('.','') }}"

runtime_deps:
  type: yaml
  when: false
  default: >-
    {{ ((['pydantic-settings>=2'] if settings == 'pydantic' else [])
      + (['boto3'] if cloud == 'aws' else [])
      + (['google-cloud-core'] if cloud == 'gcp' else [])
      + (['typer'] if preset == 'cli' else [])
      + (['fastapi', 'uvicorn'] if preset == 'api' else [])
      + (['dagster'] if preset == 'pipeline' else [])) | tojson }}
```

Create `template/{{ _copier_conf.answers_file }}.jinja`:

```jinja
{{ _copier_answers|to_nice_yaml }}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS, both test files.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add question surface with computed values"
```

---

### Task 3: Base template tree

Every preset gets these files. After this task a generated `lib` project passes `ruff check` and `pytest`.

**Files:**
- Create: `template/pyproject.toml.jinja`
- Create: `template/justfile`
- Create: `template/.gitignore.jinja`
- Create: `template/LICENSE.jinja`
- Create: `template/src/{{ package_name }}/__init__.py.jinja`
- Create: `template/src/{{ package_name }}/py.typed`
- Create: `template/tests/test_smoke.py.jinja`
- Modify: `tests/test_matrix.py`

**Interfaces:**
- Consumes: all answers from Task 2.
- Produces: a generated project whose `pyproject.toml` carries `[project]`, `[dependency-groups]`, `[build-system]`, `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`. Later tasks append sections and files rather than restructuring these.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matrix.py`:

```python
import compileall
import subprocess


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
    assert subprocess.run(["ruff", "check", str(out)]).returncode == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_matrix.py -v`
Expected: FAIL on the missing `pyproject.toml`.

- [ ] **Step 3: Write minimal implementation**

Create `template/pyproject.toml.jinja`:

```jinja
[project]
name = "{{ project_name }}"
version = "0.1.0"
description = "{{ description }}"
readme = "README.md"
requires-python = ">={{ python }}"
{% if license != 'proprietary' %}license = { text = "{{ license }}" }
{% endif %}authors = [{ name = "{{ author }}" }]
dependencies = [
{% for dep in runtime_deps %}    "{{ dep }}",
{% endfor %}]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "ruff>=0.4",
    "mypy>=1.10",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{{ package_name }}"]

[tool.ruff]
line-length = 100
target-version = "{{ py_tag }}"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "ARG"]
ignore = ["E501"]

[tool.mypy]
python_version = "{{ python }}"
{% if cloud == 'none' %}strict = true
{% endif %}warn_return_any = true
warn_unused_configs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Create `template/justfile` (no `.jinja` suffix, so `{{ARGS}}` survives):

```
default: check

sync:
    uv sync

fmt:
    uv run ruff format .
    uv run ruff check --fix .

lint:
    uv run ruff check .
    uv run mypy src

test *ARGS:
    uv run pytest {{ARGS}}

check: lint test

clean:
    rm -rf .pytest_cache .mypy_cache .ruff_cache dist
    find . -name __pycache__ -type d -prune -exec rm -rf {} +
```

Create `template/.gitignore.jinja`:

```jinja
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
.coverage
htmlcov/
.env
{% if preset == 'lib' %}uv.lock
{% endif %}
```

Create `template/LICENSE.jinja`. For `Apache-2.0` and `MIT`, write the full standard text with `{{ author }}` and the year in the copyright line. For `proprietary`, write:

```jinja
{% if license == 'proprietary' %}Copyright (c) {{ author }}. All rights reserved.
{% endif %}
```

Create `template/src/{{ package_name }}/__init__.py.jinja`:

```jinja
"""{{ description or project_name }}."""

__version__ = "0.1.0"
```

Create `template/src/{{ package_name }}/py.typed` as an empty file.

Create `template/tests/test_smoke.py.jinja`:

```jinja
def test_imports() -> None:
    import {{ package_name }}

    assert {{ package_name }}.__version__
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add base template tree"
```

---

### Task 4: Settings feature

**Files:**
- Create: `template/src/{{ package_name }}/{% if settings == 'pydantic' %}settings.py{% endif %}.jinja`
- Create: `template/{% if settings == 'pydantic' %}.env.example{% endif %}.jinja`
- Modify: `tests/test_matrix.py`

**Interfaces:**
- Consumes: `settings`, `package_name`, `cloud` answers.
- Produces: a `Settings` class and a module-level `settings` instance in `<package>/settings.py`. Tasks 5 and 6 add fields to this same class through their own jinja guards inside this file.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matrix.py`:

```python
def test_settings_present_when_pydantic(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="api")
    assert (out / "src/demo_proj/settings.py").exists()
    assert (out / ".env.example").exists()
    assert "pydantic-settings" in (out / "pyproject.toml").read_text()


def test_settings_absent_when_none(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    assert not (out / "src/demo_proj/settings.py").exists()
    assert not (out / ".env.example").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_matrix.py -k settings -v`
Expected: FAIL on the missing `settings.py`.

- [ ] **Step 3: Write minimal implementation**

Create `template/src/{{ package_name }}/{% if settings == 'pydantic' %}settings.py{% endif %}.jinja`:

```jinja
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="{{ package_name|upper }}_",
        env_file=".env",
        env_nested_delimiter="__",
        extra="ignore",
    )

    log_level: str = "INFO"


settings = Settings()
```

Create `template/{% if settings == 'pydantic' %}.env.example{% endif %}.jinja`:

```jinja
{{ package_name|upper }}_LOG_LEVEL=INFO
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add pydantic-settings toggle"
```

---

### Task 5: Cloud features

**Files:**
- Create: `template/src/{{ package_name }}/{% if cloud == 'aws' %}aws.py{% endif %}.jinja`
- Create: `template/src/{{ package_name }}/{% if cloud == 'gcp' %}gcp.py{% endif %}.jinja`
- Modify: `template/src/{{ package_name }}/{% if settings == 'pydantic' %}settings.py{% endif %}.jinja`
- Modify: `template/{% if settings == 'pydantic' %}.env.example{% endif %}.jinja`
- Modify: `tests/test_matrix.py`

**Interfaces:**
- Consumes: `cloud`, `settings`, `container`, `package_name`.
- Produces: `get_session()` in `aws.py` returning a cached `boto3.Session`. `get_client_options()` in `gcp.py` returning a dict of client options. Both read from the `Settings` instance produced by Task 4.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matrix.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_matrix.py -k "aws or gcp or strict" -v`
Expected: FAIL on the missing `aws.py`.

- [ ] **Step 3: Write minimal implementation**

Create `template/src/{{ package_name }}/{% if cloud == 'aws' %}aws.py{% endif %}.jinja`:

```jinja
from functools import cache

import boto3

from .settings import settings


@cache
def get_session() -> boto3.Session:
    return boto3.Session(
        region_name=settings.aws_region,
        profile_name=settings.aws_profile or None,
    )
{% if container %}

# LocalStack listens on this endpoint under compose. Pass it to every client:
#   get_session().client("s3", endpoint_url=endpoint_url())
def endpoint_url() -> str | None:
    return settings.aws_endpoint_url or None
{% endif %}
```

Create `template/src/{{ package_name }}/{% if cloud == 'gcp' %}gcp.py{% endif %}.jinja`:

```jinja
from .settings import settings


def get_client_options() -> dict[str, str]:
    """Keyword arguments common to every google-cloud client."""
    options: dict[str, str] = {"project": settings.gcp_project}
    if settings.gcp_emulator_host:
        options["client_options"] = settings.gcp_emulator_host
    return options
```

Add to `settings.py.jinja`, inside the `Settings` class body after `log_level`:

```jinja
{% if cloud == 'aws' %}
    aws_region: str = "eu-north-1"
    aws_profile: str = ""
{% if container %}    aws_endpoint_url: str = ""
{% endif %}{% endif %}{% if cloud == 'gcp' %}
    gcp_project: str = ""
    gcp_emulator_host: str = ""
{% endif %}
```

Add the matching lines to `.env.example.jinja` under the same guards.

The mypy strict guard already lives in `pyproject.toml.jinja` from Task 3.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add aws and gcp toggles"
```

---

### Task 6: Container feature

**Files:**
- Create: `template/{% if container %}Dockerfile{% endif %}.jinja`
- Create: `template/{% if container %}compose.yaml{% endif %}.jinja`
- Modify: `tests/test_matrix.py`

**Interfaces:**
- Consumes: `container`, `cloud`, `py_tag`, `python`, `package_name`, `preset`.
- Produces: no Python symbols. The compose file names its emulator service `localstack` for aws and `gcloud-emulator` for gcp.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matrix.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_matrix.py -k container -v`
Expected: FAIL on the missing `Dockerfile`.

- [ ] **Step 3: Write minimal implementation**

Create `template/{% if container %}Dockerfile{% endif %}.jinja`:

```jinja
FROM ghcr.io/astral-sh/uv:python{{ python }}-bookworm-slim AS build
WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project
COPY . .
RUN uv sync --no-dev

FROM python:{{ python }}-slim-bookworm
WORKDIR /app
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
ENV PATH="/app/.venv/bin:$PATH"
{% if preset == 'api' %}EXPOSE 8000
CMD ["uvicorn", "{{ package_name }}.app:app", "--host", "0.0.0.0", "--port", "8000"]
{% elif preset == 'cli' %}ENTRYPOINT ["{{ project_name }}"]
{% else %}CMD ["python", "-m", "{{ package_name }}"]
{% endif %}
```

Create `template/{% if container %}compose.yaml{% endif %}.jinja`:

```jinja
services:
  app:
    build: .
{% if preset == 'api' %}    ports:
      - "8000:8000"
{% endif %}    env_file:
      - .env
{% if cloud == 'aws' %}    environment:
      {{ package_name|upper }}_AWS_ENDPOINT_URL: http://localstack:4566
    depends_on:
      - localstack

  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
{% elif cloud == 'gcp' %}    environment:
      {{ package_name|upper }}_GCP_EMULATOR_HOST: gcloud-emulator:8085
    depends_on:
      - gcloud-emulator

  gcloud-emulator:
    image: gcr.io/google.com/cloudsdktool/google-cloud-cli:emulators
    command: gcloud beta emulators pubsub start --host-port=0.0.0.0:8085
    ports:
      - "8085:8085"
{% endif %}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add container toggle"
```

---

### Task 7: CI and publish workflows

**Files:**
- Create: `template/.github/workflows/{% if ci == 'github' %}check.yml{% endif %}.jinja`
- Create: `template/.github/workflows/{% if publish %}publish.yml{% endif %}.jinja`
- Modify: `template/README.md.jinja`
- Modify: `tests/test_matrix.py`

**Interfaces:**
- Consumes: `ci`, `publish`, `python`, `project_name`.
- Produces: no Python symbols. The publish workflow filename is fixed at `publish.yml`, which the PyPI pending publisher must match.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matrix.py`:

```python
def test_ci_workflow(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    wf = out / ".github/workflows/check.yml"
    assert wf.exists()
    body = wf.read_text()
    assert "astral-sh/setup-uv" in body
    assert "just check" in body


def test_publish_is_opt_in(tmp_path: Path) -> None:
    off = generate(tmp_path / "a", preset="lib")
    on = generate(tmp_path / "b", preset="lib", publish=True)
    assert not (off / ".github/workflows/publish.yml").exists()
    assert (on / ".github/workflows/publish.yml").exists()
    assert "id-token: write" in (on / ".github/workflows/publish.yml").read_text()


def test_publish_setup_documented(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib", publish=True)
    assert "pending publisher" in (out / "README.md").read_text()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_matrix.py -k "ci or publish" -v`
Expected: FAIL on the missing `check.yml`.

- [ ] **Step 3: Write minimal implementation**

Create `template/.github/workflows/{% if ci == 'github' %}check.yml{% endif %}.jinja`:

```jinja
name: check

on:
  push:
  pull_request:

concurrency:
  group: check-${{ '{{' }} github.ref {{ '}}' }}
  cancel-in-progress: true

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "{{ python }}"
          enable-cache: true
      - uses: extractions/setup-just@v2
      - run: just check
```

Note on escaping: GitHub Actions `${{ }}` collides with jinja. Write it as
`${{ '{{' }} ... {{ '}}' }}` as shown, or wrap the whole file body in
`{% raw %}` and interpolate the answers outside the raw block.

Create `template/.github/workflows/{% if publish %}publish.yml{% endif %}.jinja`:

```jinja
name: publish

on:
  push:
    tags: ["v*"]

jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          python-version: "{{ python }}"
      - run: uv build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Append to `template/README.md.jinja`:

```jinja
{% if publish %}
## Publishing

Tagging `v*` publishes to PyPI through trusted publishing. Before the first tag,
register a pending publisher on PyPI with these exact values:

- Project name: `{{ project_name }}`
- Workflow filename: `publish.yml`
- Environment: `pypi`

A tag pushed before that step fails with an opaque authentication error.
{% endif %}
## Updating from the template

```sh
pynew . --update
```

Post-generation tasks do not re-run on update. Run `uv sync` yourself if an
update changes dependencies.
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add ci and publish workflows"
```

---

### Task 8: Preset app skeletons

**Files:**
- Create: `template/src/{{ package_name }}/{% if preset == 'cli' %}cli.py{% endif %}.jinja`
- Create: `template/src/{{ package_name }}/{% if preset == 'api' %}app.py{% endif %}.jinja`
- Create: `template/src/{{ package_name }}/jobs/{% if preset == 'pipeline' %}example.py{% endif %}.jinja`
- Modify: `template/pyproject.toml.jinja`
- Modify: `tests/test_matrix.py`

**Interfaces:**
- Consumes: `preset`, `package_name`, `project_name`, `settings`.
- Produces: `main()` in `cli.py` wired as a console script. `create_app() -> FastAPI` and a module-level `app` in `app.py`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_matrix.py`:

```python
def test_cli_skeleton(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="cli")
    assert (out / "src/demo_proj/cli.py").exists()
    assert "[project.scripts]" in (out / "pyproject.toml").read_text()


def test_api_skeleton(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="api")
    body = (out / "src/demo_proj/app.py").read_text()
    assert "def create_app()" in body
    assert "/health" in body


def test_pipeline_skeleton(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="pipeline")
    assert (out / "src/demo_proj/jobs/example.py").exists()


def test_lib_has_no_skeleton(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    assert not (out / "src/demo_proj/cli.py").exists()
    assert not (out / "src/demo_proj/app.py").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_matrix.py -k skeleton -v`
Expected: FAIL on the missing `cli.py`.

- [ ] **Step 3: Write minimal implementation**

Create `template/src/{{ package_name }}/{% if preset == 'cli' %}cli.py{% endif %}.jinja`:

```jinja
import typer

app = typer.Typer()


@app.command()
def hello(name: str = "world") -> None:
    typer.echo(f"hello {name}")


def main() -> None:
    app()
```

Create `template/src/{{ package_name }}/{% if preset == 'api' %}app.py{% endif %}.jinja`:

```jinja
import logging

from fastapi import FastAPI
{% if settings == 'pydantic' %}
from .settings import settings
{% endif %}

def create_app() -> FastAPI:
{% if settings == 'pydantic' %}    logging.basicConfig(level=settings.log_level)
{% else %}    logging.basicConfig(level="INFO")
{% endif %}    api = FastAPI(title="{{ project_name }}")

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return api


app = create_app()
```

Create `template/src/{{ package_name }}/jobs/{% if preset == 'pipeline' %}example.py{% endif %}.jinja`:

```jinja
import dagster as dg


@dg.asset
def example_asset() -> int:
    return 1
```

Add to `pyproject.toml.jinja`, after `[project]`:

```jinja
{% if preset == 'cli' %}
[project.scripts]
{{ project_name }} = "{{ package_name }}.cli:main"
{% endif %}
```

Note: the `jobs/` directory renders for every preset because copier creates
empty parent directories. Add `jobs/__init__.py.jinja` guarded the same way so
the directory carries content only for `pipeline`, and accept the empty
directory otherwise.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add preset app skeletons"
```

---

### Task 9: Post-generation tasks and the pynew wrapper

This is the task that makes `copier update` work. Its test is the only one that runs an actual update.

**Files:**
- Modify: `copier.yml`
- Create: `pynew`
- Create: `tests/test_tasks.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `pynew NAME [--update]` on PATH. A generated project that is a git repository with one commit and a clean tree.

- [ ] **Step 1: Write the failing test**

Create `tests/test_tasks.py`:

```python
import subprocess
from pathlib import Path

from .conftest import generate


def git(out: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=out, capture_output=True, text=True, check=True
    ).stdout


def test_generated_project_is_committed(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    assert git(out, "log", "--oneline").strip()
    assert git(out, "status", "--porcelain") == ""


def test_copier_update_runs(tmp_path: Path) -> None:
    out = generate(tmp_path, preset="lib")
    subprocess.run(
        ["copier", "update", "--defaults", "--trust", str(out)], check=True
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_tasks.py -v`
Expected: FAIL. No `_tasks` exist, so the generated directory is not a git repository.

- [ ] **Step 3: Write minimal implementation**

Append to `copier.yml`:

```yaml
_tasks:
  - "git init -q -b main"
  - "uv sync"
  - "git add -A"
  - "git -c user.useConfigOnly=false commit -qm 'Initial commit from pytemplate'"

_message_after_copy: |
  {{ project_name }} is ready.

    cd {{ project_name }} && just check
```

Create `pynew`:

```bash
#!/usr/bin/env bash
# copier requires --trust because the template declares _tasks.
set -euo pipefail

TEMPLATE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "${2:-}" == "--update" ]]; then
    exec copier update --trust "$1"
fi

exec copier copy --trust "$TEMPLATE" "${1:?usage: pynew NAME [--update]}"
```

Run `chmod +x pynew`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest -v`
Expected: PASS. The update test proves the task ordering leaves a clean tree.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add post-generation tasks and pynew wrapper"
```

---

### Task 10: Slow tier and repository README

**Files:**
- Create: `tests/test_slow.py`
- Modify: `README.md`
- Modify: `justfile`

**Interfaces:**
- Consumes: everything above.
- Produces: nothing later depends on.

- [ ] **Step 1: Write the failing test**

Create `tests/test_slow.py`:

```python
import subprocess
from pathlib import Path

import pytest

from .conftest import generate

PRESETS = ["lib", "cli", "api", "pipeline"]


@pytest.mark.slow
@pytest.mark.parametrize("preset", PRESETS)
def test_generated_project_passes_check(tmp_path: Path, preset: str) -> None:
    out = generate(tmp_path, preset=preset)
    result = subprocess.run(["just", "check"], cwd=out, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `uv run pytest -m slow -v`
Expected: PASS if the preceding tasks are correct. A failure here names the preset and shows the `just check` output, which is the point of the tier. Fix any failure before continuing.

- [ ] **Step 3: Write the repository docs**

Rewrite `README.md`:

```markdown
# pytemplate

Copier template for Python projects.

```sh
pynew myproject          # generate
pynew ./myproject --update   # pull template changes into an existing project
```

`ln -s ~/Projects/pytemplate/pynew ~/.local/bin/pynew` puts it on PATH.

## Presets

| preset | settings | container | skeleton |
|---|---|---|---|
| lib | none | no | bare package |
| cli | pydantic | no | Typer entrypoint |
| api | pydantic | yes | FastAPI app factory |
| pipeline | pydantic | yes | Dagster asset |

Every answer is overridable at the prompt. Toggles: `settings`, `cloud`,
`container`, `ci`, `publish`.

## Tests

`just test` runs the fast tier in seconds. `just test-slow` generates each
preset and runs its full check suite.
```

Create `justfile` at the repository root:

```
default: test

test:
    uv run pytest -m "not slow"

test-slow:
    uv run pytest -m slow

check: test test-slow
```

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -v && uv run pytest -m slow -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -s -m "feat: add slow test tier and repository docs"
```

---

## Self-review notes

Spec coverage checked section by section. Invocation is Task 9. Question surface
is Task 2. Layout and excludes are Tasks 1 and 2. Generation tasks are Task 9.
House defaults are Task 3. Computed values are Task 2. Feature output is Tasks 4
through 8. Testing is Tasks 1 and 10. Migration is Task 1, which deletes
`new.sh` and `files/`.

Two spec details deliberately deferred into the tasks that need them: the
GitHub Actions `${{ }}` escaping problem surfaces only in Task 7, and the empty
`jobs/` directory surfaces only in Task 8. Both carry their fix inline.
