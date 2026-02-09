@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv" (
  py -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install -U pip >nul
python -m pip install -r requirements.txt pyinstaller >nul

pyinstaller --noconfirm --windowed --name DebtAllocator app.py

set "RELEASE_DIR=release\DebtAllocator-windows"
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
mkdir "%RELEASE_DIR%"
xcopy /e /i /y "dist\DebtAllocator" "%RELEASE_DIR%\DebtAllocator" >nul
copy /y "Start DebtAllocator.bat" "%RELEASE_DIR%\Start DebtAllocator.bat" >nul

echo.
echo Done: %RELEASE_DIR%
echo Zip this folder and send it to user.
endlocal
