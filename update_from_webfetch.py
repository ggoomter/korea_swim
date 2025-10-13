# -*- coding: utf-8 -*-
"""
WebFetch 결과를 데이터베이스에 자동 업데이트하는 스크립트
"""
import sys
sys.path.insert(0, '.')

from database.connection import get_db
from app.models.swimming_pool import SwimmingPool

# WebFetch로 성공적으로 추출한 가격 정보
WEBFETCH_RESULTS = {
    # ID 3: 강동구민회관 수영장
    3: {
        "monthly_lesson_price": "모닝수영 38,500~55,000원 (시간대별), 남여수영 55,000원",
        "free_swim_price": "프로그램별 상이"
    },

    # ID 6: 강서구민체육센터
    6: {
        "monthly_lesson_price": "월정기권 30,000~56,000원, 일반수영 46,200원",
        "free_swim_price": "41,700~180,000원"
    },

    # ID 7: 관악구민체육센터
    7: {
        "free_swim_price": "일일입장 3,400원 (2시간)"
    },

    # ID 8: 광진구민체육센터
    8: {
        "free_swim_price": "성인 3,500원, 청소년 2,500원, 어린이 2,000원"
    },

    # ID 12: 도봉구민회관 수영장
    12: {
        "monthly_lesson_price": "새벽수영: 성인 주3회 48,400원, 주2회 32,300원"
    },

    # ID 17: 서초구민체육센터
    17: {
        "monthly_lesson_price": "유아 31,000원, 성인 43,000~76,000원, 소그룹 160,000원"
    },

    # ID 21: 잠실학생체육관
    21: {
        "monthly_lesson_price": "수영 24,000~60,000원, 아쿠아로빅 50,000~85,000원"
    },

    # ID 22: 올림픽공원 수영장
    22: {
        "monthly_lesson_price": "성인수영 59,000~90,000원, 어린이 40,000~50,000원",
        "free_swim_price": "55,000~70,000원"
    },

    # ID 30: 부산시민수영장 (사직실내수영장)
    30: {
        "monthly_lesson_price": "1개월 60,000원, 3개월 160,000원"
    },

    # ID 34: 인천도원수영장
    34: {
        "monthly_lesson_price": "1개월권 46,000원",
        "free_swim_price": "1일권 4,000원"
    },

    # ID 90: 고덕어울림수영장
    90: {
        "free_swim_price": "10분당 1,100원 (2025년 8월 현재 리노베이션 중)"
    },

    # ID 96: 강북문화예술회관수영장
    96: {
        "monthly_lesson_price": "성인 34,000~49,000원, 어린이 21,000~32,000원",
        "free_swim_price": "일일권 2,000~4,800원, 월정기권 28,000~35,000원"
    },

    # ID 102: 창동문화체육센터수영장
    102: {
        "monthly_lesson_price": "성인 주3회 48,400원, 주2회 35,000원"
    },

    # ID 110: 삼모스포렉스
    110: {
        "monthly_lesson_price": "주3회 190,000~280,000원, 시간대별 135,000~235,000원"
    }
}

def update_database():
    """WebFetch 결과로 데이터베이스 업데이트"""
    db = next(get_db())

    print("\n" + "="*70)
    print("  WebFetch 결과 데이터베이스 업데이트")
    print("="*70 + "\n")

    updated_count = 0

    for pool_id, prices in WEBFETCH_RESULTS.items():
        pool = db.query(SwimmingPool).filter(SwimmingPool.id == pool_id).first()

        if pool:
            if prices.get("monthly_lesson_price"):
                pool.monthly_lesson_price = prices["monthly_lesson_price"]
            if prices.get("free_swim_price"):
                pool.free_swim_price = prices["free_swim_price"]

            updated_count += 1
            print(f"[OK] ID {pool_id}: {pool.name}")
            print(f"     한달 수강권: {pool.monthly_lesson_price}")
            print(f"     자유수영: {pool.free_swim_price}\n")

    db.commit()

    print(f"{'='*70}")
    print(f"  [완료] {updated_count}개 수영장 가격 정보 업데이트")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    update_database()
