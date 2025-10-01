import requests
from typing import List, Dict
import time

class KakaoMapCrawler:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://dapi.kakao.com/v2/local/search/keyword.json"

    def search_pools(self, query: str = "수영장", page: int = 1, size: int = 15) -> Dict:
        """
        카카오 로컬 검색 API로 수영장 검색
        """
        headers = {"Authorization": f"KakaoAK {self.api_key}"}

        params = {
            "query": query,
            "page": page,
            "size": size,
            "sort": "accuracy"
        }

        try:
            response = requests.get(self.base_url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching data from Kakao: {e}")
            return {"documents": [], "meta": {}}

    def parse_pool_data(self, item: Dict) -> Dict:
        """
        카카오 검색 결과를 DB 스키마에 맞게 변환
        """
        return {
            "name": item.get("place_name", ""),
            "address": item.get("road_address_name") or item.get("address_name", ""),
            "lat": float(item.get("y", 0)) if item.get("y") else None,
            "lng": float(item.get("x", 0)) if item.get("x") else None,
            "phone": item.get("phone", ""),
            "source": "카카오",
            "url": item.get("place_url", ""),
        }

    def crawl_all_pools(self) -> List[Dict]:
        """
        전국 수영장 데이터 크롤링
        """
        queries = [
            "수영장",
            "실내수영장",
            "스포츠센터",
            "수영 레슨",
        ]

        all_pools = []
        seen = set()

        for query in queries:
            print(f"Searching for: {query}")
            page = 1
            max_page = 45  # 카카오 API 최대 45페이지

            while page <= max_page:
                data = self.search_pools(query, page=page)
                documents = data.get("documents", [])

                if not documents:
                    break

                for item in documents:
                    pool_data = self.parse_pool_data(item)
                    key = f"{pool_data['name']}_{pool_data['address']}"

                    if key not in seen:
                        seen.add(key)
                        all_pools.append(pool_data)

                # 메타 정보로 마지막 페이지 확인
                meta = data.get("meta", {})
                if meta.get("is_end", True):
                    break

                page += 1
                time.sleep(0.3)  # API 호출 제한 고려

            time.sleep(1)

        print(f"Total pools found from Kakao: {len(all_pools)}")
        return all_pools
