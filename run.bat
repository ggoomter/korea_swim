@echo off
echo ========================================
echo 한국 수영장 정보 API 서버 시작
echo ========================================
echo.

REM 가상환경 활성화 (있는 경우)
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM 서버 실행
echo 서버 시작 중...
echo API 문서: http://localhost:8000/docs
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
