# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
from typing import List, Dict, Optional, Set
import time
import os
import anthropic
import base64

class AdvancedPoolCrawler:
    def __init__(self):
        self.naver_client_id = "VDnVKXoA66gaC4cz3vzc"
        self.naver_client_secret = "XuMSFxDf35"

        # 서울 열린데이터광장 API 키 (환경변수 또는 직접 설정)
        # API 키 발급: https://data.seoul.go.kr/together/guide/useGuide.do
        self.seoul_data_api_key = os.getenv("SEOUL_DATA_API_KEY", "")

        self.claude_client = None
        claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        if claude_api_key:
            self.claude_client = anthropic.Anthropic(api_key=claude_api_key)
            print("✓ Claude 이미지 분석 활성화")
        else:
            print("⚠️  ANTHROPIC_API_KEY 없음 - 키워드 필터링만 사용")

        if self.seoul_data_api_key:
            print("✓ 서울 공공데이터 API 활성화")
        else:
            print("⚠️  SEOUL_DATA_API_KEY 없음 - 공공데이터 미사용")

        self.collected_pools = []  # 수집된 수영장 목록
        self.seen_pools: Set[str] = set()  # 중복 체크용 (이름|주소)
        self.seen_coordinates: List[tuple] = []  # 좌표 기반 중복 체크용

    def is_duplicate_by_distance(self, lat: float, lng: float, name: str, threshold_meters: float = 100) -> bool:
        """위도/경도 기반으로 중복 체크 (100m 이내 + 같은 이름이면 중복)"""
        if not lat or not lng:
            return False

        import math

        for seen_lat, seen_lng, seen_name in self.seen_coordinates:
            # Haversine 거리 계산
            R = 6371000  # 지구 반경 (m)
            dlat = math.radians(lat - seen_lat)
            dlng = math.radians(lng - seen_lng)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(seen_lat)) * math.cos(math.radians(lat)) *
                 math.sin(dlng / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            distance = R * c

            # 같은 이름 + 100m 이내면 중복
            if distance < threshold_meters and name in seen_name or seen_name in name:
                return True

        return False

    def is_valid_pool_image_by_keyword(self, image_url: str, title: str) -> bool:
        exclude_keywords = [
            "logo", "banner", "ad", "icon", "profile",
            "사람", "인물", "모델", "광고", "공사", "건설", "시공"
        ]
        include_keywords = [
            "수영", "pool", "swimming", "아쿠아", "aqua", "워터", "water", "레인", "lane"
        ]

        check_text = (image_url + " " + title).lower()

        for keyword in exclude_keywords:
            if keyword in check_text:
                return False

        return any(keyword in check_text for keyword in include_keywords)

    def analyze_image_with_claude(self, image_url: str) -> Optional[bool]:
        if not self.claude_client:
            return None

        try:
            response = requests.get(image_url, timeout=5)
            if response.status_code != 200:
                return None

            image_data = base64.standard_b64encode(response.content).decode("utf-8")
            content_type = response.headers.get('content-type', 'image/jpeg')

            if 'image/' not in content_type:
                return False

            media_type = content_type if content_type.startswith('image/') else 'image/jpeg'

            message = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=100,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": "이 이미지가 실내 수영장 사진입니까? (수영 레인이 보이는 실제 수영장 시설) '예' 또는 '아니오'로만 답변하세요."
                        }
                    ],
                }]
            )

            answer = message.content[0].text.strip().lower()
            return "예" in answer or "yes" in answer

        except Exception:
            return None

    def get_image_from_naver_api(self, pool_name: str) -> str:
        try:
            response = requests.get(
                "https://openapi.naver.com/v1/search/image",
                headers={
                    "X-Naver-Client-Id": self.naver_client_id,
                    "X-Naver-Client-Secret": self.naver_client_secret
                },
                params={
                    "query": f"{pool_name} 수영장 실내",
                    "display": 20,
                    "sort": "sim"
                }
            )

            if response.status_code == 200:
                items = response.json().get("items", [])

                for idx, item in enumerate(items):
                    image_url = item.get("link")
                    title = item.get("title", "")

                    if not image_url or not self.is_valid_pool_image_by_keyword(image_url, title):
                        continue

                    if self.claude_client:
                        is_pool = self.analyze_image_with_claude(image_url)
                        if is_pool is True:
                            print(f"✓ {pool_name}")
                            return image_url
                        elif is_pool is False:
                            continue
                    else:
                        print(f"✓ {pool_name} (키워드)")
                        return image_url

                print(f"✗ {pool_name} - 적합한 이미지 없음")
                return None

            return None

        except Exception as e:
            print(f"✗ {pool_name} - {str(e)[:30]}")
            return None

    def search_pools_from_seoul_data(self) -> List[Dict]:
        """서울 열린데이터광장 API로 체육시설(수영장) 검색"""
        if not self.seoul_data_api_key:
            return []

        pools = []

        try:
            # 서울시 체육시설 공공서비스예약 정보 API
            # 실제 엔드포인트는 API 키 발급 후 확인 필요
            # 예시: http://openapi.seoul.go.kr:8088/{API_KEY}/json/ListPublicReservationSport/1/100/
            response = requests.get(
                f"http://openapi.seoul.go.kr:8088/{self.seoul_data_api_key}/json/ListPublicReservationSport/1/1000/",
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("ListPublicReservationSport", {}).get("row", [])

                for item in items:
                    # 수영장 관련 시설만 필터링
                    facility_name = item.get("SVCNM", "")
                    if "수영" not in facility_name:
                        continue

                    address = item.get("PLACENM", "")
                    lat = float(item.get("Y", 0)) if item.get("Y") else None
                    lng = float(item.get("X", 0)) if item.get("X") else None

                    # 서울만 필터링
                    if "서울" not in address:
                        continue

                    # 중복 체크 1: 이름+주소
                    pool_key = f"{facility_name}|{address}"
                    if pool_key in self.seen_pools:
                        continue

                    # 중복 체크 2: 좌표 기반 (같은 이름 + 100m 이내)
                    if self.is_duplicate_by_distance(lat, lng, facility_name):
                        continue

                    self.seen_pools.add(pool_key)
                    self.seen_coordinates.append((lat, lng, facility_name))

                    pool = {
                        "name": facility_name,
                        "address": address,
                        "lat": lat,
                        "lng": lng,
                        "phone": item.get("TELNO", ""),
                        "category": "공공체육시설",
                        "source": "서울 열린데이터광장"
                    }

                    pools.append(pool)
                    print(f"✓ 공공데이터: {facility_name}")

            time.sleep(0.1)

        except Exception as e:
            print(f"✗ 서울 공공데이터 API 실패: {str(e)[:50]}")

        return pools

    def search_pools_from_naver(self, query: str, max_results: int = 100) -> List[Dict]:
        """네이버 지역 검색 API로 수영장 검색"""
        pools = []

        try:
            response = requests.get(
                "https://openapi.naver.com/v1/search/local.json",
                headers={
                    "X-Naver-Client-Id": self.naver_client_id,
                    "X-Naver-Client-Secret": self.naver_client_secret
                },
                params={
                    "query": query,
                    "display": min(max_results, 10),
                    "sort": "random"
                }
            )

            if response.status_code == 200:
                items = response.json().get("items", [])

                for item in items:
                    title = item.get("title", "").replace("<b>", "").replace("</b>", "")
                    address = item.get("address", "") or item.get("roadAddress", "")

                    # 좌표 변환 (카텍좌표 -> 위경도)
                    mapx = int(item.get("mapx", 0)) / 10000000
                    mapy = int(item.get("mapy", 0)) / 10000000

                    # 중복 체크 1: 이름+주소
                    pool_key = f"{title}|{address}"
                    if pool_key in self.seen_pools:
                        continue

                    # 중복 체크 2: 좌표 기반 (같은 이름 + 100m 이내)
                    if self.is_duplicate_by_distance(mapy, mapx, title):
                        continue

                    self.seen_pools.add(pool_key)
                    self.seen_coordinates.append((mapy, mapx, title))

                    pool = {
                        "name": title,
                        "address": address,
                        "lat": mapy,
                        "lng": mapx,
                        "phone": item.get("telephone", ""),
                        "category": item.get("category", ""),
                        "source": "네이버 검색"
                    }

                    pools.append(pool)

            time.sleep(0.1)

        except Exception as e:
            print(f"✗ 네이버 검색 실패: {query} - {str(e)[:50]}")

        return pools

    def search_all_pools(self) -> List[Dict]:
        """다양한 키워드로 서울 수영장 전체 검색"""
        print("\n🔍 서울 수영장 검색 시작...\n")

        # 1단계: 서울 공공데이터 API로 공공체육시설 검색
        if self.seoul_data_api_key:
            print("=" * 60)
            print("📊 서울 열린데이터광장 API 검색")
            print("=" * 60)
            public_pools = self.search_pools_from_seoul_data()
            self.collected_pools.extend(public_pools)
            print(f"  → {len(public_pools)}개 발견 (누적: {len(self.collected_pools)}개)\n")
            time.sleep(1)

        # 2단계: 네이버 검색 API로 민간 수영장 검색
        print("=" * 60)
        print("🔍 네이버 지역검색 API")
        print("=" * 60)

        # 다양한 검색 키워드
        search_keywords = [
            "서울 수영장",
            "서울 실내수영장",
            "서울 사립수영장",
            "서울 공공수영장",
            "서울 헬스장 수영장",
            "서울 호텔 수영장",
            "서울 아쿠아틱센터",
            "서울 스포츠센터 수영장",
            "서울 어린이 수영장",
            "서울 수영 아카데미",
        ]

        # 주요 광역시 추가
        major_cities = [
            "부산", "인천", "대구", "대전", "광주", "울산", "세종", "경기도", "제주"
        ]
        
        for city in major_cities:
            search_keywords.append(f"{city} 수영장")
            search_keywords.append(f"{city} 실내수영장")

        # 서울 25개 구별 검색
        seoul_districts = [
            "강남구", "강동구", "강북구", "강서구", "관악구",
            "광진구", "구로구", "금천구", "노원구", "도봉구",
            "동대문구", "동작구", "마포구", "서대문구", "서초구",
            "성동구", "성북구", "송파구", "양천구", "영등포구",
            "용산구", "은평구", "종로구", "중구", "중랑구"
        ]

        for district in seoul_districts:
            search_keywords.append(f"서울 {district} 수영장")
            search_keywords.append(f"서울 {district} 실내수영장")

        for keyword in search_keywords:
            print(f"검색: {keyword}")
            pools = self.search_pools_from_naver(keyword)
            self.collected_pools.extend(pools)
            print(f"  → {len(pools)}개 발견 (누적: {len(self.collected_pools)}개)\n")
            time.sleep(0.5)

        return self.collected_pools

    def enrich_pool_data(self, pool: Dict) -> Dict:
        """수영장 정보 보강 (이미지)"""
        # 이미지 크롤링
        image_url = self.get_image_from_naver_api(pool["name"])
        if image_url:
            pool["image_url"] = image_url

        # 가격 및 시간 정보는 기본값을 넣지 않고 빈 상태로 둡니다.
        # 실제 데이터는 price_crawler.py 등을 통해 채워지게 됩니다.
        
        # 기본 필드 초기화 (None으로 설정)
        if "daily_price" not in pool:
            pool["daily_price"] = None
        if "free_swim_price" not in pool:
            pool["free_swim_price"] = None
        if "operating_hours" not in pool:
            pool["operating_hours"] = None
        if "free_swim_times" not in pool:
            pool["free_swim_times"] = None

        # 기타 부가 정보 (기본값 최소화)
        if "facilities" not in pool:
            pool["facilities"] = ["수영장"]
        
        return pool

    def crawl_all_pools(self) -> List[Dict]:
        """전체 크롤링 프로세스"""
        # 1단계: 수영장 목록 검색
        pools = self.search_all_pools()

        if not pools:
            print("✗ 수영장을 찾지 못했습니다")
            return []

        print(f"\n📋 총 {len(pools)}개 수영장 발견")
        print("\n🖼️  이미지 및 상세정보 수집 중...\n")

        # 2단계: 각 수영장 상세정보 보강
        for i, pool in enumerate(pools):
            print(f"[{i+1}/{len(pools)}] {pool['name']}")
            self.enrich_pool_data(pool)
            time.sleep(0.2)

        return pools

def save_to_json(data: List[Dict], filename="advanced_pools.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 저장: {filename}")

if __name__ == "__main__":
    print("🏊 서울 수영장 크롤러\n")

    crawler = AdvancedPoolCrawler()
    pools = crawler.crawl_all_pools()

    if pools:
        save_to_json(pools, "advanced_pools.json")
        print(f"\n✅ {len(pools)}개 수영장 수집 완료")
        print("\nDB 로드: python load_data_to_db.py advanced_pools.json")
    else:
        print("✗ 수집 실패")
