# -*- coding: utf-8 -*-
"""
웹 검색 결과를 기반으로 수영장 가격 업데이트
"""
import sys
sys.path.insert(0, '.')

from database.connection import get_db
from app.models.swimming_pool import SwimmingPool

# 웹 검색으로 찾은 정보
PRICE_UPDATES = {
    # 서울 한강 수영장 표준 요금 (2025)
    "한강수영장_표준": {
        "free_swim_price": "성인 5000원, 청소년 4000원, 어린이 3000원"
    },

    # 강동유소년스포츠센터 (검색 결과 참고)
    "강동유소년스포츠센터": {
        "free_swim_price": "성인 4400원, 청소년 3500원, 어린이 3000원"
    },

    # 서울시 공공 체육시설 표준 (추정)
    "구민체육센터_표준": {
        "monthly_lesson_price": "성인 60000~80000원 (월~금 주5회)",
        "free_swim_price": "성인 3500~5000원"
    },

    # 천호어울림수영장 (2025년 신규 개장)
    "천호어울림수영장": {
        "monthly_lesson_price": "미공개 (2025년 초 개장 예정)",
        "free_swim_price": "미공개"
    }
}

def update_pool_prices():
    db = next(get_db())

    print("\n" + "="*70)
    print("  웹 검색 기반 가격 정보 업데이트")
    print("="*70 + "\n")

    updated_count = 0

    # 1. 공공 체육시설은 표준 요금 적용
    public_pools = db.query(SwimmingPool).filter(
        SwimmingPool.source.like("%공공%") |
        SwimmingPool.source.like("%구청%") |
        SwimmingPool.name.like("%구민체육센터%")
    ).all()

    print(f"[공공체육시설] {len(public_pools)}개")
    for pool in public_pools:
        # 현재 가격이 너무 낮으면 (3500원 이하) 업데이트
        try:
            current_price = int(pool.monthly_lesson_price) if pool.monthly_lesson_price else 0
            if current_price <= 3500:
                pool.monthly_lesson_price = "월 6만~8만원 (주5회 기준, 시설별 상이)"
                updated_count += 1
                print(f"  [OK] {pool.name}: 수강권 가격 업데이트")
        except ValueError:
            pass

        try:
            current_swim_price = int(pool.free_swim_price) if pool.free_swim_price else 0
            if current_swim_price <= 3500:
                pool.free_swim_price = "3500~5000원 (연령별 상이)"
                updated_count += 1
                print(f"  [OK] {pool.name}: 자유수영 가격 업데이트")
        except ValueError:
            pass

    # 2. 특정 수영장 개별 업데이트
    # 강동유소년스포츠센터
    pool = db.query(SwimmingPool).filter(
        SwimmingPool.name.like("%강동유소년%")
    ).first()
    if pool:
        pool.free_swim_price = "성인 4400원, 청소년 3500원, 어린이 3000원"
        updated_count += 1
        print(f"\n  [OK] {pool.name}: 자유수영 가격 업데이트 (검색 결과 반영)")

    # 천호어울림수영장
    pool = db.query(SwimmingPool).filter(
        SwimmingPool.name.like("%천호%어울림%") |
        SwimmingPool.name.like("%천호체육관%")
    ).first()
    if pool:
        pool.monthly_lesson_price = "미공개 (2025년 초 개장 예정)"
        pool.free_swim_price = "미공개 (2025년 초 개장 예정)"
        updated_count += 1
        print(f"\n  [OK] {pool.name}: 가격 정보 업데이트 (신규 개장 시설)")

    # 한강 수영장들
    hangang_pools = db.query(SwimmingPool).filter(
        SwimmingPool.name.like("%한강%")
    ).all()
    for pool in hangang_pools:
        pool.free_swim_price = "성인 5000원, 청소년 4000원, 어린이 3000원 (2025 기준)"
        updated_count += 1
        print(f"  [OK] {pool.name}: 자유수영 가격 업데이트")

    db.commit()

    print(f"\n{'='*70}")
    print(f"  [완료] {updated_count}개 수영장 가격 정보 업데이트 완료")
    print(f"{'='*70}\n")

    print("[업데이트 요약]")
    print("  - 공공 체육시설: 표준 요금으로 업데이트")
    print("  - 한강 수영장: 2025년 공식 요금 반영")
    print("  - 특정 시설: 웹 검색 결과 직접 반영")
    print("\n[참고] 정확한 가격은 각 시설에 직접 문의 권장")

if __name__ == "__main__":
    update_pool_prices()
