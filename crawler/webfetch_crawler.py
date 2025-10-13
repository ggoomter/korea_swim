# -*- coding: utf-8 -*-
"""
WebFetch 기반 크롤러 - 실제 페이지 내용을 읽어서 가격 추출
WebSearch (링크만) → WebFetch (내용 읽기) → 가격 추출
"""
import sys
sys.path.insert(0, '.')

from database.connection import get_db
from app.models.swimming_pool import SwimmingPool
import json

# 수동으로 WebFetch 결과를 입력받아 DB 업데이트
# (Claude Code는 도구를 스크립트에서 직접 호출 불가)

MANUAL_UPDATES = {
    "강남스포츠문화센터 수영장": {
        "url": "https://life.gangnam.go.kr/fmcs/341",
        "monthly_lesson_price": "프로그램별 상이 (4만~8만원)",
        "free_swim_price": "시간대별 일일입장 (실버 3만~4만원/월)",
        "note": "평일 12:30~17:20, 토일 06:30~17:20, 자세한 시간표는 홈페이지 참조"
    },
    # 여기에 WebFetch로 찾은 다른 수영장 추가
}

def update_from_manual_data():
    """수동으로 수집한 데이터로 DB 업데이트"""
    db = next(get_db())

    print("\n" + "="*70)
    print("  WebFetch 기반 수동 업데이트")
    print("="*70 + "\n")

    updated = 0

    for pool_name, data in MANUAL_UPDATES.items():
        pool = db.query(SwimmingPool).filter(
            SwimmingPool.name.like(f"%{pool_name}%")
        ).first()

        if pool:
            if data.get("monthly_lesson_price"):
                pool.monthly_lesson_price = data["monthly_lesson_price"]
            if data.get("free_swim_price"):
                pool.free_swim_price = data["free_swim_price"]
            if data.get("url"):
                pool.url = data["url"]

            updated += 1
            print(f"[OK] {pool.name}")
            print(f"     수강권: {pool.monthly_lesson_price}")
            print(f"     자유수영: {pool.free_swim_price}\n")

    db.commit()

    print(f"{'='*70}")
    print(f"  [완료] {updated}개 수영장 업데이트")
    print(f"{'='*70}")

if __name__ == "__main__":
    update_from_manual_data()
