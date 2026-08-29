default:
    @just --list

# Generate a project into DEST
new DEST:
    ./pynew {{DEST}}

# Pull template changes into an existing generated project
update DEST:
    ./pynew {{DEST}} --update

test:
    uv run pytest -m "not slow"

# Generate each preset and run its full check suite
test-slow:
    uv run pytest -m slow

check: test test-slow
