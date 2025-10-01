# 서울 수영장 찾기 프로젝트 - 완전 가이드

## 📋 목차
1. [빠른 시작](#빠른-시작)
2. [프로젝트 개요](#프로젝트-개요)
3. [서버 실행 방법](#서버-실행-방법)
4. [API 키 설정](#api-키-설정)
5. [주요 기능](#주요-기능)
6. [데이터 크롤링](#데이터-크롤링)
7. [환경 설정](#환경-설정)
8. [API 문서](#api-문서)
9. [파일 구조](#파일-구조)
10. [문제 해결](#문제-해결)

---

## 🚀 빠른 시작

### 화면 바로 열기 (서버 없이)
파일 탐색기에서 더블클릭:
```
G:\ai_coding\korea_swim\frontend\index_refactored.html
```

### 서버와 함께 실행
```bash
# 1. 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 2. 브라우저에서 파일 열기
# G:\ai_coding\korea_swim\frontend\index_refactored.html
```

---

## 프로젝트 개요
서울시 수영장 정보를 지도에서 검색하고 필터링할 수 있는 웹 애플리케이션
- **현재 DB**: 83개 수영장 (공공 47개 + 민간 36개)
- **실제 크롤링**: 네이버 검색 API로 실제 수영장 정보 수집

## 아키텍처

### 백엔드 (FastAPI)
- **app/main.py**: FastAPI 서버, 수영장 API 엔드포인트
- **app/database.py**: SQLite 데이터베이스 연결
- **app/models.py**: 수영장 데이터 모델 (SQLAlchemy)
- **app/crud.py**: 데이터베이스 CRUD 작업

### 프론트엔드
- **frontend/index_refactored.html**: 메인 페이지
  - 카카오맵 API 통합
  - 수영장 검색/필터링 UI
  - 지하철역 기반 검색

### 데이터 수집
- **crawler/advanced_crawler.py**: 수영장 정보 크롤러
  - 네이버 검색 API로 이미지 수집
  - Claude API로 이미지 분석 (선택적)
  - pools_data.json에서 수영장 정보 로드
- **crawler/pools_data.json**: 수영장 기본 정보 (이름, 주소, 가격 등)
- **load_data_to_db.py**: JSON 데이터를 DB에 로드

### 설정 파일
- **frontend/data/subway_lines.json**: 서울 지하철 노선 정보
- **frontend/data/config.json**: 카카오맵 API 키 등 설정

## 주요 기능

### 1. 수영장 검색
- 지도 중심점 기반 반경 검색
- 이름/주소 키워드 검색
- 지하철역 근처 검색

### 2. 필터링
- 가격대 필터
- 시설 필터 (사우나, 주차장 등)
- 수영장 크기 필터
- 평점 필터

### 3. 이미지 크롤링
크롤러는 **수동 실행**만 가능:
```bash
python crawler/advanced_crawler.py
```

**이미지 필터링 방식:**
1. 키워드 필터링 (기본)
   - 수영장 관련 키워드 포함 확인
   - 광고/로고 등 제외 키워드 필터링

2. Claude 이미지 분석 (선택적)
   - `ANTHROPIC_API_KEY` 환경변수 설정 시 활성화
   - 실제 수영장 사진인지 AI로 검증
   - 로고, 광고, 공사 사진 등 자동 제외

## 데이터 흐름

```
pools_data.json
    → advanced_crawler.py (이미지 수집)
    → advanced_pools.json
    → load_data_to_db.py
    → swimming_pools.db
    → FastAPI (/api/pools)
    → Frontend (지도 표시)
```

---

## 🖥️ 서버 실행 방법

### 방법 1: 서버 없이 사용 (권장)
프론트엔드만 사용 가능:
```bash
# 파일 탐색기에서 더블클릭
G:\ai_coding\korea_swim\frontend\index_refactored.html
```
- ✅ 지도 표시, 지하철역 검색 가능
- ❌ 수영장 데이터 표시 안됨 (API 필요)

### 방법 2: 서버와 함께 실행
전체 기능 사용:
```bash
# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 파일 탐색기에서 HTML 열기
G:\ai_coding\korea_swim\frontend\index_refactored.html
```
- ✅ 모든 기능 사용 가능
- ✅ 수영장 데이터 표시됨

### 서버 상태 확인
```bash
# API 테스트
curl http://localhost:8000/health
# 응답: {"status": "healthy"}

# 수영장 데이터 확인
curl http://localhost:8000/api/pools?lat=37.5665&lng=126.9780&radius=5
```

---

## 🔑 API 키 설정

### 1. 카카오맵 API 키
**위치**: `frontend/data/config.json`
```json
{
  "kakaoMapKey": "YOUR_KAKAO_API_KEY"
}
```

**발급 방법**:
1. https://developers.kakao.com 접속
2. 내 애플리케이션 > 앱 만들기
3. 플랫폼 설정 > Web 플랫폼 추가
4. JavaScript 키 복사 → config.json에 붙여넣기

### 2. 네이버 검색 API (크롤러용)
**위치**: `crawler/advanced_crawler.py:16-17`
```python
self.naver_client_id = "VDnVKXoA66gaC4cz3vzc"
self.naver_client_secret = "XuMSFxDf35"
```

**발급 방법**:
1. https://developers.naver.com/apps 접속
2. 애플리케이션 등록
3. 검색 API 선택
4. Client ID/Secret 복사 → 코드에 붙여넣기

### 3. Claude API (이미지 분석, 선택)
**위치**: 환경변수
```bash
# Windows
set ANTHROPIC_API_KEY=your_api_key

# Linux/Mac
export ANTHROPIC_API_KEY=your_api_key
```

**발급 방법**:
1. https://console.anthropic.com 접속
2. API Keys 생성
3. 환경변수 설정

---

## 🎯 주요 기능

### 1. 지도 기반 수영장 검색
- **반경 검색**: 지도 중심에서 1-10km 내 수영장 검색
- **마커 클릭**: 수영장 상세정보 팝업 표시
- **현재 위치**: 내 위치 기반 검색

### 2. 지하철역 기반 검색
- **위치**: `frontend/data/subway_lines.json`
- **노선별 역 검색**: 1-9호선, 분당선, 신분당선 등
- **역 선택 시**: 해당 역 근처 수영장 자동 검색

### 3. 필터링 기능
- **가격대**: 일일권/자율수영권 가격 범위
- **시설**: 사우나, 주차장, 락커룸, 샤워실, 카페 등
- **평점**: 최소 평점 지정
- **정렬**: 거리순/가격순/평점순

### 4. 수영장 정보 표시
- 이름, 주소, 전화번호
- 가격 정보 (일일권, 자율수영, 회원권)
- 운영시간, 자율수영 시간
- 시설, 레인 수, 수온
- 이미지 (크롤링된 경우)

---

## 🕷️ 데이터 크롤링

### 크롤러 실행 (수동)
```bash
# 네이버에서 서울 수영장 검색 + 이미지 수집
python crawler/advanced_crawler.py

# 결과: advanced_pools.json (36개 수영장)
```

### DB에 저장
```bash
# 중복 체크 후 저장/업데이트
python load_data_to_db.py advanced_pools.json

# 결과:
# - 신규 수영장: 새로 추가
# - 기존 수영장(이름+주소 동일): 정보 업데이트
```

### 크롤러 동작 방식
1. **네이버 지역 검색 API** 호출
   - 키워드: "서울 수영장", "서울 실내수영장", "서울 호텔 수영장" 등
   - 결과: 수영장 이름, 주소, 좌표, 카테고리
2. **중복 제거**: 이름+주소 기준
3. **이미지 수집**: 네이버 이미지 검색 API
4. **이미지 필터링**:
   - 키워드 필터 (기본): "수영", "pool" 포함 확인
   - Claude 분석 (선택): AI로 실제 수영장 사진인지 검증

### 수집된 데이터 종류
- 공공 수영장: 구민체육센터, 공원 수영장 등
- 민간 수영장: 스포츠센터, 헬스장, 수영 아카데미
- 호텔 수영장: 노보텔, 반얀트리, 롯데시티호텔 등
- 기타: 복지관, 청소년센터 수영장

---

## ⚙️ 환경 설정

### 설정 파일 위치

| 설정 | 파일 경로 | 내용 |
|------|----------|------|
| 카카오맵 API | `frontend/data/config.json` | JavaScript 키 |
| 지하철 정보 | `frontend/data/subway_lines.json` | 서울 지하철 노선/역 |
| 네이버 API | `crawler/advanced_crawler.py:16-17` | Client ID/Secret |
| Claude API | 환경변수 `ANTHROPIC_API_KEY` | API 키 |

### 데이터베이스
- **파일**: `swimming_pools.db` (SQLite)
- **위치**: 프로젝트 루트
- **내용**: 수영장 정보, 운영시간, 가격 등
- **초기화**: `load_data_to_db.py` 실행 시 자동 생성

### Python 패키지
```bash
pip install fastapi uvicorn sqlalchemy pydantic requests anthropic
```

## API 엔드포인트

### GET /api/pools
수영장 목록 조회 (필터링/정렬 지원)

**쿼리 파라미터:**
- `lat`, `lng`: 중심 좌표
- `radius`: 검색 반경 (km)
- `search`: 검색 키워드
- `min_price`, `max_price`: 가격 범위
- `facilities`: 시설 필터 (콤마 구분)
- `sort_by`: 정렬 기준 (distance, price, rating)

**응답:**
```json
[
  {
    "id": 1,
    "name": "삼성 래미안 수영장",
    "address": "서울 강남구 영동대로 513",
    "lat": 37.5089,
    "lng": 127.0632,
    "phone": "02-3011-0900",
    "daily_price": 15000,
    "free_swim_price": 12000,
    "image_url": "https://...",
    "facilities": ["사우나", "주차장"],
    "rating": 4.6
  }
]
```

## 파일 구조

```
korea_swim/
├── app/                          # 백엔드
│   ├── main.py
│   ├── models.py
│   ├── database.py
│   └── crud.py
├── crawler/                      # 크롤러
│   ├── advanced_crawler.py
│   └── pools_data.json          # 수영장 정보
├── frontend/
│   ├── index_refactored.html    # 메인 페이지
│   └── data/
│       ├── subway_lines.json    # 지하철 정보
│       └── config.json          # 설정
├── swimming_pools.db            # SQLite DB
├── advanced_pools.json          # 크롤링 결과
└── load_data_to_db.py           # DB 로더
```

---

## 🔧 문제 해결

### 1. 수영장 마커가 안 보여요
**원인**: 서버가 실행되지 않음
```bash
# 서버 실행 확인
curl http://localhost:8000/health

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 지도가 안 나와요
**원인**: 카카오맵 API 키 오류
```json
// frontend/data/config.json 확인
{
  "kakaoMapKey": "발급받은_JavaScript_키"
}
```

### 3. 크롤러 실행 시 에러
**"No module named 'anthropic'"**
```bash
pip install anthropic
```

**"API 호출 실패"**
- 네이버 API 키 확인: `crawler/advanced_crawler.py:16-17`
- API 일일 호출 제한 확인

### 4. DB에 데이터가 없어요
```bash
# 크롤링 실행
python crawler/advanced_crawler.py

# DB 저장
python load_data_to_db.py advanced_pools.json
```

### 5. 지하철역이 안 나와요
**파일 확인**: `frontend/data/subway_lines.json` 존재 여부

---

## 📚 추가 자료

### 프로젝트 구조
```
korea_swim/
├── app/                              # FastAPI 백엔드
│   ├── main.py                       # 서버 엔트리포인트
│   ├── models/swimming_pool.py       # SQLAlchemy 모델
│   ├── schemas/swimming_pool.py      # Pydantic 스키마
│   ├── crud/swimming_pool.py         # DB CRUD 함수
│   └── api/pools.py                  # API 라우터
├── crawler/
│   ├── advanced_crawler.py           # 진짜 크롤러 (네이버 검색)
│   └── pools_data.json               # (사용 안함)
├── database/
│   └── connection.py                 # DB 연결 설정
├── frontend/
│   ├── index_refactored.html         # ⭐ 메인 페이지
│   └── data/
│       ├── config.json               # 카카오맵 API 키
│       └── subway_lines.json         # 지하철 정보
├── swimming_pools.db                 # SQLite 데이터베이스
├── advanced_pools.json               # 크롤링 결과
├── load_data_to_db.py                # DB 로더
└── CLAUDE.md                         # 이 문서
```

### 데이터 흐름
```
[네이버 API]
    ↓ (검색)
[advanced_crawler.py] → advanced_pools.json
    ↓ (저장)
[load_data_to_db.py] → swimming_pools.db
    ↓ (조회)
[FastAPI /api/pools] → JSON 응답
    ↓ (표시)
[Frontend HTML] → 지도에 마커 표시
```

### 주요 파일 설명

| 파일 | 역할 | 수정 필요? |
|------|------|-----------|
| `frontend/index_refactored.html` | 메인 페이지 | ❌ |
| `frontend/data/config.json` | 카카오맵 API 키 | ✅ 발급 후 입력 |
| `crawler/advanced_crawler.py` | 수영장 크롤링 | ⚠️ 네이버 API 키 |
| `app/main.py` | FastAPI 서버 | ❌ |
| `swimming_pools.db` | 수영장 DB | 🔄 자동 생성 |

---

## 🎓 개발 히스토리

### 완료된 작업
- ✅ 네이버 지역 검색 API로 실제 수영장 크롤링
- ✅ 다양한 수영장 유형 수집 (공공, 민간, 호텔 등)
- ✅ Claude AI 이미지 분석 기능 추가
- ✅ 중복 제거 및 Upsert 로직 구현
- ✅ 지하철역 기반 검색 기능
- ✅ 카카오맵 통합 및 마커 표시
- ✅ 필터링 및 정렬 기능

### 데이터 현황
- **총 수영장**: 83개
  - 공공 수영장: 47개 (구민체육센터 등)
  - 민간 수영장: 36개 (실제 크롤링)
- **이미지**: 30개 수영장에 이미지 포함

### 향후 개선 가능 사항
- [ ] 공공데이터 포털 API 추가
- [ ] 실시간 수영장 혼잡도
- [ ] 사용자 리뷰 기능
- [ ] 모바일 최적화
- [ ] 회원권/강습 가격 정보
- [ ] 예약 기능 연동
