from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api import pools
from database.connection import init_db
import os

app = FastAPI(
    title="한국 수영장 정보 API",
    description="전국 수영장 정보 검색 및 관리 시스템",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(pools.router)

# 정적 파일 서빙 (프론트엔드)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.on_event("startup")
def startup_event():
    """앱 시작 시 DB 초기화"""
    init_db()

@app.get("/")
def root():
    """프론트엔드 메인 페이지 제공"""
    index_path = os.path.join(frontend_path, "index_refactored.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "한국 수영장 정보 API",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
