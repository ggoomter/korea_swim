# -*- coding: utf-8 -*-
"""
DB 스키마 마이그레이션: 상세 가격/시간표 구조로 전환

변경사항:
  - 추가 컬럼: pricing(JSON), free_swim_schedule(JSON), notes(TEXT),
               parking(BOOLEAN), last_enriched(DATETIME), enrichment_status(TEXT)
  - 기존 데이터 마이그레이션: daily_price → pricing, free_swim_times → free_swim_schedule 등
  - 삭제 컬럼: daily_price, free_swim_price, monthly_lesson_price,
               free_swim_times, membership_prices, lessons

사용법:
  python scripts/migrate_schema.py           # 마이그레이션 실행
  python scripts/migrate_schema.py --dry-run # 변경 사항만 출력
"""
import sys
import os
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3
import json
import shutil
import argparse
from datetime import datetime


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "swimming_pools.db")

# 삭제 대상 컬럼
DROP_COLUMNS = [
    "daily_price", "free_swim_price", "monthly_lesson_price",
    "free_swim_times", "membership_prices", "lessons",
]

# 추가 대상 컬럼 (name, type, default)
ADD_COLUMNS = [
    ("pricing", "JSON", None),
    ("free_swim_schedule", "JSON", None),
    ("notes", "TEXT", None),
    ("parking", "BOOLEAN", None),
    ("last_enriched", "DATETIME", None),
    ("enrichment_status", "TEXT", "'pending'"),
]


def get_existing_columns(cursor):
    """현재 테이블의 컬럼 목록 반환"""
    cursor.execute("PRAGMA table_info(swimming_pools)")
    return {row[1] for row in cursor.fetchall()}


def backup_db():
    """마이그레이션 전 DB 백업"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{DB_PATH}.pre-migration-{timestamp}"
    shutil.copy2(DB_PATH, backup_path)
    print(f"  DB 백업 완료: {backup_path}")
    return backup_path


def migrate_daily_price_to_pricing(value):
    """daily_price '3400' → pricing JSON 구조"""
    if not value or value in ("", "null", "None", "정보 없음"):
        return None

    try:
        price = int(value)
    except (ValueError, TypeError):
        return None

    # 합리적 가격 범위 확인 (1,000 ~ 100,000)
    if not (1000 <= price <= 100000):
        return None

    return json.dumps({
        "자유수영": {
            "성인": {"평일": price}
        }
    }, ensure_ascii=False)


def migrate_free_swim_times_to_schedule(value):
    """free_swim_times JSON → free_swim_schedule 요일별 구조"""
    if not value or value in ("", "null", "None", "{}"):
        return None

    try:
        data = json.loads(value) if isinstance(value, str) else value
    except (json.JSONDecodeError, TypeError):
        return None

    if not data:
        return None

    # 이미 요일별 구조면 그대로 사용
    day_keys = {"월", "화", "수", "목", "금", "토", "일"}
    eng_day_map = {
        "mon": "월", "tue": "화", "wed": "수", "thu": "목",
        "fri": "금", "sat": "토", "sun": "일"
    }

    schedule = {}

    if isinstance(data, dict):
        # {"times": ["06:00-08:00", "20:00-22:00"]} 형태
        if "times" in data:
            times = data["times"]
            if isinstance(times, list):
                # 시간만 있고 요일 없으면 평일용으로 배치
                for day in ["월", "화", "수", "목", "금"]:
                    schedule[day] = times
                return json.dumps(schedule, ensure_ascii=False)

        # {"mon": [...], "sat": [...]} 형태
        for key, val in data.items():
            day_kr = eng_day_map.get(key.lower(), key)
            if day_kr in day_keys:
                if isinstance(val, list):
                    schedule[day_kr] = val
                elif isinstance(val, str):
                    schedule[day_kr] = [val]

    if schedule:
        return json.dumps(schedule, ensure_ascii=False)

    return None


def add_new_columns(cursor, existing_cols, dry_run=False):
    """새 컬럼 추가"""
    added = 0
    for col_name, col_type, default in ADD_COLUMNS:
        if col_name not in existing_cols:
            default_clause = f" DEFAULT {default}" if default else ""
            sql = f"ALTER TABLE swimming_pools ADD COLUMN {col_name} {col_type}{default_clause}"
            if dry_run:
                print(f"  [DRY-RUN] {sql}")
            else:
                cursor.execute(sql)
                print(f"  + 컬럼 추가: {col_name} ({col_type})")
            added += 1
    return added


def migrate_data(cursor, dry_run=False):
    """기존 데이터를 새 컬럼으로 마이그레이션"""
    cursor.execute("""
        SELECT id, daily_price, free_swim_price, free_swim_times,
               membership_prices, monthly_lesson_price, lessons
        FROM swimming_pools
    """)
    rows = cursor.fetchall()

    migrated = 0
    for row in rows:
        pool_id = row[0]
        daily_price = row[1]
        free_swim_price = row[2]
        free_swim_times = row[3]
        membership_prices = row[4]
        monthly_lesson_price = row[5]
        lessons_data = row[6]

        updates = []
        params = []

        # pricing 마이그레이션 (daily_price 기준, free_swim_price가 다르면 별도)
        price_val = free_swim_price or daily_price
        pricing_json = migrate_daily_price_to_pricing(price_val)
        if pricing_json:
            # monthly_lesson_price가 있으면 pricing에 통합
            if monthly_lesson_price and monthly_lesson_price not in ("", "null", "None"):
                try:
                    lesson_price = int(monthly_lesson_price)
                    if 30000 <= lesson_price <= 500000:
                        pricing_data = json.loads(pricing_json)
                        pricing_data["강습_월"] = {"성인": lesson_price}
                        pricing_json = json.dumps(pricing_data, ensure_ascii=False)
                except (ValueError, TypeError):
                    pass

            updates.append("pricing = ?")
            params.append(pricing_json)

        # free_swim_schedule 마이그레이션
        schedule_json = migrate_free_swim_times_to_schedule(free_swim_times)
        if schedule_json:
            updates.append("free_swim_schedule = ?")
            params.append(schedule_json)

        if updates:
            if dry_run:
                print(f"  [DRY-RUN] ID={pool_id}: {', '.join(u.split(' =')[0] for u in updates)}")
            else:
                params.append(pool_id)
                sql = f"UPDATE swimming_pools SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(sql, params)
            migrated += 1

    return migrated


def drop_old_columns(cursor, existing_cols, dry_run=False):
    """SQLite에서 컬럼 삭제 (테이블 재생성)

    SQLite 3.35.0+ 은 ALTER TABLE DROP COLUMN 지원.
    그 이전 버전은 테이블 재생성 필요.
    """
    cols_to_drop = [c for c in DROP_COLUMNS if c in existing_cols]
    if not cols_to_drop:
        print("  삭제할 컬럼 없음")
        return 0

    if dry_run:
        for col in cols_to_drop:
            print(f"  [DRY-RUN] 컬럼 삭제: {col}")
        return len(cols_to_drop)

    # SQLite 버전 확인
    version = sqlite3.sqlite_version_info
    if version >= (3, 35, 0):
        for col in cols_to_drop:
            try:
                cursor.execute(f"ALTER TABLE swimming_pools DROP COLUMN {col}")
                print(f"  - 컬럼 삭제: {col}")
            except Exception as e:
                print(f"  ! 컬럼 삭제 실패 ({col}): {e}")
    else:
        # 테이블 재생성 방식
        print(f"  SQLite {sqlite3.sqlite_version} - 테이블 재생성으로 컬럼 삭제")

        cursor.execute("PRAGMA table_info(swimming_pools)")
        all_cols = cursor.fetchall()
        keep_cols = [c for c in all_cols if c[1] not in cols_to_drop]

        col_defs = []
        col_names = []
        for col in keep_cols:
            cid, name, ctype, notnull, default, pk = col
            parts = [name, ctype or "TEXT"]
            if pk:
                parts.append("PRIMARY KEY")
            if notnull:
                parts.append("NOT NULL")
            if default is not None:
                parts.append(f"DEFAULT {default}")
            col_defs.append(" ".join(parts))
            col_names.append(name)

        col_names_str = ", ".join(col_names)
        col_defs_str = ", ".join(col_defs)

        cursor.execute(f"CREATE TABLE swimming_pools_new ({col_defs_str})")
        cursor.execute(f"INSERT INTO swimming_pools_new ({col_names_str}) SELECT {col_names_str} FROM swimming_pools")
        cursor.execute("DROP TABLE swimming_pools")
        cursor.execute("ALTER TABLE swimming_pools_new RENAME TO swimming_pools")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_swimming_pools_id ON swimming_pools (id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_swimming_pools_name ON swimming_pools (name)")

        for col in cols_to_drop:
            print(f"  - 컬럼 삭제: {col}")

    return len(cols_to_drop)


def run_migration(dry_run=False):
    """마이그레이션 메인 실행"""
    mode = " [DRY-RUN]" if dry_run else ""
    print(f"\n{'='*60}")
    print(f"  DB 스키마 마이그레이션{mode}")
    print(f"{'='*60}\n")

    if not os.path.exists(DB_PATH):
        print(f"  DB 파일 없음: {DB_PATH}")
        sys.exit(1)

    # 백업
    if not dry_run:
        backup_db()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        existing_cols = get_existing_columns(cursor)
        print(f"  현재 컬럼 수: {len(existing_cols)}")

        # 1. 새 컬럼 추가
        print(f"\n[1/3] 새 컬럼 추가")
        added = add_new_columns(cursor, existing_cols, dry_run)
        print(f"  → {added}개 추가")

        # 2. 데이터 마이그레이션
        print(f"\n[2/3] 데이터 마이그레이션")
        migrated = migrate_data(cursor, dry_run)
        print(f"  → {migrated}건 마이그레이션")

        # 3. 이전 컬럼 삭제
        print(f"\n[3/3] 이전 컬럼 삭제")
        # 컬럼 추가 후 다시 조회
        existing_cols = get_existing_columns(cursor)
        dropped = drop_old_columns(cursor, existing_cols, dry_run)
        print(f"  → {dropped}개 삭제")

        if not dry_run:
            conn.commit()

        # 결과 확인
        print(f"\n{'='*60}")
        final_cols = get_existing_columns(cursor)
        print(f"  마이그레이션 완료! 최종 컬럼 수: {len(final_cols)}")
        print(f"  컬럼: {', '.join(sorted(final_cols))}")

        # 마이그레이션된 데이터 샘플 (dry-run이 아닐 때만)
        if not dry_run:
            cursor.execute("""
                SELECT name, pricing, free_swim_schedule, enrichment_status
                FROM swimming_pools
                WHERE pricing IS NOT NULL
                LIMIT 3
            """)
            samples = cursor.fetchall()
            if samples:
                print(f"\n  샘플 데이터:")
                for name, pricing, schedule, status in samples:
                    print(f"    {name}: pricing={pricing[:60] if pricing else 'null'}...")

        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\n  마이그레이션 실패: {e}")
        if not dry_run:
            conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="DB 스키마 마이그레이션")
    parser.add_argument("--dry-run", action="store_true",
                        help="DB 변경 없이 변경 사항만 출력")
    args = parser.parse_args()

    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
