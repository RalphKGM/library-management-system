@echo off
setlocal
cd /d "%~dp0"

if not exist "instance\library.sqlite3" (
  echo Demo database is missing. Extract the full ZIP before running this file.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    where python >nul 2>nul
    if errorlevel 1 (
      echo Install Python 3.9 or newer from python.org, then run this file again.
      pause
      exit /b 1
    )
    python -m venv .venv
  )
  if errorlevel 1 (
    echo Could not create the Python environment.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Could not install the required Python packages. Check your internet connection.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" run_demo.py
if errorlevel 1 (
  echo The demo did not start. Check the message above.
  pause
  exit /b 1
)
