# -*- coding: utf-8 -*-
"""
API 키 없이 작동하는 웹 크롤러
Selenium을 사용하여 실제 웹페이지를 크롤링
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict
import json

class WebScraper:
    def __init__(self, headless=True):
        """
        Selenium 웹드라이버 초기화
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        self.wait = WebDriverWait(self.driver, 10)

    def __del__(self):
        """드라이버 종료"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def search_naver_pools(self, query="수영장", region="서울", max_results=50) -> List[Dict]:
        """
        네이버 지도에서 수영장 검색
        """
        print(f"\n🔍 네이버 지도 검색: {region} {query}")

        search_url = f"https://map.naver.com/p/search/{region} {query}"
        self.driver.get(search_url)
        time.sleep(3)

        pools = []

        try:
            # iframe으로 전환
            self.driver.switch_to.frame('searchIframe')
            time.sleep(2)

            # 스크롤하여 더 많은 결과 로드
            scroll_container = self.driver.find_element(By.CSS_SELECTOR, '.Ryr1F')

            for i in range(5):  # 5번 스크롤
                self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scroll_container)
                time.sleep(1)

            # 검색 결과 파싱
            results = self.driver.find_elements(By.CSS_SELECTOR, '.CHC5F')

            print(f"  찾은 결과: {len(results)}개")

            for idx, result in enumerate(results[:max_results]):
                try:
                    # 기본 정보 추출
                    name_elem = result.find_element(By.CSS_SELECTOR, '.TYaxT')
                    name = name_elem.text.strip()

                    # 주소
                    try:
                        address_elem = result.find_element(By.CSS_SELECTOR, '.LDgIH')
                        address = address_elem.text.strip()
                    except:
                        address = ""

                    # 전화번호
                    try:
                        phone_elem = result.find_element(By.CSS_SELECTOR, '.dry0B')
                        phone = phone_elem.text.strip()
                    except:
                        phone = ""

                    # 평점
                    try:
                        rating_elem = result.find_element(By.CSS_SELECTOR, '.PXMot')
                        rating_text = rating_elem.text.strip()
                        rating = float(rating_text.split()[0]) if rating_text else None
                    except:
                        rating = None

                    pool_data = {
                        "name": name,
                        "address": address,
                        "phone": phone,
                        "rating": rating,
                        "source": "네이버지도_웹크롤링",
                        "lat": None,  # 좌표는 상세페이지에서 추출 가능
                        "lng": None
                    }

                    pools.append(pool_data)

                    if (idx + 1) % 10 == 0:
                        print(f"  진행중... {idx + 1}개 수집")

                except Exception as e:
                    continue

            self.driver.switch_to.default_content()

        except Exception as e:
            print(f"  ⚠️ 크롤링 오류: {e}")

        print(f"  ✅ 총 {len(pools)}개 수집 완료")
        return pools

    def search_kakao_pools(self, query="수영장", region="서울", max_pages=3) -> List[Dict]:
        """
        카카오맵에서 수영장 검색
        """
        print(f"\n🔍 카카오맵 검색: {region} {query}")

        search_url = f"https://map.kakao.com/?q={region}+{query}"
        self.driver.get(search_url)
        time.sleep(3)

        pools = []

        try:
            # 검색 결과 리스트로 이동
            results_tab = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '#info\\.search\\.place\\.list'))
            )

            for page in range(1, max_pages + 1):
                print(f"  페이지 {page} 크롤링 중...")

                # 현재 페이지 결과 파싱
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                place_list = soup.select('.placelist > .PlaceItem')

                for item in place_list:
                    try:
                        # 이름
                        name_elem = item.select_one('.head_item .tit_name .link_name')
                        name = name_elem.text.strip() if name_elem else ""

                        # 주소
                        address_elem = item.select_one('.info_item .addr p')
                        address = address_elem.text.strip() if address_elem else ""

                        # 전화번호
                        phone_elem = item.select_one('.info_item .contact_item .txt_contact')
                        phone = phone_elem.text.strip() if phone_elem else ""

                        # 카테고리
                        category_elem = item.select_one('.head_item .subcategory')
                        category = category_elem.text.strip() if category_elem else ""

                        pool_data = {
                            "name": name,
                            "address": address,
                            "phone": phone,
                            "category": category,
                            "source": "카카오맵_웹크롤링",
                            "lat": None,
                            "lng": None
                        }

                        pools.append(pool_data)

                    except Exception as e:
                        continue

                # 다음 페이지 버튼 클릭
                if page < max_pages:
                    try:
                        next_button = self.driver.find_element(By.CSS_SELECTOR, f'#info\\.search\\.page\\.next')
                        if 'disabled' not in next_button.get_attribute('class'):
                            next_button.click()
                            time.sleep(2)
                        else:
                            break
                    except:
                        break

        except Exception as e:
            print(f"  ⚠️ 크롤링 오류: {e}")

        print(f"  ✅ 총 {len(pools)}개 수집 완료")
        return pools

    def crawl_all_regions(self, regions=None) -> List[Dict]:
        """
        여러 지역의 수영장 크롤링
        """
        if regions is None:
            regions = [
                "서울", "경기", "인천",
                "부산", "대구", "광주", "대전", "울산",
                "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"
            ]

        all_pools = []
        seen = set()

        for region in regions:
            print(f"\n{'='*50}")
            print(f"📍 지역: {region}")
            print('='*50)

            # 네이버 크롤링
            try:
                naver_pools = self.search_naver_pools(query="수영장", region=region, max_results=30)

                for pool in naver_pools:
                    key = f"{pool['name']}_{pool['address']}"
                    if key not in seen:
                        seen.add(key)
                        all_pools.append(pool)
            except Exception as e:
                print(f"  ❌ 네이버 크롤링 실패: {e}")

            time.sleep(2)

            # 카카오 크롤링은 구조가 복잡하여 일단 네이버만 진행
            # 필요시 추가 구현

        return all_pools

def save_to_json(data: List[Dict], filename="crawled_pools.json"):
    """수집 데이터 JSON 저장"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n💾 데이터 저장 완료: {filename}")

if __name__ == "__main__":
    print("="*60)
    print("🏊 한국 수영장 웹 크롤러 시작")
    print("="*60)

    scraper = WebScraper(headless=False)  # 브라우저 보이게 설정

    try:
        # 서울만 테스트
        pools = scraper.search_naver_pools(query="수영장", region="서울", max_results=50)

        # JSON 파일로 저장
        save_to_json(pools, "seoul_pools.json")

        print(f"\n✅ 크롤링 완료! 총 {len(pools)}개 수영장 수집")

        # 샘플 출력
        if pools:
            print("\n📋 샘플 데이터:")
            for i, pool in enumerate(pools[:3], 1):
                print(f"\n{i}. {pool['name']}")
                print(f"   주소: {pool['address']}")
                print(f"   전화: {pool['phone']}")
                print(f"   평점: {pool['rating']}")

    finally:
        del scraper
