@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title codesearch - VirtualWorld

set "TARGET_DIR=%~dp0"
if "%TARGET_DIR:~-1%"=="\" set "TARGET_DIR=%TARGET_DIR:~0,-1%"
set "SCRIPT_DIR=F:\AI\codesearch"
set "PY=C:\ProgramData\miniconda3\python.exe"
set "PYTHONPATH=%SCRIPT_DIR%\src"
set "CODESEARCH_ROOT=%TARGET_DIR%"
set "PYTHONUNBUFFERED=1"
set "CODESEARCH_LOG_LEVEL=DEBUG"
set "CODESEARCH_DEBUG_TIMINGS=1"

if not exist "%PY%" (
    where python >nul 2>nul && set "PY=python"
)

echo ============================================================
echo  codesearch workbench  -  %TARGET_DIR%
echo  PYTHON:     %PY%
echo  PYTHONPATH: %PYTHONPATH%
echo  LOG_FILE:   %TARGET_DIR%\.codesearch\web.log
echo ============================================================
echo.

rem --- if port 5002 is already serving, just open the browser ----------------------
"%PY%" -c "import socket,sys; s=socket.socket(); r=s.connect_ex(('127.0.0.1',5002)); s.close(); sys.exit(0 if r==0 else 1)" >nul 2>&1
if not errorlevel 1 (
    echo [!] codesearch UI is already running on http://127.0.0.1:5002 - opening browser...
    start "" "http://127.0.0.1:5002"
    exit /b 0
)

rem --- start web UI FIRST; index + embed + pack run on a background thread ---------
echo Opening http://127.0.0.1:5002 immediately (index + vector pack refresh running in background)...
start "" "http://127.0.0.1:5002"
"%PY%" -u -m codesearch -r "%TARGET_DIR%" serve --bg-index %*
pause
