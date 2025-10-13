# -*- coding: utf-8 -*-
"""
스마트 수영장 크롤러 - ChatGPT 가이드 적용
- 세션 재사용 + Retry + 지수 백오프
- robots.txt 확인
- User-Agent 위장
- 실제 웹사이트에서 가격 정보 크롤링
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import time
import random
import re
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional
import urllib.robotparser as rp

import requests
from requests.adapters import HTTPAdapter, Retry
from bs4 import BeautifulSoup
import json

class SmartPoolCrawler:
    def __init__(self):
        # 세션 + Retry 설정
        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=0.5,  # 0.5초, 1초, 2초, 4초, 8초로 증가
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.mount("http://", HTTPAdapter(max_retries=retries))

        # User-Agent 위장
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })

        self.robots_cache = {}  # robots.txt 캐시

    def can_fetch(self, url: str, user_agent: str = "*") -> bool:
        """robots.txt 확인"""
        try:
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            if base_url not in self.robots_cache:
                robots_url = f"{base_url}/robots.txt"
                parser = rp.RobotFileParser()
                parser.set_url(robots_url)
                parser.read()
                self.robots_cache[base_url] = parser

            return self.robots_cache[base_url].can_fetch(user_agent, url)
        except Exception:
            # robots.txt 없으면 허용
            return True

    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """세션을 사용한 GET 요청"""
        try:
            # robots.txt 확인
            if not self.can_fetch(url):
                print(f"❌ robots.txt 차단: {url}")
                return None

            # 타임아웃 기본값 설정
            kwargs.setdefault("timeout", 10)

            # 요청 전 대기 (예의)
            time.sleep(random.uniform(0.5, 1.5))

            response = self.session.get(url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ 요청 실패: {url} - {str(e)[:50]}")
            return None

    def extract_price_from_text(self, text: str) -> Optional[str]:
        """텍스트에서 가격 정보 추출"""
        if not text:
            return None

        # 패턴 1: "000원", "0,000원"
        patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*원',
            r'(\d{4,})\s*원',
            r'₩\s*(\d{1,3}(?:,\d{3})*)',
            r'(\d{1,3}(?:,\d{3})*)\s*KRW',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                price = match.group(1).replace(',', '')
                return price

        # 특수 케이스: "무료", "문의"
        if any(keyword in text for keyword in ['무료', '공짜']):
            return '무료'
        if any(keyword in text for keyword in ['문의', '별도', '상담']):
            return '문의'

        return None

    def crawl_gangnam_pool(self, url: str, pool_name: str) -> Dict:
        """강남구청 체육시설 페이지 크롤링"""
        result = {"url": url, "monthly_lesson_price": None, "free_swim_price": None}

        response = self.get(url)
        if not response:
            return result

        soup = BeautifulSoup(response.text, "html.parser")

        # 강남구청 사이트 구조에 맞게 셀렉터 작성
        # 예: 가격표가 테이블에 있는 경우
        tables = soup.find_all("table")
        for table in tables:
            text = table.get_text()

            # "수강료", "강습료", "이용료" 등 키워드 찾기
            if any(keyword in text for keyword in ['수강료', '강습료', '이용료', '회비']):
                # 한달 수강권
                if '1개월' in text or '한달' in text or '월' in text:
                    price = self.extract_price_from_text(text)
                    if price:
                        result['monthly_lesson_price'] = price

                # 자유수영
                if '자유수영' in text or '자율수영' in text:
                    price = self.extract_price_from_text(text)
                    if price:
                        result['free_swim_price'] = price

        # 리스트에서 찾기
        price_elements = soup.select(".price, .fee, .cost, dl, .info-list")
        for elem in price_elements:
            text = elem.get_text()
            if '수영' in text or '강습' in text:
                price = self.extract_price_from_text(text)
                if price and not result['monthly_lesson_price']:
                    result['monthly_lesson_price'] = price

        return result

    def crawl_generic_pool(self, url: str, pool_name: str) -> Dict:
        """일반적인 수영장 사이트 크롤링 (범용)"""
        result = {"url": url, "monthly_lesson_price": None, "free_swim_price": None}

        response = self.get(url)
        if not response:
            return result

        soup = BeautifulSoup(response.text, "html.parser")

        # 전략 1: 메타 태그에서 찾기
        meta_desc = soup.find("meta", {"name": "description"})
        if meta_desc and meta_desc.get("content"):
            price = self.extract_price_from_text(meta_desc["content"])
            if price:
                result['monthly_lesson_price'] = price

        # 전략 2: 가격 관련 클래스/ID 찾기
        price_selectors = [
            ".price", ".fee", ".cost", "#price", "#fee",
            "[class*='price']", "[class*='fee']", "[id*='price']"
        ]

        for selector in price_selectors:
            elements = soup.select(selector)
            for elem in elements:
                text = elem.get_text()
                if '수영' in text or '강습' in text or '이용' in text:
                    price = self.extract_price_from_text(text)
                    if price:
                        if '자유' in text or '자율' in text:
                            result['free_swim_price'] = price
                        else:
                            result['monthly_lesson_price'] = price

        # 전략 3: 전체 텍스트에서 패턴 매칭
        full_text = soup.get_text()

        # "수강료: 150,000원" 형태
        lesson_match = re.search(r'(?:수강료|강습료|회비)[:\s]*(\d{1,3}(?:,\d{3})*)\s*원', full_text)
        if lesson_match:
            result['monthly_lesson_price'] = lesson_match.group(1).replace(',', '')

        # "자유수영: 8,000원" 형태
        swim_match = re.search(r'(?:자유수영|자율수영)[:\s]*(\d{1,3}(?:,\d{3})*)\s*원', full_text)
        if swim_match:
            result['free_swim_price'] = swim_match.group(1).replace(',', '')

        return result

    def crawl_pool_website(self, url: str, pool_name: str) -> Dict:
        """수영장 웹사이트 크롤링 (도메인별 전략)"""
        if not url or url == "정보 없음":
            return {"url": None, "monthly_lesson_price": None, "free_swim_price": None}

        print(f"🔍 크롤링: {pool_name}")
        print(f"   URL: {url}")

        # URL 정규화
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # 도메인별 맞춤 크롤러
            if 'gangnam.go.kr' in domain:
                result = self.crawl_gangnam_pool(url, pool_name)
            elif 'gangdong.go.kr' in domain or 'gangbuk.go.kr' in domain:
                result = self.crawl_gangnam_pool(url, pool_name)  # 비슷한 구조
            else:
                result = self.crawl_generic_pool(url, pool_name)

            # 결과 출력
            if result['monthly_lesson_price'] or result['free_swim_price']:
                print(f"   ✅ 수강권: {result['monthly_lesson_price'] or '정보없음'}")
                print(f"   ✅ 자유수영: {result['free_swim_price'] or '정보없음'}")
            else:
                print(f"   ⚠️  가격 정보 없음")

            return result

        except Exception as e:
            print(f"   ❌ 오류: {str(e)[:50]}")
            return {"url": url, "monthly_lesson_price": None, "free_swim_price": None}

    def crawl_pools_from_db(self, limit: int = 10) -> List[Dict]:
        """DB에서 수영장 목록 가져와서 크롤링"""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from database.connection import get_db
        from app.models.swimming_pool import SwimmingPool

        db = next(get_db())

        # URL이 있는 수영장만
        pools = db.query(SwimmingPool).filter(
            SwimmingPool.url.isnot(None),
            SwimmingPool.url != '',
            SwimmingPool.url != '정보 없음'
        ).limit(limit).all()

        results = []

        print(f"\n{'='*70}")
        print(f"  🏊 {len(pools)}개 수영장 웹사이트 크롤링 시작")
        print(f"{'='*70}\n")

        for i, pool in enumerate(pools, 1):
            print(f"\n[{i}/{len(pools)}] {pool.name}")

            result = self.crawl_pool_website(pool.url, pool.name)
            result['pool_id'] = pool.id
            result['pool_name'] = pool.name
            results.append(result)

            # 예의 지키기
            time.sleep(random.uniform(1.0, 2.0))

        return results

    def update_db_with_results(self, results: List[Dict]):
        """크롤링 결과로 DB 업데이트"""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from database.connection import get_db
        from app.models.swimming_pool import SwimmingPool

        db = next(get_db())

        updated_count = 0

        for result in results:
            if not result.get('pool_id'):
                continue

            pool = db.query(SwimmingPool).filter(
                SwimmingPool.id == result['pool_id']
            ).first()

            if not pool:
                continue

            updated = False

            # 가격 정보 업데이트 (문자열로 저장)
            if result.get('monthly_lesson_price'):
                pool.monthly_lesson_price = str(result['monthly_lesson_price'])
                updated = True

            if result.get('free_swim_price'):
                pool.free_swim_price = str(result['free_swim_price'])
                updated = True

            if updated:
                updated_count += 1

        db.commit()

        print(f"\n{'='*70}")
        print(f"  ✅ {updated_count}개 수영장 가격 정보 업데이트 완료")
        print(f"{'='*70}")

        return updated_count


def main():
    print("\n" + "="*70)
    print("  🏊 스마트 수영장 크롤러 (ChatGPT 가이드 적용)")
    print("="*70)

    crawler = SmartPoolCrawler()

    # 샘플: 처음 10개만 테스트
    results = crawler.crawl_pools_from_db(limit=10)

    # 결과 저장
    with open('crawl_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 결과 저장: crawl_results.json")

    # DB 업데이트
    updated = crawler.update_db_with_results(results)

    print(f"\n📊 통계:")
    print(f"   - 시도: {len(results)}개")
    print(f"   - 성공: {sum(1 for r in results if r.get('monthly_lesson_price') or r.get('free_swim_price'))}개")
    print(f"   - 업데이트: {updated}개")


if __name__ == "__main__":
    main()
