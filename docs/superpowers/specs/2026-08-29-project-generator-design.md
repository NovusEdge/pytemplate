# Python project generator

Date: 2026-08-29

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

The cost of the chosen approach is a template tree carrying jinja conditions in
file paths. Confining those files to `_features/` contains the noise.

## Question surface

`copier.yml` asks the preset first. The preset supplies jinja defaults for every
later question, and copier still prompts for each one, so any single answer can
be overridden.

```yaml
preset:      lib | cli | api | pipeline | custom
project_name, package_name, description, author
python:      3.13
settings:    none | pydantic
cloud:       none | aws | gcp
container:   bool
ci:          none | github
```

Preset defaults:

| preset | settings | cloud | container | ci |
|---|---|---|---|---|
| lib | none | none | false | github + publish |
| cli | pydantic | none | false | github |
| api | pydantic | ask | true | github |
| pipeline | pydantic | ask | true | github |

`custom` asks every question with no preset defaults.

The preset also selects the app skeleton, which is not a toggle:

- `lib`: bare package, nothing else
- `cli`: Typer entrypoint
- `api`: FastAPI app factory, health endpoint, logging setup
- `pipeline`: jobs directory with one example asset

## Excluded

No database toggle. A database choice pulls in migrations, a driver, and test
fixtures, and the right default is not yet known.

No deploy-target toggle beyond the container. Cloud Run and ECS definitions go
stale faster than anything else in the tree.

## Layout

```
pytemplate/
  copier.yml
  template/
    pyproject.toml.jinja
    justfile
    README.md.jinja
    .gitignore
    {{ _copier_conf.answers_file }}.jinja
    src/{{ package_name }}/__init__.py.jinja
    _features/
      settings.py.jinja
      cloud_aws.py.jinja
      cloud_gcp.py.jinja
      Dockerfile.jinja
      compose.yaml.jinja
      ci.yml.jinja
  tests/test_matrix.py
```

Conditional files carry a jinja guard in the path. Copier skips a file whose
rendered path is empty. The exact idiom must be confirmed against the installed
copier version during implementation, because it has changed across releases.

`_tasks` in `copier.yml` runs `git init` and `uv sync` after generation.

The answers file ships in every generated project. Without it `copier update`
cannot run.

`pyproject.toml.jinja` assembles the dependency list, optional-dependency
groups, and tool config from the answers. It carries most of the template's
complexity.

## House defaults, applied to every preset

- ruff, line length 100, lint select `E F I UP B SIM ARG`, ignore `E501`
- mypy strict, pinned to the chosen Python version
- pytest with `asyncio_mode = auto` and `testpaths = ["tests"]`
- src layout, hatchling build backend
- a justfile: `check` runs lint and tests; also `fmt`, `sync`, `test`, `clean`

## Feature output

`settings` emits a `BaseSettings` subclass with `env_prefix` derived from the
package name, `.env` support, and a nested delimiter. It also emits a
`.env.example` listing every field. The cloud and container toggles add their
fields to this same class.

`cloud=aws` emits a cached `boto3.Session` factory that reads region and profile
from settings. When `container` is true, it points at LocalStack.

`cloud=gcp` emits a client bootstrap using application default credentials, with
project read from settings and an emulator host override honored the same way.

`container` emits a multi-stage Dockerfile on the uv base image, and a compose
file carrying the app plus whatever emulator the cloud toggle implies.

`ci=github` emits a workflow running `just check` on push against the pinned
Python. The `lib` preset adds a tag-triggered PyPI publish using trusted
publishing, so no token is stored in the repository.

## Testing

`tests/test_matrix.py` generates every preset into a temporary directory and
runs `just check` inside each one. A combination that fails to lint, type-check,
or test fails the suite.

Each cloud value gets its own case, because `aws` and `gcp` paths never render
together.

This matrix is the only guard against template rot. A generator that nobody
exercises breaks silently.

## Migration

The existing `new.sh` and `files/` are superseded and get deleted. The repository
keeps its git history.
