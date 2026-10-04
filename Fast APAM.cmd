@echo off
setlocal
rem Double-click sessions stay open even if Python fails or input is cancelled.
rem Explicit command arguments retain normal noninteractive exit behavior.
if not "%~1"=="" goto run
if defined FAST_APAM_KEEP_OPEN goto run
set "FAST_APAM_KEEP_OPEN=1"
"%ComSpec%" /d /k call "%~f0"
exit /b
:run
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
if defined FAST_APAM_KEEP_OPEN (
    echo.
    echo This window will stay open. Type exit to close it.
)
exit /b %taskExit%
