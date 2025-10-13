@echo off
cd /d "%~dp0"

start "FastAPI Server" cmd /k "uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak > nul

start http://localhost:8000

exit
