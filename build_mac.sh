#!/usr/bin/env bash
set -euo pipefail

APP_NAME="DeptAllocation"
PYTHON_BIN="${PYTHON_BIN:-python3}"
DIST_DIR="dist"
APP_PATH="${DIST_DIR}/${APP_NAME}.app"
ZIP_PATH="${DIST_DIR}/${APP_NAME}.zip"
MAC_SIGN_IDENTITY="${MAC_SIGN_IDENTITY:-}"

cd "$(dirname "$0")"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python not found: $PYTHON_BIN" >&2
  exit 1
fi

if [ ! -d ".venv" ]; then
  "$PYTHON_BIN" -m venv .venv
fi

source .venv/bin/activate

python -m pip install -U pip
pip install --no-compile -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --windowed --name "$APP_NAME" app.py

rm -rf build "${APP_NAME}.spec"
find "$DIST_DIR" -mindepth 1 -maxdepth 1 ! -name "${APP_NAME}.app" -exec rm -rf {} +

if [ ! -d "$APP_PATH" ]; then
  echo "Build failed: ${APP_PATH} not found" >&2
  exit 1
fi

# Optional Developer ID signing for better compatibility with Gatekeeper.
if [ -n "$MAC_SIGN_IDENTITY" ]; then
  echo "Signing app with identity: $MAC_SIGN_IDENTITY"
  codesign --force --deep --options runtime --timestamp --sign "$MAC_SIGN_IDENTITY" "$APP_PATH"
  codesign --verify --deep --strict --verbose=2 "$APP_PATH"
fi

if ! command -v ditto >/dev/null 2>&1; then
  echo "ditto not found; cannot create distribution zip safely for macOS app bundles" >&2
  exit 1
fi

rm -f "$ZIP_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$ZIP_PATH"

echo "Build complete: ${APP_PATH}"
echo "Zip ready: ${ZIP_PATH}"
if [ -z "$MAC_SIGN_IDENTITY" ]; then
  echo "Note: app is unsigned with Developer ID (set MAC_SIGN_IDENTITY to sign)."
fi
