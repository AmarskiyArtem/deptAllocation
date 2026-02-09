#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
APP_PATH="$HERE/DebtAllocator.app"

if [[ ! -d "$APP_PATH" ]]; then
  osascript -e 'display dialog "Не найден DebtAllocator.app рядом с этим файлом." buttons {"OK"} default button "OK"'
  exit 1
fi

xattr -dr com.apple.quarantine "$APP_PATH" || true
open "$APP_PATH"
