# pytemplate

Scaffolds a uv Python project with house defaults.

```sh
~/Projects/pytemplate/new.sh myproject          # library (src layout, packaged)
~/Projects/pytemplate/new.sh myapp --app        # application entrypoint
~/Projects/pytemplate/new.sh thing --dir ~/tmp  # parent other than $PWD
```

What you get on top of `uv init --package`:

- ruff (line 100, `E F I UP B SIM ARG`) and mypy strict, both pinned to py313
- pytest with `asyncio_mode = auto` and a smoke test that imports the package
- a justfile: `just check` runs lint plus tests, plus `fmt`, `sync`, `test`, `clean`
- dev deps installed and `uv sync` run

`uv init` does the scaffolding, so the layout tracks whatever uv currently generates.
Config lives in `files/` and is appended to the generated `pyproject.toml`.

To put it on PATH:

```sh
ln -s ~/Projects/pytemplate/new.sh ~/.local/bin/pynew
```
