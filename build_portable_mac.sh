#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -U pip >/dev/null
python -m pip install -r requirements.txt pyinstaller >/dev/null

pyinstaller --noconfirm --windowed --name DebtAllocator app.py

RELEASE_DIR="release/DebtAllocator-mac"
rm -rf "$RELEASE_DIR"
mkdir -p "$RELEASE_DIR"
cp -R "dist/DebtAllocator.app" "$RELEASE_DIR/DebtAllocator.app"
cp "Run DebtAllocator.command" "$RELEASE_DIR/Run DebtAllocator.command"
chmod +x "$RELEASE_DIR/Run DebtAllocator.command"

echo "Готово: $RELEASE_DIR"
echo "Упакуйте папку в zip и отправьте пользователю."
