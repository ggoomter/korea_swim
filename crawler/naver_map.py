import requests
from typing import List, Dict
import time

class NaverMapCrawler:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://openapi.naver.com/v1/search/local.json"

    def search_pools(self, query: str = "수영장", display: int = 100) -> List[Dict]:
        """
        네이버 지역 검색 API로 수영장 검색
        """
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }

        all_results = []
        start = 1

        while start <= 1000:  # 네이버 API 최대 1000개
            params = {
                "query": query,
                "display": display,
                "start": start,
                "sort": "random"
            }

            try:
                response = requests.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()

                items = data.get("items", [])
                if not items:
                    break

                all_results.extend(items)
                start += display

                # API 호출 제한 고려
                time.sleep(0.1)

            except Exception as e:
                print(f"Error fetching data from Naver: {e}")
                break

        return all_results

    def parse_pool_data(self, item: Dict) -> Dict:
        """
        네이버 검색 결과를 DB 스키마에 맞게 변환
        """
        # HTML 태그 제거
        name = item.get("title", "").replace("<b>", "").replace("</b>", "")
        address = item.get("roadAddress") or item.get("address", "")

        # 좌표 변환 (네이버 좌표계 -> WGS84)
        # mapx, mapy는 카텍 좌표계이므로 변환 필요
        mapx = int(item.get("mapx", 0)) / 10000000
        mapy = int(item.get("mapy", 0)) / 10000000

        return {
            "name": name,
            "address": address,
            "lng": mapx if mapx != 0 else None,
            "lat": mapy if mapy != 0 else None,
            "phone": item.get("telephone", ""),
            "source": "네이버",
            "url": item.get("link", ""),
        }

    def crawl_all_pools(self) -> List[Dict]:
        """
        전국 수영장 데이터 크롤링
        """
        queries = [
            "수영장",
            "실내수영장",
            "스포츠센터 수영장",
            "헬스장 수영장",
            "아쿠아로빅"
        ]

        all_pools = []
        seen = set()  # 중복 제거용

        for query in queries:
            print(f"Searching for: {query}")
            results = self.search_pools(query)

            for item in results:
                pool_data = self.parse_pool_data(item)
                # 이름+주소로 중복 체크
                key = f"{pool_data['name']}_{pool_data['address']}"
                if key not in seen:
                    seen.add(key)
                    all_pools.append(pool_data)

            time.sleep(1)  # 쿼리 간 딜레이

        print(f"Total pools found: {len(all_pools)}")
        return all_pools
