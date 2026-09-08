@echo off

cd /d "%~dp0"

echo. >> logs\monitor.log
echo ======================================== >> logs\monitor.log
echo Run started: %date% %time% >> logs\monitor.log
echo ======================================== >> logs\monitor.log

.venv\Scripts\python.exe price_monitor.py >> logs\monitor.log 2>&1

set EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE% EQU 0 (
    echo Run finished successfully: %date% %time% >> logs\monitor.log
) else (
    echo RUN FAILED with exit code %EXIT_CODE%: %date% %time% >> logs\monitor.log
)

exit /b %EXIT_CODE%