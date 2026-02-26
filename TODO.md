# korea_swim 프로젝트 TODO

## 현재 상태 (2026-02-26)

### 브랜치
- `main`: feature/overhaul-upgrade 병합 완료
- `origin/feature/overhaul-upgrade-*`: 병합됨 (삭제 가능)

### DB (swimming_pools.db) - 352건

| 필드 | 채워진 건수 | 비율 | 비고 |
|------|-----------|------|------|
| daily_price | 76 | 21% | 실제 다양한 값 (3,400~50,000원) |
| free_swim_price | 76 | 21% | |
| monthly_lesson_price | 30 | 8% | |
| operating_hours | 1 | 0% | 거의 없음 |
| free_swim_times | 44 | 12% | |
| phone | 47 | 13% | |
| image_url | 294 | 83% | 일부 만료 URL 포함 |
| facilities | 315 | 89% | |

### JSON 파일

| 파일 | 건수 | 상태 |
|------|------|------|
| advanced_pools.json | 256건 | 이름/주소/이미지만 있음, 가격/운영시간 전무, 비수영 데이터 10건 혼재 |
| final_pools.json | 183건 | **더미 데이터** (전부 동일값: 10000원, 06:00-22:00) - 사용 불가 |

### 소스 분포 (DB)
- 네이버 검색: 305건
- 서울시공공서비스: 29건
- 인공지능: 9건
- 공공데이터: 8건
- 테스트: 1건

---

## Phase 1: 데이터 정리 (최우선)

### 1-1. 비수영 데이터 제거
- [ ] DB에서 수영장 무관 데이터 식별 및 제거 (찜질방, 야구장, 카페, 음식점 등)
- [ ] advanced_pools.json에서도 동일 정리
- [ ] final_pools.json 삭제 또는 용도 재정의 (현재 더미 데이터)

### 1-2. 데이터 보강 - 가격/운영시간 크롤링
- [ ] 네이버 플레이스에서 실제 가격 크롤링 (현재 21%만 있음)
- [ ] 운영시간 크롤링 (현재 거의 0%)
- [ ] 자유수영 시간표 수집
- [ ] 전화번호 수집

### 1-3. 데이터 품질 검증
- [ ] 중복 수영장 제거 (이름+주소 기준)
- [ ] 좌표 검증 (서울 범위 내인지)
- [ ] 이미지 URL 유효성 검사 (만료된 URL 제거)
- [ ] DB ↔ JSON 데이터 동기화 정책 결정

---

## Phase 2: 보안 수정

### 2-1. API 키 하드코딩 제거
- [ ] `crawler/advanced_crawler.py:16-17` 네이버 API 키 → 환경변수
- [ ] `crawler/naver_place_crawler.py` 동일
- [ ] `crawler/price_crawler.py` 동일
- [ ] CLAUDE.md에서 API 키 노출 부분 제거

### 2-2. 서버 보안
- [ ] CORS `allow_origins=["*"]` → 배포 도메인만 허용
- [ ] `allow_credentials=True` 제거 (또는 origins 특정)
- [ ] POST `/api/pools/` 인증 추가 (또는 비활성화)
- [ ] 전역 에러 핸들러 추가 (스택 트레이스 노출 방지)

---

## Phase 3: 배포 (Fly.io)

hellgater 프로젝트의 release 브랜치 패턴 참고:
- GitHub Actions → release 브랜치 push 시 Fly.io 자동 배포

### 3-1. 인프라 설정
- [ ] Dockerfile 작성 (python-slim 기반)
- [ ] fly.toml 작성 (nrt 리전)
- [ ] SQLite → PostgreSQL 전환 검토 (Fly.io 디스크 휘발 문제)
  - 대안: SQLite + Fly.io Volume 마운트
- [ ] `.github/workflows/deploy-release.yml` 작성

### 3-2. 프론트엔드
- [ ] FastAPI에서 정적 파일 서빙 (별도 컨테이너 불필요)
- [ ] 빌드 시 DB 초기화 스크립트 포함

---

## Phase 4: 품질 개선

### 4-1. 테스트
- [ ] pytest 설정 (pyproject.toml)
- [ ] API 엔드포인트 테스트
- [ ] 데이터 로딩 테스트

### 4-2. 로깅/모니터링
- [ ] Python logging 설정
- [ ] 에러 알림

### 4-3. UI/UX
- [ ] `alert()` → 토스트 알림
- [ ] 로딩 스피너 개선
- [ ] 480px 이하 모바일 대응

---

## 불필요 파일 정리 대상
- `check_sillim_detail.py` (untracked, 테스트용)
- `find_example.py` (untracked, 테스트용)
- `test_sillim.py` (untracked, 테스트용)
- `final_pools.json` (더미 데이터)
- `changes.diff` (feature 브랜치에서 삭제됨)
