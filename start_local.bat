@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\backend"
set "ENV_FILE=%ROOT%\.env"
set "PYTHON_EXE=%BACKEND%\.venv\Scripts\python.exe"
set "APP_PORT=8000"
set "JOB_MODE=inline"
set "DRY_RUN=0"

if /I "%~1"=="--dry-run" set "DRY_RUN=1"

echo.
echo [TRON] Starting...
echo [TRON] Root: %ROOT%
echo.

if not exist "%BACKEND%\app\main.py" (
  echo [ERROR] backend\app\main.py not found.
  pause
  exit /b 1
)

if not exist "%ENV_FILE%" (
  if exist "%ROOT%\.env.local.example" (
    copy /Y "%ROOT%\.env.local.example" "%ENV_FILE%" >nul
    echo [TRON] .env created from .env.local.example
  ) else (
    echo [ERROR] .env not found and .env.local.example missing.
    pause
    exit /b 1
  )
)

if not exist "%PYTHON_EXE%" (
  echo [TRON] Creating virtual environment...
  py -3 -m venv "%BACKEND%\.venv" 2>nul
  if errorlevel 1 (
    python -m venv "%BACKEND%\.venv"
    if errorlevel 1 (
      echo [ERROR] Failed to create venv. Please install Python 3.11+.
      pause
      exit /b 1
    )
  )
)

echo [TRON] Installing dependencies...
cd /d "%BACKEND%"
"%PYTHON_EXE%" -m pip -q install --upgrade pip
"%PYTHON_EXE%" -m pip -q install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  pause
  exit /b 1
)

for /f "tokens=1,* delims==" %%A in ('findstr /r /b /c:"APP_PORT=" /c:"JOB_EXECUTION_MODE=" "%ENV_FILE%"') do (
  if /I "%%A"=="APP_PORT" set "APP_PORT=%%B"
  if /I "%%A"=="JOB_EXECUTION_MODE" set "JOB_MODE=%%B"
)

if "%DRY_RUN%"=="1" (
  echo [DRY-RUN] APP_PORT=%APP_PORT%
  echo [DRY-RUN] JOB_EXECUTION_MODE=%JOB_MODE%
  echo [DRY-RUN] Would start API and open browser.
  pause
  exit /b 0
)

echo.
echo [TRON] Starting API window...
start "TRON API" cmd /k ""%BACKEND%\run_api_local.bat" %APP_PORT%"

if /I "%JOB_MODE%"=="redis" (
  echo [TRON] Starting Worker window (redis mode)...
  start "TRON Worker" cmd /k ""%BACKEND%\run_worker_local.bat""
) else (
  echo [TRON] Inline mode detected, worker is not required.
)

echo [TRON] Waiting for API and opening browser...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$u='http://localhost:%APP_PORT%/api/v1/health'; for($i=0;$i -lt 40;$i++){ try{ $r=Invoke-RestMethod -Uri $u -TimeoutSec 2; if($r.ok -eq $true){ Start-Process 'http://localhost:%APP_PORT%/'; exit 0 } } catch{}; Start-Sleep -Milliseconds 500 }; Start-Process 'http://localhost:%APP_PORT%/'"

echo.
echo [TRON] Done: http://localhost:%APP_PORT%/
echo [TRON] Close TRON API / TRON Worker windows to stop.
echo.
pause
