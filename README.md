# 🏊 한국 수영장 찾기 (Korea Swim Finder)

서울시 수영장 정보를 검색하고 지도에서 확인할 수 있는 웹 애플리케이션입니다.

## 🚀 주요 기능

- 🗺️ **카카오 지도 기반** 수영장 위치 표시
- 🔍 **반경 검색**: 현재 위치 또는 특정 지점 기준 근처 수영장 찾기
- 💰 **가격 필터링**: 일일권 가격으로 필터링
- 🏊‍♂️ **자유 수영 시간** 확인
- 📊 **245개 이상**의 서울시 수영장 정보

## 🛠️ 기술 스택

### Backend
- **FastAPI**: Python 웹 프레임워크
- **SQLAlchemy**: ORM
- **SQLite**: 데이터베이스
- **Uvicorn**: ASGI 서버

### Frontend
- **Vanilla JavaScript**
- **Kakao Maps API**: 지도 표시
- **Responsive Design**

### Crawler
- **Naver Local Search API**: 수영장 정보 수집
- **Naver Image Search API**: 이미지 수집
- **Claude AI (선택)**: 이미지 검증
- **Seoul Open Data Portal (선택)**: 공공 체육시설 정보

## 📦 설치 및 실행

### 로컬 환경

1. **저장소 클론**
```bash
git clone https://github.com/yourusername/korea_swim.git
cd korea_swim
```

2. **패키지 설치**
```bash
pip install -r requirements.txt
```

3. **데이터베이스 초기화**
```bash
python load_data_to_db.py swimming_pools.json
```

4. **서버 실행**
```bash
uvicorn app.main:app --reload
```

5. **브라우저에서 접속**
```
http://localhost:8000
```

### 서버 없이 실행 (프론트엔드만)
```bash
# frontend/index_refactored.html 파일을 브라우저로 열기
```

## 🌐 배포 (Render)

### 1단계: GitHub 레포지토리 생성

1. GitHub에서 새 레포지토리 생성
2. 로컬 코드 푸시:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/korea_swim.git
git push -u origin main
```

### 2단계: Render 배포

1. [Render](https://render.com) 가입/로그인
2. **New +** 버튼 클릭 → **Web Service** 선택
3. GitHub 레포지토리 연결
4. 설정:
   - **Name**: korea-swim
   - **Region**: Singapore (가장 가까운 지역)
   - **Branch**: main
   - **Build Command**: `pip install -r requirements.txt && python load_data_to_db.py swimming_pools.json`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. **Create Web Service** 클릭

### 3단계: 배포 완료

5-10분 후 배포 완료. URL은 다음과 같은 형식:
```
https://korea-swim.onrender.com
```

## 🔑 API 키 설정

### 필수: Kakao Map API
1. [Kakao Developers](https://developers.kakao.com/) 가입
2. 애플리케이션 생성 후 JavaScript 키 발급
3. `frontend/data/config.json`에 API 키 입력

### 선택: 크롤러 API 키
크롤러를 실행하려면 추가 API 키 필요:

- **Naver API**: `crawler/advanced_crawler.py`에 클라이언트 ID/Secret 입력
- **Claude AI**: 환경변수 `ANTHROPIC_API_KEY` 설정
- **Seoul Data Portal**: 환경변수 `SEOUL_DATA_API_KEY` 설정

## 📊 데이터 수집 (크롤링)

```bash
# 수영장 데이터 크롤링
python crawler/advanced_crawler.py

# DB에 로드
python load_data_to_db.py advanced_pools.json
```

## 📁 프로젝트 구조

```
korea_swim/
├── app/
│   ├── api/          # API 엔드포인트
│   ├── crud/         # DB 작업
│   ├── models/       # DB 모델
│   ├── schemas/      # Pydantic 스키마
│   └── main.py       # FastAPI 앱
├── crawler/          # 수영장 데이터 크롤러
├── database/         # DB 설정
├── frontend/         # 프론트엔드 파일
│   ├── data/         # 정적 데이터 (지하철, 설정)
│   └── index_refactored.html
├── requirements.txt  # Python 패키지
├── render.yaml       # Render 배포 설정
└── README.md
```

## 🤝 기여

이슈와 PR은 언제나 환영합니다!

## 📝 라이선스

MIT License

## 👨‍💻 개발자

개발 문의: [이메일 주소]
