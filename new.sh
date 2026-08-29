#!/usr/bin/env bash
# Scaffold a uv project with house defaults: src layout, ruff, mypy strict, pytest, justfile.
#   new.sh NAME [--app|--lib] [--dir PARENT]
set -euo pipefail

TEMPLATE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KIND="--lib"
PARENT="$PWD"
NAME=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --app|--lib) KIND="$1"; shift ;;
        --dir) PARENT="$2"; shift 2 ;;
        -*) echo "unknown flag: $1" >&2; exit 2 ;;
        *) NAME="$1"; shift ;;
    esac
done

[[ -n "$NAME" ]] || { echo "usage: new.sh NAME [--app|--lib] [--dir PARENT]" >&2; exit 2; }

DEST="$PARENT/$NAME"
[[ -e "$DEST" ]] && { echo "$DEST already exists" >&2; exit 1; }

uv init --package "$KIND" --name "$NAME" --vcs git --author-from auto "$DEST"
cd "$DEST"

# uv init writes no tool config; append house lint/type/test settings.
cat "$TEMPLATE/files/config.toml" >> pyproject.toml
cp "$TEMPLATE/files/justfile" justfile
cat "$TEMPLATE/files/gitignore" >> .gitignore

mkdir -p tests
cat > tests/test_smoke.py <<EOF
def test_imports() -> None:
    import ${NAME//-/_}  # noqa: F401
EOF

uv add --dev pytest pytest-asyncio ruff mypy
uv sync

echo
echo "$DEST ready. just check"
