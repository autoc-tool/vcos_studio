@echo off
setlocal
@REM Switch to the current directory
cd /d %~dp0

set CURRENT_PATH=%~dp0
set Path=%CURRENT_PATH%\..\..\.venv\Scripts;%Path%
python -s %CURRENT_PATH%\configurator.py

endlocal
pause 