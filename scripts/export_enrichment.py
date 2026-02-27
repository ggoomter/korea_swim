# -*- coding: utf-8 -*-
"""
로컬 DB의 enrichment 데이터를 advanced_pools.json에 머지하는 스크립트

사용법:
  python scripts/export_enrichment.py              # 머지 후 저장
  python scripts/export_enrichment.py --dry-run    # 미리보기만
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import sqlite3
import os
import argparse

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "swimming_pools.db")
JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "advanced_pools.json")

# DB에서 가져올 enrichment 필드
ENRICHMENT_FIELDS = [
    "pricing", "free_swim_schedule", "operating_hours",
    "phone", "lanes", "pool_size", "parking", "notes",
]

# JSON으로 파싱해야 하는 필드
JSON_FIELDS = {"pricing", "free_swim_schedule", "operating_hours"}


def load_enrichment_from_db():
    """DB에서 enrichment 성공한 수영장 데이터 로드"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT name, address, {', '.join(ENRICHMENT_FIELDS)} "
        f"FROM swimming_pools WHERE enrichment_status = 'success'"
    )
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    conn.close()

    result = {}
    for row in rows:
        data = dict(zip(cols, row))
        name = data.pop("name")
        address = data.pop("address")
        key = f"{name}|{address}"

        # JSON 문자열 → dict/list 변환
        for field in JSON_FIELDS:
            val = data.get(field)
            if isinstance(val, str) and val not in ("null", ""):
                try:
                    data[field] = json.loads(val)
                except json.JSONDecodeError:
                    data[field] = None
            elif val == "null":
                data[field] = None

        # None 값 제거
        enriched = {k: v for k, v in data.items() if v is not None}
        if enriched:
            result[key] = enriched

    return result


def merge_enrichment(dry_run=False):
    """advanced_pools.json에 enrichment 데이터 머지"""
    # 1. JSON 로드
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        pools = json.load(f)

    # 2. DB에서 enrichment 데이터 로드
    enrichment = load_enrichment_from_db()

    print(f"advanced_pools.json: {len(pools)}건")
    print(f"DB enrichment 대상: {len(enrichment)}건")
    print()

    # 3. 매칭 & 머지
    merged_count = 0
    field_counts = {f: 0 for f in ENRICHMENT_FIELDS}

    for pool in pools:
        key = f"{pool.get('name', '')}|{pool.get('address', '')}"
        if key in enrichment:
            for field, value in enrichment[key].items():
                pool[field] = value
                field_counts[field] += 1
            merged_count += 1

    # 4. 매칭 안 된 enrichment 데이터도 추가 (DB에만 있는 수영장)
    existing_keys = {f"{p.get('name', '')}|{p.get('address', '')}" for p in pools}
    db_only_count = 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, address, lat, lng, phone, source, image_url, url, "
        f"{', '.join(ENRICHMENT_FIELDS)} "
        "FROM swimming_pools WHERE enrichment_status = 'success'"
    )
    cols = [d[0] for d in cursor.description]
    for row in cursor.fetchall():
        data = dict(zip(cols, row))
        key = f"{data['name']}|{data['address']}"
        if key not in existing_keys:
            # JSON 필드 파싱
            for field in JSON_FIELDS:
                val = data.get(field)
                if isinstance(val, str) and val not in ("null", ""):
                    try:
                        data[field] = json.loads(val)
                    except json.JSONDecodeError:
                        data[field] = None
                elif val == "null":
                    data[field] = None

            # None 제거
            new_pool = {k: v for k, v in data.items() if v is not None}
            pools.append(new_pool)
            db_only_count += 1
    conn.close()

    # 5. 결과 출력
    print(f"기존 풀 머지: {merged_count}건")
    print(f"DB에만 있던 풀 추가: {db_only_count}건")
    print(f"최종 advanced_pools.json: {len(pools)}건")
    print()
    print("필드별 머지 건수:")
    for field, count in field_counts.items():
        if count > 0:
            print(f"  {field}: {count}건")

    # 6. 저장
    if dry_run:
        print("\n[DRY-RUN] 파일 저장하지 않음")
    else:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(pools, f, ensure_ascii=False, indent=2)
        print(f"\n저장 완료: {JSON_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DB enrichment → advanced_pools.json 머지")
    parser.add_argument("--dry-run", action="store_true", help="미리보기만")
    args = parser.parse_args()

    merge_enrichment(dry_run=args.dry_run)
