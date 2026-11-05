@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  echo error: python not found on PATH 1>&2
  pause
  exit /b 1
)

echo Updating codesearch index ...
%PY% -m codesearch index
echo Opening http://127.0.0.1:5002 ...
start "" "http://127.0.0.1:5002"
%PY% -m codesearch serve %*
pause
