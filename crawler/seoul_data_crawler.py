# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
import sqlite3
from typing import List, Dict, Optional
import time

class SeoulPoolDataCrawler:
    """서울 열린데이터광장 API로 공공 수영장 실제 가격 정보 수집"""

    def __init__(self):
        # 서울 열린데이터광장 API 키
        # 발급: https://data.seoul.go.kr/
        self.api_key = "5670664b7a6c756e34326763574758"  # 샘플 키 (실제 키로 교체 필요)

    def get_public_sports_facilities(self) -> List[Dict]:
        """서울시 체육시설 공공서비스예약 정보 가져오기"""
        pools = []

        try:
            # API 엔드포인트: http://openapi.seoul.go.kr:8088/{KEY}/json/ListPublicReservationSport/1/1000/
            url = f"http://openapi.seoul.go.kr:8088/{self.api_key}/json/ListPublicReservationSport/1/1000/"

            print(f"서울 열린데이터광장 API 호출 중...")
            response = requests.get(url, timeout=30)

            if response.status_code == 200:
                data = response.json()

                # API 결과 확인
                result = data.get("ListPublicReservationSport")
                if not result:
                    print("✗ API 응답에 데이터가 없습니다")
                    print(f"응답: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}...")
                    return pools

                code = result.get("RESULT", {}).get("CODE")
                if code != "INFO-000":
                    print(f"✗ API 오류: {result.get('RESULT', {}).get('MESSAGE')}")
                    return pools

                items = result.get("row", [])
                print(f"✓ {len(items)}개 시설 발견")

                for item in items:
                    facility_name = item.get("SVCNM", "")

                    # 수영장 관련 시설만 필터링
                    if "수영" not in facility_name:
                        continue

                    # 가격 정보 추출
                    pay_info = item.get("PAYATNM", "")  # 이용 요금 정보
                    usage_info = item.get("USETGTINFO", "")  # 이용 대상

                    pool_data = {
                        "name": facility_name,
                        "service_id": item.get("SVCID", ""),
                        "category": item.get("MINCLASSNM", ""),  # 소분류명
                        "place_name": item.get("PLACENM", ""),  # 장소명 (주소)
                        "usage_target": usage_info,
                        "pay_info": pay_info,
                        "start_time": item.get("SVCOPNBGNDT", ""),  # 서비스 개시 시작일
                        "end_time": item.get("SVCOPNENDDT", ""),  # 서비스 개시 종료일
                        "url": item.get("SVCURL", ""),  # 서비스 URL
                        "x": item.get("X", ""),  # 경도
                        "y": item.get("Y", ""),  # 위도
                        "phone": item.get("TELNO", ""),
                    }

                    pools.append(pool_data)
                    print(f"  ✓ {facility_name} - {pay_info[:30]}...")

            else:
                print(f"✗ API 호출 실패: HTTP {response.status_code}")
                print(f"응답: {response.text[:200]}...")

        except Exception as e:
            print(f"✗ 서울 공공데이터 API 오류: {str(e)}")

        return pools

    def extract_price_from_payinfo(self, pay_info: str) -> Optional[int]:
        """이용 요금 정보에서 가격 추출"""
        import re

        # "유료 3,500원" 같은 패턴
        patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*원',  # 3,500원 or 3500원
            r'(\d+)\s*만\s*원',             # 1만원
        ]

        for pattern in patterns:
            match = re.search(pattern, pay_info)
            if match:
                price_str = match.group(1).replace(',', '')
                if '만' in pay_info[match.start():match.end()+3]:
                    return int(price_str) * 10000
                return int(price_str)

        return None

    def update_database(self, pools: List[Dict]):
        """DB에 공공 수영장 가격 정보 업데이트"""
        conn = sqlite3.connect('swimming_pools.db')
        cursor = conn.cursor()

        updated_count = 0
        not_found_count = 0

        print(f"\n📊 DB 업데이트 중...\n")

        for pool_data in pools:
            name = pool_data["name"]
            pay_info = pool_data["pay_info"]
            url = pool_data["url"]
            phone = pool_data["phone"]

            # 이름으로 수영장 찾기
            cursor.execute('SELECT id, name FROM swimming_pools WHERE name LIKE ?', (f'%{name}%',))
            result = cursor.fetchone()

            if not result:
                print(f"✗ DB에 없음: {name}")
                not_found_count += 1
                continue

            pool_id, db_name = result

            # 가격 추출
            price = self.extract_price_from_payinfo(pay_info)

            updates = []
            params = []

            if url:
                updates.append("url = ?")
                params.append(url)

            if phone and phone != "":
                updates.append("phone = ?")
                params.append(phone)

            if price and 1000 <= price <= 30000:
                updates.append("free_swim_price = ?")
                params.append(str(price))
                print(f"✓ {db_name}: {price:,}원")
            else:
                print(f"⚠️  {db_name}: 가격 정보 없음 ({pay_info[:30]}...)")

            if updates:
                params.append(pool_id)
                query = f"UPDATE swimming_pools SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                updated_count += 1

        conn.commit()
        conn.close()

        print(f"\n{'='*60}")
        print(f"✅ 업데이트 완료")
        print(f"  • 업데이트: {updated_count}개")
        print(f"  • DB에 없음: {not_found_count}개")
        print(f"{'='*60}")

if __name__ == "__main__":
    print("🏊 서울시 공공 수영장 가격 크롤러\n")
    print("ℹ️  서울 열린데이터광장 API 사용\n")

    crawler = SeoulPoolDataCrawler()

    # 1단계: 공공 체육시설 데이터 가져오기
    pools = crawler.get_public_sports_facilities()

    if pools:
        print(f"\n✓ {len(pools)}개 수영장 발견\n")

        # 2단계: DB 업데이트
        crawler.update_database(pools)
    else:
        print("\n⚠️  API에서 수영장 데이터를 가져오지 못했습니다")
        print("   → API 키를 확인하세요: https://data.seoul.go.kr/")
