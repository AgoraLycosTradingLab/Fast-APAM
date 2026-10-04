@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "tools\start_fast_apam.py" %*
) else (
    py -3 "tools\start_fast_apam.py" %*
)
set "taskExit=%errorlevel%"
if errorlevel 1 (
    echo.
    echo Fast APAM could not complete. Read the message above.
    echo If Python was not found, install Python 3.11 or newer and reopen VS Code.
)
pause
exit /b %taskExit%
