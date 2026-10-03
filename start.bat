@echo off
cd /d "%~dp0"
where npm >nul 2>&1
if errorlevel 1 (
  echo npm not found - skipping TypeScript build, serving existing static\js
) else (
  echo Building TypeScript to static\js ...
  call npm run build:ts
  if errorlevel 1 echo WARNING: TypeScript build failed - static\js may be stale
)
echo Starting Virtual World on http://127.0.0.1:4444
python app.py
pause
