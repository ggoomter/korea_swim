# -*- coding: utf-8 -*-
"""
LLM 기반 수영장 데이터 추출기

웹사이트 크롤링 → Claude Haiku로 구조화 JSON 추출 → DB 저장

사용법:
  python crawler/llm_enricher.py                      # 전체 실행
  python crawler/llm_enricher.py --test 5 --dry-run   # 5건 테스트 (DB 저장 없이)
  python crawler/llm_enricher.py --id 42              # 특정 수영장만
  python crawler/llm_enricher.py --retry-failed       # 실패한 것만 재시도

환경변수:
  ANTHROPIC_API_KEY (필수)
  NAVER_CLIENT_ID, NAVER_CLIENT_SECRET (2차 검색용, 선택)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import argparse
import json
import time
import re
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv
load_dotenv()
from bs4 import BeautifulSoup
import anthropic


# LLM에 전달할 JSON 추출 스키마
EXTRACTION_SCHEMA = """{
  "pricing": {
    "일일권": {
      "성인": {"평일": null, "주말": null},
      "청소년": {"평일": null, "주말": null},
      "어린이": {"평일": null, "주말": null},
      "경로": {"평일": null, "주말": null}
    },
    "자유수영": {
      "성인": {"평일": null, "주말": null},
      "청소년": {"평일": null, "주말": null},
      "어린이": {"평일": null, "주말": null},
      "경로": {"평일": null, "주말": null}
    },
    "강습_월": {"성인": null, "청소년": null}
  },
  "free_swim_schedule": {
    "월": ["HH:MM-HH:MM"],
    "화": [], "수": [], "목": [], "금": [], "토": [], "일": [],
    "휴관": "매월 첫째 일요일"
  },
  "operating_hours": {
    "월": "HH:MM-HH:MM", "화": "", "수": "", "목": "", "금": "",
    "토": "HH:MM-HH:MM", "일": "HH:MM-HH:MM"
  },
  "phone": "02-XXX-XXXX",
  "lanes": 8,
  "pool_size": "25m x 6레인",
  "parking": true,
  "notes": "비고 사항 (휴관일, 예약방법 등)"
}"""

# 시스템 프롬프트
SYSTEM_PROMPT = """당신은 수영장 웹페이지에서 정보를 추출하는 전문가입니다.
주어진 텍스트에서 정보를 정확히 추출하여 JSON으로 반환하세요.

규칙:
1. 정보가 없으면 반드시 null로 남기세요. 추측하지 마세요.
2. 가격은 반드시 정수(원 단위)로 변환하세요. 예: "3,400원" → 3400
3. 시간은 "HH:MM-HH:MM" 형식으로 변환하세요. 예: "오전 6시~오후 10시" → "06:00-22:00"
4. 자유수영 시간표는 요일별로 분리하세요. 평일이 같으면 월~금 모두 같은 값을 넣으세요.
5. 비어있는 카테고리(가격이 모두 null인 경우)는 해당 키 자체를 null로 반환하세요.
6. 반드시 유효한 JSON만 반환하세요. 설명 텍스트 없이 JSON만 출력하세요."""

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "swimming_pools.db")


class LLMPoolEnricher:
    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY 환경변수를 설정하세요.")
            sys.exit(1)

        self.client = anthropic.Anthropic(api_key=api_key)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

        # 네이버 API (2차 검색용, 선택)
        self.naver_client_id = os.environ.get("NAVER_CLIENT_ID")
        self.naver_client_secret = os.environ.get("NAVER_CLIENT_SECRET")

        if self.naver_client_id:
            print("  Naver API 활성화 (2차 검색)")
        else:
            print("  Naver API 미설정 (웹사이트만 크롤링)")

    def crawl_website(self, url: str) -> Optional[str]:
        """웹사이트 HTML 크롤링 → 텍스트 추출"""
        try:
            response = self.session.get(url, timeout=15)
            response.encoding = "utf-8"
            if response.status_code != 200:
                return None

            # 5MB 제한
            if len(response.content) > 5 * 1024 * 1024:
                return None

            soup = BeautifulSoup(response.text, "html.parser")

            # 불필요한 태그 제거
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True)

            # 빈 줄 정리, 최대 8000자 제한 (토큰 절약)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)[:8000]

            return text if len(text) > 50 else None

        except Exception as e:
            print(f"    ! 크롤링 실패: {str(e)[:50]}")
            return None

    def search_naver_web(self, pool_name: str) -> Optional[str]:
        """네이버 웹검색으로 보충 정보 수집"""
        if not self.naver_client_id:
            return None

        try:
            query = f"{pool_name} 자유수영 가격 시간표"
            response = requests.get(
                "https://openapi.naver.com/v1/search/webkr.json",
                headers={
                    "X-Naver-Client-Id": self.naver_client_id,
                    "X-Naver-Client-Secret": self.naver_client_secret,
                },
                params={"query": query, "display": 3},
            )

            if response.status_code != 200:
                return None

            items = response.json().get("items", [])
            texts = []
            for item in items:
                title = item.get("title", "").replace("<b>", "").replace("</b>", "")
                desc = item.get("description", "").replace("<b>", "").replace("</b>", "")
                url = item.get("link", "")
                texts.append(f"제목: {title}\n내용: {desc}\nURL: {url}")

                # 상위 결과의 웹사이트도 크롤링 시도
                exclude = ["blog", "cafe", "post", "news"]
                if not any(kw in url.lower() for kw in exclude):
                    page_text = self.crawl_website(url)
                    if page_text:
                        texts.append(f"--- 페이지 내용 ---\n{page_text[:3000]}")
                        break  # 첫 번째 유효 페이지만

            time.sleep(0.2)
            combined = "\n\n".join(texts)
            return combined[:8000] if combined else None

        except Exception as e:
            print(f"    ! 네이버 검색 실패: {str(e)[:50]}")
            return None

    def extract_with_llm(self, text: str, pool_name: str) -> Optional[Dict]:
        """Claude Haiku에 텍스트 전달 → 구조화 JSON 추출"""
        user_prompt = f"""이 수영장 웹페이지에서 다음 정보를 JSON으로 추출하세요.
정보가 없으면 반드시 null로 남기세요. 추측하지 마세요.

수영장: {pool_name}

추출할 JSON 스키마:
{EXTRACTION_SCHEMA}

웹페이지 텍스트:
{text}"""

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=2048,
                temperature=0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            result_text = response.content[0].text.strip()

            # JSON 블록 추출 (```json ... ``` 형태 처리)
            json_match = re.search(r"```json\s*(.*?)\s*```", result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(1)

            # JSON 파싱
            data = json.loads(result_text)
            return data

        except json.JSONDecodeError as e:
            print(f"    ! JSON 파싱 실패: {str(e)[:50]}")
            return None
        except anthropic.APIError as e:
            print(f"    ! Claude API 에러: {str(e)}")
            return None

    def validate_result(self, data: Dict) -> Dict:
        """JSON 스키마 검증 + 정규화"""
        validated = {}

        # pricing 검증
        pricing = data.get("pricing")
        if isinstance(pricing, dict):
            clean_pricing = {}
            for category, targets in pricing.items():
                if targets is None:
                    continue
                if isinstance(targets, dict):
                    clean_targets = {}
                    for target, prices in targets.items():
                        if prices is None:
                            continue
                        if isinstance(prices, dict):
                            clean_prices = {}
                            for day_type, price in prices.items():
                                if isinstance(price, (int, float)) and 500 <= price <= 500000:
                                    clean_prices[day_type] = int(price)
                            if clean_prices:
                                clean_targets[target] = clean_prices
                        elif isinstance(prices, (int, float)) and 500 <= prices <= 500000:
                            clean_targets[target] = int(prices)
                    if clean_targets:
                        clean_pricing[category] = clean_targets
            if clean_pricing:
                validated["pricing"] = clean_pricing

        # free_swim_schedule 검증
        schedule = data.get("free_swim_schedule")
        if isinstance(schedule, dict):
            clean_schedule = {}
            day_keys = {"월", "화", "수", "목", "금", "토", "일"}
            time_pattern = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")
            for key, value in schedule.items():
                if key == "휴관" and isinstance(value, str):
                    clean_schedule["휴관"] = value
                elif key in day_keys and isinstance(value, list):
                    valid_times = [t for t in value if isinstance(t, str) and time_pattern.match(t)]
                    if valid_times:
                        clean_schedule[key] = valid_times
            if clean_schedule:
                validated["free_swim_schedule"] = clean_schedule

        # operating_hours 검증
        hours = data.get("operating_hours")
        if isinstance(hours, dict):
            clean_hours = {}
            time_range_pattern = re.compile(r"^\d{2}:\d{2}-\d{2}:\d{2}$")
            day_keys = {"월", "화", "수", "목", "금", "토", "일"}
            for key, value in hours.items():
                if key in day_keys and isinstance(value, str):
                    if time_range_pattern.match(value) or value in ("휴관", ""):
                        clean_hours[key] = value
            if clean_hours:
                validated["operating_hours"] = clean_hours

        # 단순 필드 검증
        phone = data.get("phone")
        if isinstance(phone, str) and re.match(r"^0\d{1,2}-\d{3,4}-\d{4}$", phone):
            validated["phone"] = phone

        lanes = data.get("lanes")
        if isinstance(lanes, int) and 1 <= lanes <= 50:
            validated["lanes"] = lanes

        pool_size = data.get("pool_size")
        if isinstance(pool_size, str) and len(pool_size) <= 50:
            validated["pool_size"] = pool_size

        parking = data.get("parking")
        if isinstance(parking, bool):
            validated["parking"] = parking

        notes = data.get("notes")
        if isinstance(notes, str) and len(notes) <= 500 and notes != "비고 사항":
            validated["notes"] = notes

        return validated

    def update_db(self, cursor, pool_id: int, data: Dict):
        """검증된 데이터를 DB에 UPDATE"""
        updates = []
        params = []

        field_map = {
            "pricing": json.dumps,
            "free_swim_schedule": json.dumps,
            "operating_hours": json.dumps,
            "phone": str,
            "lanes": int,
            "pool_size": str,
            "parking": bool,
            "notes": str,
        }

        for field, converter in field_map.items():
            if field in data:
                value = data[field]
                if converter in (json.dumps,):
                    value = json.dumps(value, ensure_ascii=False)
                updates.append(f"{field} = ?")
                params.append(value)

        # 상태 업데이트
        updates.append("enrichment_status = ?")
        params.append("success")
        updates.append("last_enriched = ?")
        params.append(datetime.now().isoformat())

        params.append(pool_id)
        sql = f"UPDATE swimming_pools SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(sql, params)

    def enrich_pool(self, pool_id: int, name: str, url: str, cursor, dry_run: bool = False) -> bool:
        """단일 수영장 데이터 추출 파이프라인"""

        # 1차: 웹사이트 크롤링
        text = None
        if url and url not in ("", "null", "None"):
            print(f"  → 웹사이트 크롤링...")
            text = self.crawl_website(url)
            if text:
                print(f"    ({len(text)}자 추출)")

        # 2차: 네이버 검색 (1차 실패 시)
        if not text:
            print(f"  → 네이버 웹검색...")
            text = self.search_naver_web(name)
            if text:
                print(f"    ({len(text)}자 추출)")

        if not text:
            print(f"  ! 텍스트 추출 실패")
            if not dry_run:
                cursor.execute(
                    "UPDATE swimming_pools SET enrichment_status = ?, last_enriched = ? WHERE id = ?",
                    ("failed", datetime.now().isoformat(), pool_id)
                )
            return False

        # LLM 추출
        print(f"  → Claude Haiku 추출 중...")
        raw_data = self.extract_with_llm(text, name)
        if not raw_data:
            print(f"  ! LLM 추출 실패")
            if not dry_run:
                cursor.execute(
                    "UPDATE swimming_pools SET enrichment_status = ?, last_enriched = ? WHERE id = ?",
                    ("failed", datetime.now().isoformat(), pool_id)
                )
            return False

        # 검증
        validated = self.validate_result(raw_data)
        if not validated:
            print(f"  ! 검증 통과 데이터 없음")
            if not dry_run:
                cursor.execute(
                    "UPDATE swimming_pools SET enrichment_status = ?, last_enriched = ? WHERE id = ?",
                    ("failed", datetime.now().isoformat(), pool_id)
                )
            return False

        # 결과 출력
        for key, val in validated.items():
            if key == "pricing":
                print(f"    pricing: {json.dumps(val, ensure_ascii=False)[:80]}...")
            elif key == "free_swim_schedule":
                day_count = len([k for k in val if k != "휴관"])
                print(f"    free_swim_schedule: {day_count}일")
            else:
                print(f"    {key}: {val}")

        # DB 저장
        if dry_run:
            print(f"  [DRY-RUN] {len(validated)}개 필드 업데이트 예정")
        else:
            self.update_db(cursor, pool_id, validated)
            print(f"  DB 업데이트 완료 ({len(validated)}개 필드)")

        return True

    def enrich_all(self, test_count: int = 0, dry_run: bool = False,
                   pool_id: Optional[int] = None, retry_failed: bool = False):
        """메인 루프: DB 조회 → 크롤링 → LLM → 검증 → 저장"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        try:
            # 대상 수영장 조회
            if pool_id:
                cursor.execute(
                    "SELECT id, name, url FROM swimming_pools WHERE id = ?",
                    (pool_id,)
                )
            elif retry_failed:
                cursor.execute(
                    "SELECT id, name, url FROM swimming_pools WHERE enrichment_status = 'failed' ORDER BY id"
                )
            else:
                cursor.execute(
                    "SELECT id, name, url FROM swimming_pools WHERE enrichment_status != 'success' ORDER BY id"
                )

            pools = cursor.fetchall()

            if test_count > 0:
                pools = pools[:test_count]

            total = len(pools)
            mode_label = " [DRY-RUN]" if dry_run else ""

            print(f"\n{'='*60}")
            print(f"  LLM 데이터 추출{mode_label}")
            print(f"  대상: {total}건")
            print(f"{'='*60}\n")

            stats = {"success": 0, "failed": 0, "skipped": 0}

            for i, (pid, name, url) in enumerate(pools):
                print(f"[{i+1}/{total}] {name} (ID: {pid})")

                success = self.enrich_pool(pid, name, url, cursor, dry_run)

                if success:
                    stats["success"] += 1
                else:
                    stats["failed"] += 1

                if not dry_run:
                    conn.commit()

                # API 속도 제한 방지
                time.sleep(1)
                print()

            # 결과 요약
            print(f"{'='*60}")
            print(f"  추출 완료{mode_label}")
            print(f"  성공: {stats['success']}건")
            print(f"  실패: {stats['failed']}건")
            print(f"{'='*60}\n")

        except Exception as e:
            print(f"\n  에러 발생: {e}")
            raise
        finally:
            conn.close()


def main():
    parser = argparse.ArgumentParser(description="LLM 기반 수영장 데이터 추출기")
    parser.add_argument("--test", type=int, default=0, metavar="N",
                        help="N건만 테스트 (기본: 전체)")
    parser.add_argument("--dry-run", action="store_true",
                        help="DB 저장 없이 결과만 출력")
    parser.add_argument("--id", type=int, default=None, metavar="ID",
                        help="특정 수영장 ID만 처리")
    parser.add_argument("--retry-failed", action="store_true",
                        help="실패한 것만 재시도")
    args = parser.parse_args()

    print("LLM 기반 수영장 데이터 추출기\n")

    enricher = LLMPoolEnricher()
    enricher.enrich_all(
        test_count=args.test,
        dry_run=args.dry_run,
        pool_id=args.id,
        retry_failed=args.retry_failed,
    )


if __name__ == "__main__":
    main()
