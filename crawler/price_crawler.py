# -*- coding: utf-8 -*-
"""
수영장 데이터 보강 통합 크롤러

기능:
  - 네이버 지역검색 API로 전화번호 수집
  - 네이버 웹검색 API로 공식 웹사이트 찾기
  - 웹사이트 크롤링으로 가격/운영시간/자유수영시간 추출

사용법:
  python crawler/price_crawler.py              # 전체 실행
  python crawler/price_crawler.py --test 5     # 5건만 테스트
  python crawler/price_crawler.py --dry-run    # DB 업데이트 없이 결과만 출력
  python crawler/price_crawler.py --test 3 --dry-run
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import argparse
import requests
from bs4 import BeautifulSoup
import json
import time
import re
from typing import Dict, Optional, List
import sqlite3


class PoolDataCrawler:
    def __init__(self):
        # 환경변수에서 API 키 로드
        self.naver_client_id = os.environ.get('NAVER_CLIENT_ID')
        self.naver_client_secret = os.environ.get('NAVER_CLIENT_SECRET')

        if not self.naver_client_id or not self.naver_client_secret:
            print("ERROR: 환경변수 NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 을 설정하세요.")
            print("  set NAVER_CLIENT_ID=your_client_id")
            print("  set NAVER_CLIENT_SECRET=your_client_secret")
            sys.exit(1)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    # ── 네이버 지역검색 API (전화번호 수집) ──

    def search_naver_place(self, pool_name: str, address: str) -> Optional[Dict]:
        """네이버 지역검색 API로 전화번호/카테고리 수집"""
        try:
            # 주소에서 구 정보 추출
            district = ""
            if "구" in address:
                for part in address.split():
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
                params={"query": search_query, "display": 5}
            )

            if response.status_code == 200:
                items = response.json().get("items", [])
                for item in items:
                    title = item.get("title", "").replace("<b>", "").replace("</b>", "")
                    # 이름 유사도 확인 (앞 4글자 비교)
                    if pool_name[:4] in title or title[:4] in pool_name:
                        return {
                            "telephone": item.get("telephone", ""),
                            "category": item.get("category", ""),
                            "link": item.get("link", ""),
                        }

            time.sleep(0.1)
            return None

        except Exception as e:
            print(f"    ✗ 네이버 지역검색 실패: {str(e)[:50]}")
            return None

    # ── 네이버 웹검색 API (공식 웹사이트 찾기) ──

    def find_pool_website(self, pool_name: str, address: str) -> Optional[str]:
        """네이버 웹검색으로 수영장 공식 웹사이트 찾기"""
        try:
            addr_parts = address.split()
            district = addr_parts[1] if len(addr_parts) > 1 else ''
            search_query = f"{pool_name} {district} 수영장"

            response = requests.get(
                "https://openapi.naver.com/v1/search/webkr.json",
                headers={
                    "X-Naver-Client-Id": self.naver_client_id,
                    "X-Naver-Client-Secret": self.naver_client_secret
                },
                params={"query": search_query, "display": 5}
            )

            if response.status_code == 200:
                items = response.json().get("items", [])
                exclude_keywords = ['blog', 'cafe', 'post', 'news', 'review']
                priority_domains = ['go.kr', 'or.kr', 'co.kr', 'com']

                # 1) 수영장 이름 매칭
                for item in items:
                    url = item.get("link", "")
                    title = item.get("title", "").lower().replace("<b>", "").replace("</b>", "")
                    if any(kw in url.lower() for kw in exclude_keywords):
                        continue
                    pool_clean = pool_name.replace(" ", "").lower()
                    title_clean = title.replace(" ", "")
                    if pool_clean[:4] in title_clean or title_clean[:4] in pool_clean:
                        return url

                # 2) 우선순위 도메인
                for domain in priority_domains:
                    for item in items:
                        url = item.get("link", "")
                        if domain in url and not any(kw in url for kw in exclude_keywords):
                            return url

                # 3) 블로그 제외 첫 번째 결과
                for item in items:
                    url = item.get("link", "")
                    if not any(kw in url.lower() for kw in exclude_keywords):
                        return url

            time.sleep(0.1)
            return None

        except Exception as e:
            print(f"    ✗ 웹사이트 찾기 실패 ({pool_name}): {str(e)[:50]}")
            return None

    # ── 가격 추출 ──

    def extract_price_from_text(self, text: str, context: str = "") -> Optional[int]:
        """텍스트에서 가격 추출 (원 단위)"""
        patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*원',
            r'(\d+)\s*만\s*(\d{1,4})\s*원',
            r'(\d+)\s*만\s*원',
            r'(\d{4,6})\s*원',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                try:
                    price_str = match.group(1).replace(',', '')
                    if '만' in match.group(0):
                        price = int(price_str) * 10000
                        if len(match.groups()) > 1 and match.group(2):
                            price += int(match.group(2))
                    else:
                        price = int(price_str)

                    # 수영장 가격 범위: 2,000 ~ 50,000원
                    if 2000 <= price <= 50000:
                        return price
                except (ValueError, IndexError):
                    continue

        return None

    # ── 시간 추출 ──

    def extract_time_from_text(self, text: str) -> List[str]:
        """텍스트에서 시간 범위 추출 (HH:MM-HH:MM 형식)"""
        time_ranges = []

        # HH:MM ~ HH:MM
        for m in re.findall(r'(\d{1,2}):(\d{2})\s*[-~]\s*(\d{1,2}):(\d{2})', text):
            start = f"{int(m[0]):02d}:{m[1]}"
            end = f"{int(m[2]):02d}:{m[3]}"
            time_ranges.append(f"{start}-{end}")

        # HH시 ~ HH시
        for m in re.findall(r'(\d{1,2})\s*시\s*[-~]\s*(\d{1,2})\s*시', text):
            time_ranges.append(f"{int(m[0]):02d}:00-{int(m[1]):02d}:00")

        return time_ranges

    # ── 운영시간 추출 ──

    def extract_operating_hours(self, text: str) -> Optional[Dict]:
        """텍스트에서 운영시간 추출 → JSON 형태

        다양한 패턴을 처리:
        1) 같은 줄: "평일 06:00~22:00 / 주말 07:00~21:00"
        2) 분리 줄: "평일" (줄1) → "06:00~22:00" (줄2)
        3) 운영시간 키워드 근처에서 시간 범위 탐색
        """
        weekday_keywords = ['평일', '월~금', '월요일~금요일', '주중']
        weekend_keywords = ['주말', '토요일', '일요일', '토,일', '토·일', '토/일']
        saturday_keywords = ['토요일']
        sunday_keywords = ['일요일']
        hours_keywords = ['운영시간', '이용시간', '영업시간', '개장시간', '개방시간', '센터운영']

        result = {}

        # 1단계: 같은 줄에 평일/주말 시간이 함께 있는 패턴
        combined_pattern = (
            r'(?:평일|주중|월~금)\s*(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})'
            r'\s*[/,]\s*'
            r'(?:주말|토[·,/]?일)\s*(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})'
        )
        m = re.search(combined_pattern, text)
        if m:
            result["weekday"] = f"{m.group(1)}-{m.group(2)}"
            result["weekend"] = f"{m.group(3)}-{m.group(4)}"
            return result

        # 2단계: 줄 기반 탐색 — 운영시간 키워드 또는 요일 키워드 근처에서 시간 추출
        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # 운영시간 키워드가 있는 영역(±10줄)에서만 탐색
        hours_zones = set()
        for i, line in enumerate(lines):
            if any(kw in line for kw in hours_keywords):
                for j in range(i, min(i + 10, len(lines))):
                    hours_zones.add(j)

        for i, line in enumerate(lines):
            # 운영시간 영역 안에서만 탐색
            if hours_zones and i not in hours_zones:
                continue

            # 같은 줄에 요일+시간이 있는 경우: "평일 06:00~22:00"
            times_in_line = self.extract_time_from_text(line)
            if times_in_line:
                if any(kw in line for kw in weekday_keywords) and "weekday" not in result:
                    result["weekday"] = times_in_line[0]
                    continue
                if any(kw in line for kw in weekend_keywords + saturday_keywords) and "weekend" not in result:
                    result["weekend"] = times_in_line[0]
                    continue
                if any(kw in line for kw in sunday_keywords) and "sunday" not in result:
                    result["sunday"] = times_in_line[0]
                    continue

            # 요일 키워드만 있는 줄 → 다음 줄에서 시간 탐색
            is_weekday_label = any(kw in line for kw in weekday_keywords) and not times_in_line
            is_weekend_label = any(kw in line for kw in weekend_keywords + saturday_keywords) and not times_in_line
            is_sunday_label = any(kw in line for kw in sunday_keywords) and not times_in_line

            if is_weekday_label or is_weekend_label or is_sunday_label:
                # 다음 1~2줄에서 시간 탐색
                for j in range(i + 1, min(i + 3, len(lines))):
                    next_times = self.extract_time_from_text(lines[j])
                    if next_times:
                        if is_weekday_label and "weekday" not in result:
                            result["weekday"] = next_times[0]
                        elif is_weekend_label and "weekend" not in result:
                            result["weekend"] = next_times[0]
                        elif is_sunday_label and "sunday" not in result:
                            result["sunday"] = next_times[0]
                        break

        # 운영시간 영역이 없으면(키워드 없는 경우) 결과 없음 반환
        if not hours_zones and not result:
            return None

        # 운영시간 영역은 있는데 요일 구분이 없는 경우: 첫 번째 시간을 weekday로
        if not result and hours_zones:
            for i in sorted(hours_zones):
                if i < len(lines):
                    times = self.extract_time_from_text(lines[i])
                    if times:
                        result["weekday"] = times[0]
                        break

        # 토요일만 있고 "weekend" 키로 통합
        if "saturday" in result and "weekend" not in result:
            result["weekend"] = result.pop("saturday")

        return result if result else None

    # ── 웹사이트 크롤링 ──

    def crawl_pool_website(self, url: str, pool_name: str) -> Dict:
        """수영장 웹사이트에서 가격/운영시간/자유수영시간 크롤링"""
        result = {
            "free_swim_price": None,
            "monthly_lesson_price": None,
            "free_swim_times": [],
            "operating_hours": None,
        }

        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'utf-8'
            if response.status_code != 200:
                return result

            # 응답 크기 제한 (5MB)
            if len(response.content) > 5 * 1024 * 1024:
                return result

            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            lines = [line.strip() for line in text.split('\n') if line.strip()]

            free_swim_keywords = ['자유수영', '자율수영', '일일입장', '1회 이용']
            lesson_keywords = ['강습', '수강', '월 수영', '한달']

            for i, line in enumerate(lines):
                # 자유수영 가격
                if any(kw in line for kw in free_swim_keywords):
                    for j in range(i, min(i + 4, len(lines))):
                        price = self.extract_price_from_text(lines[j], context=line)
                        if price and result["free_swim_price"] is None:
                            result["free_swim_price"] = price
                            break

                # 강습 가격
                if any(kw in line for kw in lesson_keywords):
                    for j in range(i, min(i + 4, len(lines))):
                        price = self.extract_price_from_text(lines[j], context=line)
                        if price and price > 30000 and result["monthly_lesson_price"] is None:
                            result["monthly_lesson_price"] = price
                            break

                # 자유수영 시간
                if any(kw in line for kw in free_swim_keywords):
                    for j in range(i, min(i + 5, len(lines))):
                        times = self.extract_time_from_text(lines[j])
                        if times:
                            result["free_swim_times"].extend(times)

            # 운영시간 추출
            result["operating_hours"] = self.extract_operating_hours(text)

            # 중복 제거
            if result["free_swim_times"]:
                result["free_swim_times"] = list(set(result["free_swim_times"]))

            return result

        except Exception as e:
            print(f"    ✗ 크롤링 실패 ({pool_name}): {str(e)[:50]}")
            return result

    # ── 메인 실행 ──

    def crawl_all_pools(self, test_count: int = 0, dry_run: bool = False):
        """DB의 보강 필요한 수영장 크롤링

        Args:
            test_count: 0이면 전체, N이면 N건만 크롤링
            dry_run: True이면 DB 업데이트 없이 결과만 출력
        """
        conn = sqlite3.connect('swimming_pools.db')
        try:
            self._crawl_pools_inner(conn, test_count, dry_run)
        finally:
            conn.close()

    def _crawl_pools_inner(self, conn, test_count: int, dry_run: bool):
        """크롤링 내부 로직 (conn은 호출자가 관리)"""
        cursor = conn.cursor()

        # 보강 필요한 수영장 조회
        empty_vals = ('', '정보 없음', 'null', 'None')
        ph = ','.join(['?'] * len(empty_vals))
        cursor.execute(f'''
            SELECT id, name, address, url, phone, operating_hours
            FROM swimming_pools
            WHERE (phone IS NULL OR phone IN ({ph}))
               OR (url IS NULL OR url IN ({ph}))
               OR (free_swim_price IS NULL OR free_swim_price IN ({ph}))
               OR (daily_price IS NULL OR daily_price IN ({ph}))
               OR (operating_hours IS NULL OR operating_hours IN ({ph}) OR operating_hours = '{{}}')
            ORDER BY id
        ''', empty_vals * 5)

        pools = cursor.fetchall()

        if test_count > 0:
            pools = pools[:test_count]

        total = len(pools)
        mode_label = " [DRY-RUN]" if dry_run else ""

        print(f"\n{'='*60}")
        print(f"  {total}개 수영장 데이터 보강 크롤링 시작{mode_label}")
        print(f"{'='*60}\n")

        stats = {"phone": 0, "url": 0, "price": 0, "hours": 0, "failed": 0}

        for i, (pool_id, name, address, url, phone, operating_hours) in enumerate(pools):
            print(f"[{i+1}/{total}] {name}")

            updates = []
            params = []

            # ── 1단계: 전화번호 없으면 네이버 지역검색 ──
            if not phone or phone in ('', '정보 없음'):
                print(f"  → 네이버 지역검색 (전화번호)...")
                place = self.search_naver_place(name, address)
                if place and place["telephone"]:
                    updates.append("phone = ?")
                    params.append(place["telephone"])
                    stats["phone"] += 1
                    print(f"    ✓ 전화번호: {place['telephone']}")
                else:
                    print(f"    ✗ 전화번호 못 찾음")

            # ── 2단계: URL 없으면 네이버 웹검색 ──
            if not url or url in ('', '정보 없음'):
                print(f"  → 네이버 웹검색 (공식 사이트)...")
                url = self.find_pool_website(name, address)
                if url:
                    updates.append("url = ?")
                    params.append(url)
                    stats["url"] += 1
                    print(f"    ✓ 웹사이트: {url[:60]}...")
                else:
                    print(f"    ✗ 웹사이트 못 찾음")

            # ── 3단계: URL이 있으면 웹사이트 크롤링 ──
            if url and url not in ('', '정보 없음'):
                print(f"  → 웹사이트 크롤링 (가격/운영시간)...")
                data = self.crawl_pool_website(url, name)

                if data["free_swim_price"]:
                    updates.append("daily_price = ?")
                    updates.append("free_swim_price = ?")
                    params.append(str(data["free_swim_price"]))
                    params.append(str(data["free_swim_price"]))
                    stats["price"] += 1
                    print(f"    ✓ 자유수영: {data['free_swim_price']:,}원")

                if data["monthly_lesson_price"]:
                    updates.append("monthly_lesson_price = ?")
                    params.append(str(data["monthly_lesson_price"]))
                    print(f"    ✓ 월강습: {data['monthly_lesson_price']:,}원")

                if data["free_swim_times"]:
                    updates.append("free_swim_times = ?")
                    params.append(json.dumps({"times": data["free_swim_times"]}, ensure_ascii=False))
                    print(f"    ✓ 자유수영시간: {', '.join(data['free_swim_times'][:3])}")

                # 운영시간: 기존 값이 비어있을 때만 업데이트
                empty_hours = (None, '', '{}', 'null', 'None')
                if data["operating_hours"] and (not operating_hours or operating_hours in empty_hours):
                    updates.append("operating_hours = ?")
                    params.append(json.dumps(data["operating_hours"], ensure_ascii=False))
                    stats["hours"] += 1
                    print(f"    ✓ 운영시간: {data['operating_hours']}")

            # ── 4단계: DB 업데이트 ──
            if updates:
                if dry_run:
                    print(f"  [DRY-RUN] {len(updates)}개 필드 업데이트 예정")
                else:
                    params.append(pool_id)
                    query = f"UPDATE swimming_pools SET {', '.join(updates)} WHERE id = ?"
                    cursor.execute(query, params)
                    conn.commit()
                    print(f"  ✓ DB 업데이트 완료 ({len(updates)}개 필드)")
            else:
                stats["failed"] += 1
                print(f"  ✗ 추출 가능한 정보 없음")

            time.sleep(0.5)
            print()

        # ── 결과 요약 ──
        print(f"{'='*60}")
        print(f"  크롤링 완료{mode_label}")
        print(f"  전화번호 추가: {stats['phone']}건")
        print(f"  웹사이트 추가: {stats['url']}건")
        print(f"  가격 추출:     {stats['price']}건")
        print(f"  운영시간 추출: {stats['hours']}건")
        print(f"  실패:          {stats['failed']}건")
        print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="수영장 데이터 보강 통합 크롤러")
    parser.add_argument('--test', type=int, default=0, metavar='N',
                        help='N건만 테스트 크롤링 (기본: 전체)')
    parser.add_argument('--dry-run', action='store_true',
                        help='DB 업데이트 없이 결과만 출력')
    args = parser.parse_args()

    print("수영장 데이터 보강 통합 크롤러\n")

    crawler = PoolDataCrawler()
    crawler.crawl_all_pools(test_count=args.test, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
