@echo off
setlocal
chcp 65001 >nul

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  echo error: python not found on PATH 1>&2
  exit /b 1
)

if "%~1"=="" (
  %PY% "%~dp0tasks.py"
) else (
  %PY% "%~dp0tasks.py" %*
)
exit /b %errorlevel%
