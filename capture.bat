@echo off
cd /d "%~dp0"
echo Updating Bulle...
git pull origin ui-motion
echo Taking screenshots (do not touch the window for ~40 seconds)...
uv run python tools\capture_screens.py
echo.
echo Send bulle_screens\contact_sheet.png and bulle_screens\report.txt
pause
