@echo off
setlocal

REM List of required Python packages
set PACKAGES=scipy numpy matplotlib flask werkzeug

REM Check for python
where python >nul 2>nul
if errorlevel 1 (
    echo Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Install missing packages
for %%p in (%PACKAGES%) do (
    python -c "import %%p" 2>NUL
    if errorlevel 1 (
        echo Installing missing package: %%p
        pip install %%p
        if errorlevel 1 (
            echo Failed to install %%p. Aborting.
            pause
            exit /b 1
        )
    ) else (
        echo Package %%p is already installed.
    )
)

REM Run the Python script
start "" /B python app.py

REM Wait a moment to let the server start
timeout /t 3 >nul

REM Open the URL in the default browser
start http://127.0.0.1:5000

endlocal
