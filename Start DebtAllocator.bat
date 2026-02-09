@echo off
setlocal

cd /d "%~dp0"

if exist "DebtAllocator\DebtAllocator.exe" (
  start "" "DebtAllocator\DebtAllocator.exe"
) else (
  echo DebtAllocator.exe was not found near this file.
  echo Expected path: DebtAllocator\DebtAllocator.exe
  pause
)

endlocal
