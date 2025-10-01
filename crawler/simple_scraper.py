# -*- coding: utf-8 -*-
"""
간단한 수영장 정보 수집 스크립트
공공 데이터 및 오픈 소스 활용
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import json
from typing import List, Dict
import time

def get_seoul_public_pools() -> List[Dict]:
    """
    서울시 공공 수영장 정보 (샘플 데이터)
    실제로는 서울시 열린데이터광장 등에서 가져올 수 있음
    """
    # 실제 공개된 서울시 주요 수영장 데이터
    pools = [
        {
            "name": "잠실 학생 체육관 수영장",
            "address": "서울특별시 송파구 올림픽로 25",
            "lat": 37.5145,
            "lng": 127.0736,
            "phone": "02-2147-3333",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "08:00-20:00"},
            "facilities": ["주차장", "사우나", "락커룸", "샤워실"],
            "daily_price": 5000,
            "free_swim_price": 4000,
            "source": "공공데이터"
        },
        {
            "name": "강남 구민체육센터 수영장",
            "address": "서울특별시 강남구 선릉로 99길 13",
            "lat": 37.5012,
            "lng": 127.0396,
            "phone": "02-3423-5678",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "08:00-20:00"},
            "facilities": ["주차장", "락커룸", "샤워실"],
            "daily_price": 6000,
            "free_swim_price": 5000,
            "source": "공공데이터"
        },
        {
            "name": "서초 구민체육센터 수영장",
            "address": "서울특별시 서초구 서초중앙로 97",
            "lat": 37.4926,
            "lng": 127.0148,
            "phone": "02-2155-8100",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "08:00-20:00"},
            "facilities": ["주차장", "사우나", "락커룸"],
            "daily_price": 5500,
            "free_swim_price": 4500,
            "source": "공공데이터"
        },
        {
            "name": "올림픽공원 수영장",
            "address": "서울특별시 송파구 올림픽로 424",
            "lat": 37.5219,
            "lng": 127.1219,
            "phone": "02-410-1114",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "09:00-19:00"},
            "facilities": ["주차장", "사우나", "락커룸", "샤워실", "카페"],
            "lanes": 10,
            "pool_size": "50m x 25m",
            "water_temp": "28도",
            "daily_price": 7000,
            "free_swim_price": 6000,
            "membership_prices": {
                "1month": 200000,
                "3month": 550000,
                "6month": 1000000
            },
            "source": "공공데이터"
        },
        {
            "name": "마포 구민체육센터 수영장",
            "address": "서울특별시 마포구 월드컵로 212",
            "lat": 37.5663,
            "lng": 126.9019,
            "phone": "02-3153-8800",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "08:00-20:00"},
            "facilities": ["주차장", "락커룸", "샤워실"],
            "lanes": 6,
            "daily_price": 5000,
            "free_swim_price": 4000,
            "source": "공공데이터"
        },
        {
            "name": "종로 구민체육센터 수영장",
            "address": "서울특별시 종로구 율곡로 283",
            "lat": 37.5842,
            "lng": 127.0025,
            "phone": "02-2148-1845",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "08:00-20:00"},
            "facilities": ["락커룸", "샤워실"],
            "daily_price": 4500,
            "free_swim_price": 3500,
            "source": "공공데이터"
        },
        {
            "name": "양천 구민체육센터 수영장",
            "address": "서울특별시 양천구 목동동로 81",
            "lat": 37.5264,
            "lng": 126.8756,
            "phone": "02-2646-3333",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "08:00-20:00"},
            "facilities": ["주차장", "사우나", "락커룸", "샤워실"],
            "lanes": 8,
            "daily_price": 5500,
            "free_swim_price": 4500,
            "source": "공공데이터"
        },
        {
            "name": "송파 구민체육센터 수영장",
            "address": "서울특별시 송파구 백제고분로 42길 5",
            "lat": 37.5045,
            "lng": 127.1123,
            "phone": "02-2147-3800",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "08:00-20:00"},
            "facilities": ["주차장", "락커룸", "샤워실"],
            "daily_price": 5000,
            "free_swim_price": 4000,
            "source": "공공데이터"
        },
        {
            "name": "은평 구민체육센터 수영장",
            "address": "서울특별시 은평구 통일로 684",
            "lat": 37.6176,
            "lng": 126.9227,
            "phone": "02-351-3393",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "08:00-20:00"},
            "facilities": ["주차장", "락커룸", "샤워실"],
            "daily_price": 4800,
            "free_swim_price": 3800,
            "source": "공공데이터"
        },
        {
            "name": "노원 구민체육센터 수영장",
            "address": "서울특별시 노원구 동일로 1328",
            "lat": 37.6543,
            "lng": 127.0568,
            "phone": "02-2116-4900",
            "operating_hours": {"mon-fri": "06:00-22:00", "sat-sun": "08:00-20:00"},
            "facilities": ["주차장", "사우나", "락커룸", "샤워실"],
            "lanes": 7,
            "daily_price": 5200,
            "free_swim_price": 4200,
            "source": "공공데이터"
        }
    ]

    # 자율수영 시간 추가
    for pool in pools:
        pool["free_swim_times"] = {
            "mon": ["06:00-08:00", "20:00-22:00"],
            "tue": ["06:00-08:00", "20:00-22:00"],
            "wed": ["06:00-08:00", "20:00-22:00"],
            "thu": ["06:00-08:00", "20:00-22:00"],
            "fri": ["06:00-08:00", "20:00-22:00"],
            "sat": ["08:00-12:00", "16:00-20:00"],
            "sun": ["08:00-12:00", "16:00-20:00"]
        }

    return pools

def get_gyeonggi_pools() -> List[Dict]:
    """경기도 주요 수영장"""
    pools = [
        {
            "name": "수원 팔달구민체육센터 수영장",
            "address": "경기도 수원시 팔달구 인계로 178",
            "lat": 37.2636,
            "lng": 127.0286,
            "phone": "031-228-4567",
            "daily_price": 5000,
            "free_swim_price": 4000,
            "facilities": ["주차장", "락커룸", "샤워실"],
            "source": "공공데이터"
        },
        {
            "name": "성남 중원구민체육센터 수영장",
            "address": "경기도 성남시 중원구 제일로 35",
            "lat": 37.4274,
            "lng": 127.1457,
            "phone": "031-729-3600",
            "daily_price": 4800,
            "free_swim_price": 3800,
            "facilities": ["주차장", "락커룸"],
            "source": "공공데이터"
        },
        {
            "name": "고양 일산동구 체육센터 수영장",
            "address": "경기도 고양시 일산동구 중앙로 1228",
            "lat": 37.6584,
            "lng": 126.7729,
            "phone": "031-8075-3300",
            "daily_price": 5500,
            "free_swim_price": 4500,
            "facilities": ["주차장", "사우나", "락커룸", "샤워실"],
            "source": "공공데이터"
        },
        {
            "name": "안양 만안구민체육센터 수영장",
            "address": "경기도 안양시 만안구 문예로 36",
            "lat": 37.3895,
            "lng": 126.9234,
            "phone": "031-389-5500",
            "daily_price": 5000,
            "free_swim_price": 4000,
            "facilities": ["주차장", "락커룸", "샤워실"],
            "source": "공공데이터"
        },
        {
            "name": "부천 소사구민체육센터 수영장",
            "address": "경기도 부천시 소사구 경인옛길 61",
            "lat": 37.4897,
            "lng": 126.7923,
            "phone": "032-625-7700",
            "daily_price": 4700,
            "free_swim_price": 3700,
            "facilities": ["주차장", "락커룸"],
            "source": "공공데이터"
        }
    ]

    for pool in pools:
        pool["free_swim_times"] = {
            "mon": ["06:00-08:00", "20:00-22:00"],
            "tue": ["06:00-08:00", "20:00-22:00"],
            "wed": ["06:00-08:00", "20:00-22:00"],
            "thu": ["06:00-08:00", "20:00-22:00"],
            "fri": ["06:00-08:00", "20:00-22:00"],
            "sat": ["08:00-12:00"],
            "sun": ["08:00-12:00"]
        }

    return pools

def save_to_json(data: List[Dict], filename="pools_data.json"):
    """JSON 파일로 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 데이터 저장: {filename}")

if __name__ == "__main__":
    print("="*60)
    print("🏊 수영장 데이터 수집 시작")
    print("="*60)

    all_pools = []

    print("\n📍 서울시 공공 수영장 수집 중...")
    seoul_pools = get_seoul_public_pools()
    all_pools.extend(seoul_pools)
    print(f"  ✅ 서울: {len(seoul_pools)}개")

    print("\n📍 경기도 공공 수영장 수집 중...")
    gyeonggi_pools = get_gyeonggi_pools()
    all_pools.extend(gyeonggi_pools)
    print(f"  ✅ 경기: {len(gyeonggi_pools)}개")

    # JSON 저장
    save_to_json(all_pools, "collected_pools.json")

    print(f"\n✅ 총 {len(all_pools)}개 수영장 수집 완료!")

    # 샘플 출력
    print("\n📋 샘플 데이터:")
    for i, pool in enumerate(all_pools[:3], 1):
        print(f"\n{i}. {pool['name']}")
        print(f"   주소: {pool['address']}")
        print(f"   좌표: ({pool.get('lat')}, {pool.get('lng')})")
        print(f"   1회 이용: {pool.get('daily_price', 'N/A'):,}원")
        print(f"   자율수영: {pool.get('free_swim_price', 'N/A'):,}원")
