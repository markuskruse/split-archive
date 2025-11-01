#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

cd "$PROJECT_ROOT"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "Error: PyInstaller is required but was not found in PATH." >&2
  echo "Install it with: python3 -m pip install pyinstaller" >&2
  exit 1
fi

APP_SCRIPT="split-archive.py"

if [ ! -f "$APP_SCRIPT" ]; then
  echo "Error: $APP_SCRIPT not found in $PROJECT_ROOT" >&2
  exit 1
fi

rm -rf build dist "$APP_SCRIPT".spec

pyinstaller --onefile --name split-archive "$APP_SCRIPT"

cat <<INFO

Build complete! The executable can be found at:
  $(pwd)/dist/split-archive
INFO
