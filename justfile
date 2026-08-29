default: test

test:
    uv run pytest -m "not slow"

test-slow:
    uv run pytest -m slow

check: test test-slow
