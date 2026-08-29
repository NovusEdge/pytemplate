# Python project generator

Date: 2026-08-29

Verified against copier 9.17.2.

## Purpose

Generate Python projects from a preset plus a small set of toggles, so that
settings, cloud clients, containers, and CI stop being retyped per project.
Generated projects stay connected to the template, so template improvements
reach projects created earlier.

## Approach

One copier template with conditional file paths. Copier was chosen over
cookiecutter for `copier update`, which merges upstream template changes into
an existing project. Two alternatives were rejected:

- Base template plus layered subtemplates. Each template stays small, but each
  keeps its own answers file, so updates must be reconciled per layer.
- A hand-written Python generator. Full control, at the cost of owning conflict
  resolution and update logic that copier already provides.

The cost is a template tree carrying jinja guards in file paths. Copier's source
tree is its destination tree, so a conditional file must sit at its real
destination. There is no way to group the optional files elsewhere.

## Invocation

`_tasks` makes the template unsafe in copier's terms, and copier aborts without
`--trust`. A `pynew` wrapper supplies the flag:

```sh
pynew myproject            # copier copy --trust <template> ./myproject
pynew myproject --update   # copier update --trust in an existing project
```

The wrapper stays under about ten lines. `ln -s ~/Projects/pytemplate/pynew
~/.local/bin/pynew` puts it on PATH.

## Question surface

`copier.yml` asks the preset first. The preset supplies jinja defaults for every
later question, and copier still prompts for each one, so any single answer can
be overridden. Defaults referencing an earlier answer are confirmed to work.

```yaml
preset:      lib | cli | api | pipeline
project_name, package_name, description, author, license
python:      3.13
settings:    none | pydantic
cloud:       none | aws | gcp
container:   bool
ci:          none | github
publish:     bool
```

Preset defaults:

| preset | settings | cloud | container | ci | publish |
|---|---|---|---|---|---|
| lib | none | none | false | github | false |
| cli | pydantic | none | false | github | false |
| api | pydantic | none | true | github | false |
| pipeline | pydantic | none | true | github | false |

The preset also selects the app skeleton, which is not a toggle:

- `lib`: bare package, nothing else
- `cli`: Typer entrypoint
- `api`: FastAPI app factory, health endpoint, logging setup
- `pipeline`: jobs directory with one example asset

`package_name` defaults to
`{{ project_name|lower|replace('-','_')|replace(' ','_') }}` and a validator
rejects anything that is not a Python identifier.

A validator rejects `cloud != none` when `settings == none`. A cloud client needs
configuration, and forcing settings on removes a code path from the template.

## Excluded

No `custom` preset. A copier `choices` question always has a selected default, so
"ask everything with no defaults" is not expressible. Picking a preset and
overriding at the prompt already covers it.

No database toggle. A database choice pulls in migrations, a driver, and test
fixtures, and the right default is not yet known.

No deploy-target toggle beyond the container. Cloud Run and ECS definitions go
stale faster than anything else in the tree.

## Layout

```
pytemplate/
  copier.yml
  pynew                       # wrapper supplying --trust
  template/
    pyproject.toml.jinja
    justfile
    README.md.jinja
    .gitignore.jinja
    LICENSE.jinja
    {{ _copier_conf.answers_file }}.jinja
    src/{{ package_name }}/__init__.py.jinja
    src/{{ package_name }}/py.typed
    src/{{ package_name }}/{% if settings == 'pydantic' %}settings.py{% endif %}.jinja
    src/{{ package_name }}/{% if cloud == 'aws' %}aws.py{% endif %}.jinja
    src/{{ package_name }}/{% if cloud == 'gcp' %}gcp.py{% endif %}.jinja
    tests/test_smoke.py.jinja
    {% if settings == 'pydantic' %}.env.example{% endif %}.jinja
    {% if container %}Dockerfile{% endif %}.jinja
    {% if container %}compose.yaml{% endif %}.jinja
    .github/workflows/{% if ci == 'github' %}check.yml{% endif %}.jinja
    .github/workflows/{% if publish %}publish.yml{% endif %}.jinja
  tests/test_matrix.py
```

Copier skips a file when any path segment renders empty. The guard wraps the
basename and `.jinja` stays outermost, because copier strips the `.jinja` suffix
before rendering the segment. Empty parent directories are still created, so a
guarded file must not be the only occupant of a directory that should not exist.

`copier.yml` declares both keys, because setting `_subdirectory` drops copier's
built-in exclude list:

```yaml
_subdirectory: template
_exclude: ["copier.yml", "~*", "*.py[co]", "__pycache__", ".git", ".DS_Store"]
_min_copier_version: "9.7.0"
```

The answers file ships in every generated project. Without it `copier update`
cannot run.

## Generation tasks

```yaml
_tasks:
  - "git init -q -b main"
  - "uv sync"
  - "git add -A"
  - "git -c user.useConfigOnly=false commit -qm 'Initial commit from pytemplate'"
```

Order matters. `copier update` requires a git repository holding at least one
commit and a clean working tree. `uv sync` writes `uv.lock`, so it must run
before the commit.

`_tasks` run on copy and not on update. The generated README states that an
update touching dependencies needs a manual `uv sync`.

## House defaults, applied to every preset

- ruff, line length 100, lint select `E F I UP B SIM ARG`, ignore `E501`
- mypy strict, pinned to the chosen Python version
- pytest with `asyncio_mode = auto` and `testpaths = ["tests"]`
- src layout, hatchling build backend, `py.typed` shipped in the wheel
- a justfile: `check` runs lint and tests; also `fmt`, `sync`, `test`, `clean`
- `tests/test_smoke.py` importing the package, so `just check` passes on a fresh
  project. Without a collected test, pytest exits 5 and fails the recipe.

`uv.lock` is committed for `cli`, `api`, and `pipeline`. The `lib` preset
gitignores it.

mypy strict is disabled when `cloud != none`. Neither boto3 nor the
google-cloud clients type-check clean under strict, and this keeps one rule
instead of a per-SDK mechanism. The trade is that a cloud project loses strict
checking on its own code too.

`.gitignore` covers `.env`, `.venv`, caches, and build output. The settings
feature emits `.env` support, and `_tasks` runs `git add -A`, so an ungitignored
`.env` would commit real credentials on the first generation.

## Decisions live in copier.yml

Computed values keep conditional logic out of the TOML. A question with
`when: false` is never asked, and copier stores the computed result:

```yaml
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
      + (['fastapi', 'uvicorn'] if preset == 'api' else [])) | tojson }}
```

`pyproject.toml.jinja` then loops over the result instead of branching inline.
The Python version has five spellings across `requires-python`, ruff
`target-version`, mypy `python_version`, the CI matrix, and the Docker base tag.
`py_tag` computes the no-dot form once.

Jinja partials via `{% include %}` are not used. A partials directory inside
`template/` would ship into every generated project.

## Feature output

`settings` emits a `BaseSettings` subclass with `env_prefix` derived from the
package name, `.env` support, and a nested delimiter, plus a `.env.example`
listing every field. The cloud and container toggles add their fields to this
same class.

`cloud=aws` emits a cached `boto3.Session` factory that reads region and profile
from settings. When `container` is true, it points at LocalStack.

`cloud=gcp` emits a client bootstrap using application default credentials, with
project read from settings and an emulator host override honored the same way.

`container` emits a multi-stage Dockerfile on the uv base image, and a compose
file carrying the app plus whatever emulator the cloud toggle implies.

`ci=github` emits a workflow running `just check` on push, using
`astral-sh/setup-uv` with caching and a concurrency group.

`publish` emits a tag-triggered PyPI workflow using trusted publishing, with
`id-token: write` and a matching `environment:`. Trusted publishing needs a
pending publisher registered on PyPI against the exact owner, repository,
workflow filename, and environment. The template fixes the filename; the
generated README carries the remaining setup steps, because the first
`git tag v0.1.0` fails opaquely without them.

`LICENSE` is written from the `license` answer, and the `[project]` license field
and classifiers are generated to agree with it.

## Testing

Two tiers, because a full `uv sync` per case runs into minutes and a slow suite
gets skipped.

Fast, the default, runs in seconds. It calls
`copier.run_copy(src, dst, data={...}, defaults=True, unsafe=True)` over roughly
twelve explicit answer combinations, then asserts which files exist, runs
`ruff check`, and compiles every emitted `.py`. No dependency resolution.

Slow, marked `@pytest.mark.slow` and run in CI, generates the four presets and
runs `just check` inside each.

The fast tier covers the combinations the presets never reach on their own:
`lib` with `container`, `cli` with `aws`, `gcp` with `container` for the
emulator branch, and `publish` independent of preset.

This matrix is the only guard against template rot. A generator that nobody
exercises breaks silently.

## Migration

`new.sh` and `files/` are superseded and get deleted. `pynew` replaces `new.sh`
as the entry point. The repository keeps its git history.

## Note for implementation

`justfile` ships without a `.jinja` suffix, so its `{{ARGS}}` survives verbatim.
If it ever needs a conditional and gains the suffix, recipe bodies must be
wrapped in `{% raw %}`, or `{{ARGS}}` renders empty.
