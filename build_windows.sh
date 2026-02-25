#!/usr/bin/env bash
set -euo pipefail

APP_NAME="DeptAllocation"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"

cd "$(dirname "$0")"

if command -v py >/dev/null 2>&1; then
  PY_CREATE=(py "-${PYTHON_VERSION}")
elif command -v python >/dev/null 2>&1; then
  PY_CREATE=(python)
else
  echo "Python launcher not found (py/python)." >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  "${PY_CREATE[@]}" -m venv .venv
fi

if [ ! -f ".venv/Scripts/activate" ]; then
  echo "Expected venv activation script not found: .venv/Scripts/activate" >&2
  exit 1
fi

source .venv/Scripts/activate

python -m pip install -U pip
pip install --no-compile -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --windowed --onefile --name "$APP_NAME" app.py

rm -rf build "${APP_NAME}.spec"
find dist -mindepth 1 -maxdepth 1 ! -name "${APP_NAME}.exe" -exec rm -rf {} +

echo "Build complete: dist/${APP_NAME}.exe"
