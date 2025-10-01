import requests
from typing import List, Dict
import time
import xml.etree.ElementTree as ET

class PublicDataCrawler:
    """
    공공데이터포털 체육시설 정보 API
    https://www.data.go.kr/
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        # 실제 API URL은 발급받은 후 설정 필요
        self.base_url = "http://api.data.go.kr/openapi/tn_pubr_public_sport_faclt_api"

    def get_facilities(self, page_no: int = 1, num_of_rows: int = 100) -> Dict:
        """
        공공 체육시설 정보 조회
        """
        params = {
            "serviceKey": self.api_key,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
            "type": "json"  # 또는 xml
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            # JSON 응답 처리
            if "json" in params["type"]:
                return response.json()
            else:
                # XML 응답 처리
                return self.parse_xml(response.text)

        except Exception as e:
            print(f"Error fetching public data: {e}")
            return {"items": []}

    def parse_xml(self, xml_text: str) -> Dict:
        """XML 응답 파싱"""
        try:
            root = ET.fromstring(xml_text)
            items = []

            for item in root.findall(".//item"):
                item_dict = {}
                for child in item:
                    item_dict[child.tag] = child.text
                items.append(item_dict)

            return {"items": items}
        except Exception as e:
            print(f"Error parsing XML: {e}")
            return {"items": []}

    def parse_pool_data(self, item: Dict) -> Dict:
        """
        공공데이터를 DB 스키마에 맞게 변환
        """
        # 공공데이터 필드명은 실제 API 응답에 따라 조정 필요
        return {
            "name": item.get("faciNm") or item.get("fcltyNm", ""),
            "address": item.get("rdnmadr") or item.get("lnmadr", ""),
            "lat": float(item.get("latitude", 0)) if item.get("latitude") else None,
            "lng": float(item.get("longitude", 0)) if item.get("longitude") else None,
            "phone": item.get("phoneNumber") or item.get("telno", ""),
            "operating_hours": self.parse_operating_hours(item),
            "facilities": self.parse_facilities(item),
            "source": "공공데이터",
            "url": item.get("homepageUrl", ""),
        }

    def parse_operating_hours(self, item: Dict) -> Dict:
        """운영시간 파싱"""
        # 실제 데이터 구조에 따라 구현
        return {}

    def parse_facilities(self, item: Dict) -> List[str]:
        """시설정보 파싱"""
        facilities = []
        if item.get("parkingLotCnt"):
            facilities.append("주차장")
        return facilities

    def crawl_all_pools(self) -> List[Dict]:
        """
        전국 공공 수영장 데이터 크롤링
        """
        all_pools = []
        page = 1
        max_pages = 100  # 안전장치

        while page <= max_pages:
            print(f"Fetching page {page}...")
            data = self.get_facilities(page_no=page, num_of_rows=100)

            items = data.get("items", [])
            if not items:
                break

            for item in items:
                # 수영장만 필터링
                facility_type = item.get("fcltyNm", "").lower()
                if "수영" in facility_type or "pool" in facility_type:
                    pool_data = self.parse_pool_data(item)
                    all_pools.append(pool_data)

            page += 1
            time.sleep(0.5)

        print(f"Total public pools found: {len(all_pools)}")
        return all_pools
