from pathlib import Path

import copier

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "project_name": "demo-proj",
    "description": "A demo project",
    "author": "Aliasgar Khimani",
}


def generate(dst: Path, *, run_tasks: bool = False, **answers: object) -> Path:
    """Render the template into dst/<project_name> and return that path.

    unsafe=True is required because copier.yml declares _tasks. Tasks are
    skipped by default so fast tests don't pay for `uv sync`; pass
    run_tasks=True to run them.
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
        skip_tasks=not run_tasks,
    )
    return out
