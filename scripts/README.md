# 포트폴리오 스크린샷 촬영 가이드

## 개요

화면이나 기능이 변경되면 포트폴리오 스크린샷을 다시 촬영해야 합니다.
korea_swim은 공개 사이트이므로 로그인 없이 촬영 가능합니다.

---

## 촬영 방법

### hellgater 디렉토리에서 실행 (Playwright 설치됨)

```bash
cd C:\Users\ggoom\OneDrive\문서\hellgater
npx tsx scripts/capture-korea-swim.ts
```

### 결과물 위치

```
korea_swim/screenshots/
├── pc/
│   ├── 01_main_map.png      # 메인 지도 화면
│   ├── 02_map_loaded.png    # 지도 로드 완료
│   └── 03_filter_active.png # 필터 활성화 (있는 경우)
└── mobile/
    ├── 01_main_map.png
    └── 02_map_loaded.png
```

---

## 뷰포트 설정

| 플랫폼 | 너비 | 높이 | deviceScaleFactor |
|--------|------|------|-------------------|
| PC | 1440px | 900px | 1x |
| Mobile | 430px | 932px | 2x (Retina) |

---

## 촬영 스크립트 위치

```
hellgater/scripts/capture-korea-swim.ts
```

---

## 주의사항

- Render 무료 플랜 사용 중이라 서버가 자주 잠듭니다
- 촬영 전 https://korea-swim.onrender.com 에 한 번 접속하여 서버를 깨우세요
- 스크립트는 90초 타임아웃으로 설정되어 있습니다

---

## README 업데이트

스크린샷 촬영 후 README.md에서 이미지 경로 확인:

```markdown
<img src="screenshots/pc/01_main_map.png" alt="메인 지도 화면" width="80%">
```
