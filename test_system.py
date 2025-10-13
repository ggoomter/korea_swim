# -*- coding: utf-8 -*-
"""
시스템 테스트 스크립트
"""
import requests
import json
import sys
import io

# Windows 콘솔 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE_URL = "http://localhost:8000"
API_PREFIX = "/api"

def test_health():
    """헬스체크"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"✅ Health Check: {response.json()}")

def test_add_sample_pool():
    """샘플 수영장 추가"""
    pool_data = {
        "name": "강남 수영장",
        "address": "서울특별시 강남구 테헤란로 123",
        "lat": 37.5012,
        "lng": 127.0396,
        "phone": "02-1234-5678",
        "operating_hours": {
            "mon": "06:00-22:00",
            "tue": "06:00-22:00",
            "wed": "06:00-22:00",
            "thu": "06:00-22:00",
            "fri": "06:00-22:00",
            "sat": "08:00-20:00",
            "sun": "08:00-20:00"
        },
        "lanes": 8,
        "pool_size": "25m x 15m",
        "water_temp": "28도",
        "facilities": ["사우나", "주차장", "락커룸", "샤워실"],
        "membership_prices": {
            "1month": 150000,
            "3month": 400000,
            "6month": 750000,
            "1year": 1400000
        },
        "daily_price": 10000,
        "free_swim_times": {
            "mon": ["06:00-08:00", "20:00-22:00"],
            "tue": ["06:00-08:00", "20:00-22:00"],
            "wed": ["06:00-08:00", "20:00-22:00"],
            "thu": ["06:00-08:00", "20:00-22:00"],
            "fri": ["06:00-08:00", "20:00-22:00"],
            "sat": ["08:00-12:00", "16:00-20:00"],
            "sun": ["08:00-12:00", "16:00-20:00"]
        },
        "free_swim_price": 8000,
        "lessons": [
            {"type": "초급", "price": 200000, "schedule": "월수금 19:00"},
            {"type": "중급", "price": 250000, "schedule": "화목 19:00"},
            {"type": "상급", "price": 300000, "schedule": "월수금 20:00"}
        ],
        "source": "테스트",
        "url": "https://example.com",
        "rating": 4.5
    }

    response = requests.post(f"{BASE_URL}{API_PREFIX}/pools/", json=pool_data)
    print(f"✅ 샘플 수영장 추가: {response.json()['name']}")
    return response.json()

def test_search_nearby(lat: float, lng: float, radius_km: float = 5.0):
    """위치 기반 검색"""
    search_data = {
        "lat": lat,
        "lng": lng,
        "radius_km": radius_km,
        "has_free_swim": True
    }

    response = requests.post(f"{BASE_URL}{API_PREFIX}/pools/search", json=search_data)
    results = response.json()

    print(f"\n🔍 검색 결과 ({len(results)}개):")
    for pool in results:
        distance = pool.get('distance')
        print(f"  - {pool['name']}: {pool['address']}")
        if distance is not None:
            print(f"    거리: {distance:.2f}km")
        if pool.get('free_swim_price'):
            print(f"    자율수영: {pool['free_swim_price']:,}원")


def test_search_nearby_get(lat: float, lng: float, radius_km: float = 5.0):
    """쿼리 파라미터 기반 위치 검색"""
    params = {
        "lat": lat,
        "lng": lng,
        "radius": radius_km,
        "has_free_swim": True
    }

    response = requests.get(f"{BASE_URL}{API_PREFIX}/pools/nearby", params=params)
    results = response.json()

    print(f"\n🌐 GET 검색 결과 ({len(results)}개):")
    for pool in results[:5]:
        distance = pool.get('distance')
        if distance is not None:
            print(f"  - {pool['name']} ({distance:.2f}km)")
        else:
            print(f"  - {pool['name']}")

def test_get_all_pools():
    """전체 수영장 조회"""
    response = requests.get(f"{BASE_URL}{API_PREFIX}/pools/")
    pools = response.json()
    print(f"\n📋 전체 수영장: {len(pools)}개")
    return pools

if __name__ == "__main__":
    print("=== 시스템 테스트 시작 ===\n")

    try:
        # 1. 헬스체크
        test_health()

        # 2. 샘플 데이터 추가
        print("\n--- 샘플 데이터 추가 ---")
        sample_pool = test_add_sample_pool()

        # 3. 전체 조회
        print("\n--- 전체 수영장 조회 ---")
        test_get_all_pools()

        # 4. 위치 기반 검색 (강남역 기준)
        print("\n--- 위치 기반 검색 (강남역 근처 5km) ---")
        test_search_nearby(37.4979, 127.0276, radius_km=5.0)
        test_search_nearby_get(37.4979, 127.0276, radius_km=5.0)

        print("\n✅ 모든 테스트 완료!")

    except requests.exceptions.ConnectionError:
        print("❌ 서버가 실행되지 않았습니다.")
        print("다음 명령으로 서버를 실행하세요:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ 테스트 오류: {e}")
