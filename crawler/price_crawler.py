# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import Dict, Optional, List
import sqlite3
from urllib.parse import quote

class PoolPriceCrawler:
    def __init__(self):
        self.naver_client_id = "VDnVKXoA66gaC4cz3vzc"
        self.naver_client_secret = "XuMSFxDf35"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def find_pool_website(self, pool_name: str, address: str) -> Optional[str]:
        """네이버 검색으로 수영장 공식 웹사이트 찾기"""
        try:
            # 네이버 웹검색 API 사용
            search_query = f"{pool_name} {address.split()[1] if len(address.split()) > 1 else ''} 수영장"

            response = requests.get(
                "https://openapi.naver.com/v1/search/webkr.json",
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

                # 공식 사이트로 보이는 URL 우선순위
                priority_domains = ['go.kr', 'or.kr', 'co.kr', 'com']
                exclude_keywords = ['blog', 'cafe', 'post', 'news', 'review']

                for item in items:
                    url = item.get("link", "")
                    title = item.get("title", "").lower()

                    # 블로그, 카페, 뉴스 제외
                    if any(keyword in url.lower() for keyword in exclude_keywords):
                        continue

                    # 수영장 이름이 타이틀에 포함되어 있는지 확인
                    pool_name_clean = pool_name.replace(" ", "").lower()
                    title_clean = title.replace(" ", "").replace("<b>", "").replace("</b>", "")

                    if pool_name_clean[:4] in title_clean or title_clean[:4] in pool_name_clean:
                        return url

                # 우선순위 도메인 찾기
                for domain in priority_domains:
                    for item in items:
                        url = item.get("link", "")
                        if domain in url and not any(kw in url for kw in exclude_keywords):
                            return url

                # 첫 번째 결과 반환 (블로그 등 제외)
                for item in items:
                    url = item.get("link", "")
                    if not any(keyword in url.lower() for keyword in exclude_keywords):
                        return url

            time.sleep(0.1)
            return None

        except Exception as e:
            print(f"✗ 웹사이트 찾기 실패 ({pool_name}): {str(e)[:50]}")
            return None

    def extract_price_from_text(self, text: str) -> Optional[int]:
        """텍스트에서 가격 추출 (원 단위)"""
        # 가격 패턴: 10,000원, 10000원, 1만원 등
        patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*원',  # 10,000원
            r'(\d+)\s*만\s*원',             # 1만원
            r'(\d+)원',                      # 10000원
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace(',', '')
                if '만' in text[match.start():match.end()+2]:
                    return int(price_str) * 10000
                return int(price_str)

        return None

    def extract_time_from_text(self, text: str) -> List[str]:
        """텍스트에서 시간 추출 (HH:MM-HH:MM 형식)"""
        # 시간 패턴: 06:00-08:00, 6시-8시, 오전 6시 - 오전 8시
        time_ranges = []

        # HH:MM-HH:MM 패턴
        pattern1 = r'(\d{1,2}):(\d{2})\s*[-~]\s*(\d{1,2}):(\d{2})'
        matches = re.findall(pattern1, text)
        for match in matches:
            start_time = f"{int(match[0]):02d}:{match[1]}"
            end_time = f"{int(match[2]):02d}:{match[3]}"
            time_ranges.append(f"{start_time}-{end_time}")

        # HH시-HH시 패턴
        pattern2 = r'(\d{1,2})\s*시\s*[-~]\s*(\d{1,2})\s*시'
        matches = re.findall(pattern2, text)
        for match in matches:
            start_time = f"{int(match[0]):02d}:00"
            end_time = f"{int(match[1]):02d}:00"
            time_ranges.append(f"{start_time}-{end_time}")

        return time_ranges

    def crawl_pool_website(self, url: str, pool_name: str) -> Dict:
        """수영장 웹사이트에서 가격 및 시간 정보 크롤링"""
        result = {
            "daily_price": None,
            "free_swim_price": None,
            "free_swim_times": [],
            "operating_hours": None
        }

        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'

            if response.status_code != 200:
                return result

            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)

            # 가격 정보 추출
            # "자유수영" 관련 섹션 찾기
            free_swim_keywords = ['자유수영', '자율수영', '일일입장', '1회 이용']
            lesson_keywords = ['강습', '수강', '회원']

            # 텍스트를 줄 단위로 분리
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            for i, line in enumerate(lines):
                line_lower = line.lower()

                # 자유수영 가격 찾기
                if any(keyword in line for keyword in free_swim_keywords):
                    # 현재 줄과 다음 3줄에서 가격 찾기
                    for j in range(i, min(i+4, len(lines))):
                        price = self.extract_price_from_text(lines[j])
                        if price and 3000 <= price <= 30000:  # 합리적인 가격 범위
                            if result["free_swim_price"] is None:
                                result["free_swim_price"] = price
                            break

                # 자유수영 시간 찾기
                if any(keyword in line for keyword in free_swim_keywords):
                    for j in range(i, min(i+5, len(lines))):
                        times = self.extract_time_from_text(lines[j])
                        if times:
                            result["free_swim_times"].extend(times)

            # 일일권 가격이 없으면 자유수영 가격 사용
            if result["free_swim_price"]:
                result["daily_price"] = result["free_swim_price"]

            # 중복 제거
            if result["free_swim_times"]:
                result["free_swim_times"] = list(set(result["free_swim_times"]))

            return result

        except Exception as e:
            print(f"✗ 크롤링 실패 ({pool_name}): {str(e)[:50]}")
            return result

    def crawl_all_pools(self):
        """DB의 모든 수영장 가격 정보 크롤링"""
        conn = sqlite3.connect('swimming_pools.db')
        cursor = conn.cursor()

        # URL이 없거나 가격이 기본값인 수영장 가져오기
        cursor.execute('''
            SELECT id, name, address, url
            FROM swimming_pools
            WHERE (url IS NULL OR url = '')
               OR (daily_price = 10000 OR daily_price = 5000)
            ORDER BY id
        ''')

        pools = cursor.fetchall()
        total = len(pools)

        print(f"\n🔍 {total}개 수영장 가격 크롤링 시작...\n")

        success_count = 0
        failed_count = 0

        for i, (pool_id, name, address, url) in enumerate(pools):
            print(f"[{i+1}/{total}] {name}")

            # 1단계: 웹사이트 찾기
            if not url or url == '':
                print(f"  → 웹사이트 검색 중...")
                url = self.find_pool_website(name, address)

                if url:
                    print(f"  ✓ 웹사이트 발견: {url[:50]}...")
                    # URL 업데이트
                    cursor.execute('UPDATE swimming_pools SET url = ? WHERE id = ?', (url, pool_id))
                else:
                    print(f"  ✗ 웹사이트를 찾을 수 없음")
                    failed_count += 1
                    continue

            # 2단계: 가격 정보 크롤링
            print(f"  → 가격 정보 크롤링 중...")
            price_data = self.crawl_pool_website(url, name)

            # 3단계: DB 업데이트 (값이 있는 경우만)
            updates = []
            params = []

            if price_data["daily_price"]:
                updates.append("daily_price = ?")
                params.append(price_data["daily_price"])
                print(f"  ✓ 일일권: {price_data['daily_price']:,}원")

            if price_data["free_swim_price"]:
                updates.append("free_swim_price = ?")
                params.append(price_data["free_swim_price"])
                print(f"  ✓ 자유수영: {price_data['free_swim_price']:,}원")

            if price_data["free_swim_times"]:
                updates.append("free_swim_times = ?")
                params.append(json.dumps({"times": price_data["free_swim_times"]}, ensure_ascii=False))
                print(f"  ✓ 자유수영 시간: {', '.join(price_data['free_swim_times'][:3])}")

            if updates:
                params.append(pool_id)
                query = f"UPDATE swimming_pools SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                success_count += 1
                print(f"  ✓ 업데이트 완료")
            else:
                print(f"  ✗ 가격 정보를 찾을 수 없음")
                failed_count += 1

            conn.commit()
            time.sleep(0.5)  # 서버 부하 방지
            print()

        conn.close()

        print(f"\n{'='*60}")
        print(f"✅ 크롤링 완료")
        print(f"  • 성공: {success_count}개")
        print(f"  • 실패: {failed_count}개")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    print("🏊 수영장 가격 크롤러\n")

    crawler = PoolPriceCrawler()
    crawler.crawl_all_pools()
