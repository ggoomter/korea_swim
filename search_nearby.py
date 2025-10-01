# -*- coding: utf-8 -*-
"""
집 근처 수영장 검색 테스트
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json

BASE_URL = "http://localhost:8000"

def search_nearby_pools(lat, lng, radius_km=5.0, location_name=""):
    """
    위치 기반 수영장 검색
    """
    print("="*70)
    print(f"🔍 {location_name} 근처 수영장 검색")
    print(f"   위치: ({lat}, {lng})")
    print(f"   반경: {radius_km}km")
    print("="*70)

    search_data = {
        "lat": lat,
        "lng": lng,
        "radius_km": radius_km,
        "has_free_swim": True
    }

    try:
        response = requests.post(f"{BASE_URL}/pools/search", json=search_data)
        response.raise_for_status()
        results = response.json()

        if not results:
            print(f"\n❌ {radius_km}km 반경 내에 수영장이 없습니다.")
            return

        print(f"\n✅ {len(results)}개 수영장 발견!\n")

        for i, pool in enumerate(results, 1):
            print(f"{i}. {pool['name']}")
            print(f"   📍 주소: {pool['address']}")

            if pool.get('phone'):
                print(f"   📞 전화: {pool['phone']}")

            if pool.get('daily_price'):
                print(f"   💰 1회 이용: {pool['daily_price']:,}원")

            if pool.get('free_swim_price'):
                print(f"   🏊 자율수영: {pool['free_swim_price']:,}원")

            if pool.get('facilities'):
                facilities_str = ', '.join(pool['facilities'])
                print(f"   🏢 시설: {facilities_str}")

            if pool.get('rating'):
                print(f"   ⭐ 평점: {pool['rating']}")

            # 운영시간
            if pool.get('operating_hours'):
                hours = pool['operating_hours']
                if isinstance(hours, dict):
                    hours_str = ', '.join([f"{k}: {v}" for k, v in list(hours.items())[:2]])
                    print(f"   🕐 운영시간: {hours_str}")

            print()

    except requests.exceptions.ConnectionError:
        print("❌ 서버가 실행되지 않았습니다.")
        print("서버 실행: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ 오류: {e}")

def main():
    """
    주요 지역별 수영장 검색
    """
    print("\n" + "="*70)
    print("🏊 한국 수영장 검색 시스템")
    print("="*70 + "\n")

    # 주요 지역 좌표
    locations = [
        {"name": "강남역", "lat": 37.4979, "lng": 127.0276},
        {"name": "잠실", "lat": 37.5133, "lng": 127.1000},
        {"name": "홍대", "lat": 37.5563, "lng": 126.9240},
        {"name": "수원역", "lat": 37.2663, "lng": 127.0016},
    ]

    for loc in locations:
        search_nearby_pools(
            lat=loc['lat'],
            lng=loc['lng'],
            radius_km=5.0,
            location_name=loc['name']
        )
        print("\n" + "-"*70 + "\n")

    # 사용자 정의 검색 예제
    print("\n💡 사용법:")
    print("   1. Google Maps에서 집 주소 검색")
    print("   2. 우클릭 -> 좌표 복사")
    print("   3. 이 스크립트에서 lat, lng에 입력")
    print("\n   예시:")
    print("   search_nearby_pools(lat=37.5012, lng=127.0396, location_name='우리집')")

if __name__ == "__main__":
    main()
