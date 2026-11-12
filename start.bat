@echo off
rem Start the Too Good To Go Telegram bot (Windows) - double-click this file.
rem First run: asks for the bot token and installs everything into .venv.
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
    if not errorlevel 1 (
        py -3 quickstart.py %*
        goto end
    )
)

where python >nul 2>nul
if %errorlevel%==0 (
    python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
    if not errorlevel 1 (
        python quickstart.py %*
        goto end
    )
)

echo Python 3.11 or newer is required but was not found.
echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH".

:end
echo.
pause
