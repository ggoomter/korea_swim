@echo off
chcp 65001 >nul 2>&1
setlocal

cls
echo 한국 수영장 정보 API 서버 시작
echo.

python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo 필수 패키지 설치 중...
    pip install -r requirements.txt >nul 2>&1
    echo 설치 완료!
    echo.
)

echo API 문서: http://localhost:8000/docs
echo 웹페이지: frontend\index_refactored.html
echo.
echo 서버 실행 중... (종료: Ctrl+C)
echo.

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

pause >nul
