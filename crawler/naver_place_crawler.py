# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import json
import time
import re
import sqlite3
from typing import Dict, Optional

class NaverPlaceCrawler:
    """네이버 플레이스에서 수영장 정보 크롤링"""

    def __init__(self):
        self.naver_client_id = "VDnVKXoA66gaC4cz3vzc"
        self.naver_client_secret = "XuMSFxDf35"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def search_naver_place(self, pool_name: str, address: str) -> Optional[Dict]:
        """네이버 지역 검색으로 플레이스 정보 가져오기"""
        try:
            # 주소에서 구 정보 추출
            district = ""
            if "구" in address:
                parts = address.split()
                for part in parts:
                    if "구" in part:
                        district = part
                        break

            search_query = f"{pool_name} {district}"

            response = requests.get(
                "https://openapi.naver.com/v1/search/local.json",
                headers={
                    "X-Naver-Client-Id": self.naver_client_id,
                    "X-Naver-Client-Secret": self.naver_client_secret
                },
                params={
                    "query": search_query,
                    "display": 5
                }
            )

            if response.status_code == 200:
                items = response.json().get("items", [])

                for item in items:
                    title = item.get("title", "").replace("<b>", "").replace("</b>", "")
                    item_address = item.get("address", "")

                    # 이름이 유사한지 확인
                    if pool_name[:4] in title or title[:4] in pool_name:
                        return {
                            "title": title,
                            "category": item.get("category", ""),
                            "telephone": item.get("telephone", ""),
                            "address": item_address,
                            "roadAddress": item.get("roadAddress", ""),
                            "link": item.get("link", "")
                        }

            time.sleep(0.1)
            return None

        except Exception as e:
            print(f"  ✗ 네이버 검색 실패: {str(e)[:50]}")
            return None

    def extract_price_from_description(self, description: str) -> Optional[int]:
        """설명에서 가격 추출"""
        if not description:
            return None

        patterns = [
            r'(\d{1,2}),(\d{3})\s*원',  # 3,500원
            r'(\d{4,5})\s*원',           # 3500원
            r'(\d{1,2})\s*만\s*(\d{0,4})\s*원',  # 1만 5000원
        ]

        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                if '만' in description[max(0, match.start()-2):match.end()+2]:
                    man = int(match.group(1))
                    cheon = int(match.group(2)) if len(match.groups()) > 1 and match.group(2) else 0
                    return man * 10000 + cheon
                elif len(match.groups()) > 1:
                    return int(match.group(1) + match.group(2))
                else:
                    price = int(match.group(1))
                    if price >= 1000:
                        return price

        return None

    def get_public_pool_prices(self) -> Dict[str, int]:
        """구민체육센터 등 공공 수영장 표준 가격"""
        return {
            "구민체육센터": 3500,
            "구민회관": 3500,
            "공공수영장": 3000,
            "구립수영장": 3500,
            "체육관": 3500,
            "복지관": 3000,
            "청소년": 2500,
            "어린이": 2000,
        }

    def estimate_price_by_category(self, pool_name: str, category: str) -> Optional[int]:
        """카테고리와 이름으로 가격 추정"""
        # 공공 수영장 가격
        public_keywords = self.get_public_pool_prices()
        for keyword, price in public_keywords.items():
            if keyword in pool_name:
                return price

        # 민간 수영장 카테고리별 가격
        if "호텔" in category or "호텔" in pool_name:
            return 20000
        elif "피트니스" in category or "헬스" in pool_name or "스포츠센터" in pool_name:
            return 12000
        elif "수영장" in category:
            return 10000
        elif "아카데미" in pool_name or "강습" in pool_name:
            return 8000

        return None

    def crawl_pool_info(self, pool_name: str, address: str) -> Dict:
        """수영장 정보 크롤링"""
        result = {
            "name": pool_name,
            "address": address,
            "daily_price": None,
            "free_swim_price": None,
            "phone": None,
            "category": None
        }

        print(f"  → 네이버 검색 중...")

        # 1. 네이버 플레이스 검색
        place_info = self.search_naver_place(pool_name, address)

        if not place_info:
            print(f"  ✗ 네이버 플레이스 없음")
            # 카테고리 기반 가격 추정
            estimated_price = self.estimate_price_by_category(pool_name, "")
            if estimated_price:
                result["daily_price"] = estimated_price
                result["free_swim_price"] = estimated_price
                print(f"  ⚠️  가격 추정: {estimated_price:,}원")
            return result

        # 2. 전화번호, 카테고리 저장
        result["phone"] = place_info.get("telephone", "")
        result["category"] = place_info.get("category", "")

        print(f"  ✓ 플레이스 발견: {place_info['title']}")
        print(f"    카테고리: {result['category']}")

        # 3. 가격 추정
        estimated_price = self.estimate_price_by_category(pool_name, result['category'])

        if estimated_price:
            result["daily_price"] = estimated_price
            result["free_swim_price"] = estimated_price
            print(f"  ✓ 가격 추정: {estimated_price:,}원")
        else:
            result["daily_price"] = 10000
            result["free_swim_price"] = 8000
            print(f"  ⚠️  기본 가격 설정: 10,000원/8,000원")

        return result

    def update_database(self):
        """DB의 모든 수영장 정보 업데이트"""
        conn = sqlite3.connect('swimming_pools.db')
        cursor = conn.cursor()

        # 가격이 없거나 기본값인 수영장만 업데이트
        cursor.execute('''
            SELECT id, name, address
            FROM swimming_pools
            WHERE daily_price IS NULL
               OR daily_price IN (5000, 10000)
               OR free_swim_price IS NULL
               OR free_swim_price IN (4000, 8000)
            ORDER BY id
        ''')

        pools = cursor.fetchall()
        total = len(pools)

        print(f"\n{'='*80}")
        print(f"🏊 {total}개 수영장 정보 업데이트 시작")
        print(f"{'='*80}\n")

        updated_count = 0

        for i, (pool_id, name, address) in enumerate(pools):
            print(f"[{i+1}/{total}] {name}")

            # 정보 크롤링
            info = self.crawl_pool_info(name, address)

            # DB 업데이트
            updates = []
            params = []

            if info["daily_price"]:
                updates.append("daily_price = ?")
                params.append(info["daily_price"])

            if info["free_swim_price"]:
                updates.append("free_swim_price = ?")
                params.append(info["free_swim_price"])

            if info["phone"] and info["phone"] != "":
                updates.append("phone = ?")
                params.append(info["phone"])

            if updates:
                params.append(pool_id)
                query = f"UPDATE swimming_pools SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                updated_count += 1

            conn.commit()
            time.sleep(0.3)  # 서버 부하 방지
            print()

        conn.close()

        print(f"\n{'='*80}")
        print(f"✅ 업데이트 완료: {updated_count}개 수영장")
        print(f"{'='*80}")

if __name__ == "__main__":
    print("🏊 네이버 플레이스 기반 수영장 가격 크롤러\n")

    crawler = NaverPlaceCrawler()
    crawler.update_database()
