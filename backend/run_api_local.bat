@echo off
setlocal
set "PORT=%~1"
if "%PORT%"=="" set "PORT=8000"

cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv\Scripts\python.exe not found.
  pause
  exit /b 1
)

echo [TRON API] Running on port %PORT%
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%

