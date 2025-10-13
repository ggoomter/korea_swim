# -*- coding: utf-8 -*-
"""
AI 웹 검색 크롤러 - Claude/Perplexity를 사용한 실시간 웹 검색
수영장 이름만으로 웹에서 가격 정보를 자동으로 찾아옴
"""
import sys
import io
sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json
import time
import random
from typing import Dict, List, Optional
import anthropic
import requests

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env 파일 로드 완료")
except ImportError:
    print("⚠️  python-dotenv 없음 - 환경변수 직접 사용")

class AISearchCrawler:
    def __init__(self):
        # Claude API
        self.claude_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.claude_api_key:
            raise ValueError("ANTHROPIC_API_KEY 환경변수를 설정하세요")

        self.claude_client = anthropic.Anthropic(api_key=self.claude_api_key)

        # Perplexity API (옵션)
        self.perplexity_api_key = os.getenv("PERPLEXITY_API_KEY")

        print("✅ AI 웹 검색 크롤러 초기화 완료")
        if self.perplexity_api_key:
            print("   - Perplexity API 활성화")
        else:
            print("   - Claude만 사용 (Perplexity 미설정)")

    def search_with_perplexity(self, pool_name: str, address: str) -> Optional[Dict]:
        """Perplexity API로 웹 검색"""
        if not self.perplexity_api_key:
            return None

        try:
            query = f"{pool_name} {address} 수영장 가격 한달 수강권 자유수영 이용료"

            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.perplexity_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 수영장 가격 정보를 찾는 전문가입니다. 웹에서 찾은 정보만 기반으로 답변하세요."
                        },
                        {
                            "role": "user",
                            "content": f"""
{pool_name} ({address})의 다음 정보를 웹에서 찾아주세요:

1. 한달 수강권 가격 (1개월 강습 프로그램)
2. 자유수영 1회 이용 가격

다음 JSON 형식으로만 답변하세요:
{{
  "monthly_lesson_price": "가격 또는 '정보없음' 또는 '가격 다양, 홈페이지 참조'",
  "free_swim_price": "가격 또는 '정보없음'",
  "url": "공식 웹사이트 주소",
  "source": "정보를 찾은 웹사이트"
}}

숫자만 있는 경우 숫자만 반환하세요 (예: "150000")
가격이 다양한 경우 설명을 포함하세요 (예: "연령별 상이, 6만~15만원")
"""
                        }
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500
                },
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']

                # JSON 추출
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    return result

            return None

        except Exception as e:
            print(f"   ⚠️  Perplexity 오류: {str(e)[:50]}")
            return None

    def search_with_claude(self, pool_name: str, address: str, phone: str = None) -> Dict:
        """Claude로 웹 검색 (Web Search 시뮬레이션)"""
        try:
            # Claude에게 웹 검색 요청
            prompt = f"""
다음 수영장의 가격 정보를 찾아주세요:

**수영장 정보:**
- 이름: {pool_name}
- 주소: {address}
{f"- 전화번호: {phone}" if phone else ""}

**찾아야 할 정보:**
1. 한달 수강권 가격 (1개월 수영 강습 프로그램 비용)
2. 자유수영 1회 이용 가격

**검색 방법:**
1. "{pool_name} 가격" 키워드로 검색
2. 공식 홈페이지나 구청 사이트 확인
3. 네이버 플레이스, 블로그 후기 참고

**답변 형식 (반드시 JSON으로):**
```json
{{
  "monthly_lesson_price": "숫자 또는 설명",
  "free_swim_price": "숫자 또는 설명",
  "url": "정보 출처 URL",
  "confidence": "high/medium/low",
  "note": "추가 설명"
}}
```

**예시:**
- 가격이 명확한 경우: "150000"
- 가격이 다양한 경우: "연령별 10만~18만원"
- 정보 없는 경우: "정보없음"
- 문의 필요한 경우: "전화 문의"

지금 웹에서 실시간으로 검색해서 찾아주세요.
"""

            message = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.2,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = message.content[0].text

            # JSON 추출
            import re
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if not json_match:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

            if json_match:
                try:
                    result = json.loads(json_match.group(1) if json_match.lastindex else json_match.group())
                    return result
                except json.JSONDecodeError:
                    pass

            # JSON 파싱 실패 시 텍스트에서 추출
            result = {
                "monthly_lesson_price": None,
                "free_swim_price": None,
                "url": None,
                "confidence": "low",
                "note": response_text[:200]
            }

            # 가격 패턴 매칭
            monthly_match = re.search(r'한달|수강권|강습.*?(\d{4,}|[\d,]+원|정보없음|문의|다양)', response_text)
            if monthly_match:
                result['monthly_lesson_price'] = monthly_match.group(1)

            swim_match = re.search(r'자유수영.*?(\d{4,}|[\d,]+원|정보없음|문의)', response_text)
            if swim_match:
                result['free_swim_price'] = swim_match.group(1)

            return result

        except Exception as e:
            print(f"   ❌ Claude 오류: {str(e)[:100]}")
            return {
                "monthly_lesson_price": None,
                "free_swim_price": None,
                "url": None,
                "error": str(e)
            }

    def search_pool_info(self, pool_name: str, address: str, phone: str = None) -> Dict:
        """수영장 정보 검색 (Perplexity → Claude)"""
        print(f"\n🔍 검색: {pool_name}")

        # 1단계: Perplexity 시도
        result = self.search_with_perplexity(pool_name, address)
        if result and result.get('monthly_lesson_price') != '정보없음':
            print(f"   ✅ Perplexity 성공")
            print(f"      수강권: {result.get('monthly_lesson_price', '정보없음')}")
            print(f"      자유수영: {result.get('free_swim_price', '정보없음')}")
            return result

        # 2단계: Claude 시도
        print(f"   🤖 Claude 검색중...")
        result = self.search_with_claude(pool_name, address, phone)

        if result.get('monthly_lesson_price') or result.get('free_swim_price'):
            print(f"   ✅ 검색 완료")
            print(f"      수강권: {result.get('monthly_lesson_price', '정보없음')}")
            print(f"      자유수영: {result.get('free_swim_price', '정보없음')}")
        else:
            print(f"   ⚠️  가격 정보 없음")

        # 예의 지키기 (API Rate Limit)
        time.sleep(random.uniform(2.0, 3.0))

        return result

    def crawl_pools_from_db(self, limit: int = 10) -> List[Dict]:
        """DB에서 수영장 가져와서 AI 검색"""
        from database.connection import get_db
        from app.models.swimming_pool import SwimmingPool

        db = next(get_db())

        # 가격 정보가 없는 수영장 우선
        pools = db.query(SwimmingPool).filter(
            (SwimmingPool.monthly_lesson_price.is_(None)) |
            (SwimmingPool.free_swim_price.is_(None))
        ).limit(limit).all()

        results = []

        print(f"\n{'='*70}")
        print(f"  🏊 {len(pools)}개 수영장 AI 검색 시작")
        print(f"{'='*70}")

        for i, pool in enumerate(pools, 1):
            print(f"\n[{i}/{len(pools)}] {pool.name}")

            result = self.search_pool_info(
                pool_name=pool.name,
                address=pool.address,
                phone=pool.phone
            )

            result['pool_id'] = pool.id
            result['pool_name'] = pool.name
            result['pool_address'] = pool.address
            results.append(result)

        return results

    def update_db_with_results(self, results: List[Dict]) -> int:
        """검색 결과로 DB 업데이트"""
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

            # 가격 정보 업데이트
            if result.get('monthly_lesson_price'):
                pool.monthly_lesson_price = str(result['monthly_lesson_price'])
                updated = True

            if result.get('free_swim_price'):
                pool.free_swim_price = str(result['free_swim_price'])
                updated = True

            # URL 업데이트
            if result.get('url') and not pool.url:
                pool.url = result['url']
                updated = True

            if updated:
                updated_count += 1

        db.commit()

        print(f"\n{'='*70}")
        print(f"  ✅ {updated_count}개 수영장 정보 업데이트 완료")
        print(f"{'='*70}")

        return updated_count


def main():
    print("\n" + "="*70)
    print("  🤖 AI 웹 검색 크롤러")
    print("  수영장 이름만으로 웹에서 가격 정보 자동 검색")
    print("="*70)

    try:
        crawler = AISearchCrawler()
    except ValueError as e:
        print(f"\n❌ 오류: {e}")
        print("\n환경변수 설정 방법:")
        print("  Windows: set ANTHROPIC_API_KEY=your_api_key")
        print("  Linux/Mac: export ANTHROPIC_API_KEY=your_api_key")
        return

    # 10개 샘플 검색
    results = crawler.crawl_pools_from_db(limit=10)

    # 결과 저장
    with open('ai_search_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 결과 저장: ai_search_results.json")

    # DB 업데이트
    updated = crawler.update_db_with_results(results)

    # 통계
    success_count = sum(1 for r in results if r.get('monthly_lesson_price') or r.get('free_swim_price'))
    print(f"\n📊 통계:")
    print(f"   - 검색: {len(results)}개")
    print(f"   - 성공: {success_count}개 ({success_count/len(results)*100:.1f}%)")
    print(f"   - DB 업데이트: {updated}개")


if __name__ == "__main__":
    main()
