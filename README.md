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
