# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from bs4 import BeautifulSoup
import re

def test_crawl_pool(url, pool_name):
    """단일 수영장 웹사이트 크롤링 테스트"""
    print(f"\n{'='*80}")
    print(f"수영장: {pool_name}")
    print(f"URL: {url}")
    print(f"{'='*80}\n")

    try:
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        response = session.get(url, timeout=10)
        response.encoding = 'utf-8'

        if response.status_code != 200:
            print(f"✗ HTTP {response.status_code}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)

        # 가격 관련 키워드 찾기
        price_keywords = ['이용료', '이용요금', '요금', '가격', '수강료', '회비', '자유수영', '자율수영', '1회 이용']

        print("📋 페이지 내용 분석:")
        print("-" * 80)

        lines = [line.strip() for line in text.split('\n') if line.strip()]

        found_price_section = False
        for i, line in enumerate(lines):
            # 가격 키워드가 있는 줄 찾기
            if any(keyword in line for keyword in price_keywords):
                found_price_section = True
                print(f"\n✓ 가격 관련 섹션 발견:")
                print(f"  {line}")

                # 다음 10줄 출력
                for j in range(i+1, min(i+11, len(lines))):
                    print(f"  {lines[j]}")

                print()

        if not found_price_section:
            print("✗ 가격 정보를 찾을 수 없음")
            print("\n전체 텍스트 샘플 (처음 1000자):")
            print(text[:1000])

    except Exception as e:
        print(f"✗ 크롤링 실패: {str(e)}")

# 테스트할 수영장 목록
test_pools = [
    ("강남구민체육센터 수영장", "https://life.gangnam.go.kr/fmcs/63?action-value=dbb6e4d860c490948f61ebe14efbe8d5"),
    ("관악구민체육센터", "https://www.gwanakgongdan.or.kr/www/1399?action=read&action-value=e29063ab66ce01f9f3d5e6a1c5c27cbb"),
]

for name, url in test_pools:
    test_crawl_pool(url, name)
