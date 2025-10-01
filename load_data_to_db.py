# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from sqlalchemy.orm import Session
from database.connection import SessionLocal, init_db
from app.crud.swimming_pool import upsert_swimming_pool
from app.schemas.swimming_pool import SwimmingPoolCreate

def load_pools_to_db(json_file="collected_pools.json"):
    print("="*60)
    print("📥 수영장 데이터 DB 저장/업데이트")
    print("="*60)

    init_db()
    db = SessionLocal()

    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            pools_data = json.load(f)

        print(f"\n📂 {len(pools_data)}개 수영장 로드")

        new_count = 0
        update_count = 0
        error_count = 0

        for pool_data in pools_data:
            try:
                pool_schema = SwimmingPoolCreate(**pool_data)

                # Upsert: 기존 수영장은 업데이트, 없으면 새로 생성
                _, is_new = upsert_swimming_pool(db, pool_schema)

                if is_new:
                    new_count += 1
                else:
                    update_count += 1

                if (new_count + update_count) % 10 == 0:
                    print(f"  진행중... 신규 {new_count}개, 업데이트 {update_count}개")

            except Exception as e:
                error_count += 1
                print(f"  ⚠️ 실패: {pool_data.get('name', 'Unknown')} - {str(e)[:50]}")

        print(f"\n✅ 완료!")
        print(f"  신규 추가: {new_count}개")
        print(f"  업데이트: {update_count}개")
        if error_count > 0:
            print(f"  실패: {error_count}개")

        # 저장된 데이터 확인
        print("\n📊 저장된 수영장 목록:")
        from app.crud.swimming_pool import get_swimming_pools
        pools = get_swimming_pools(db, skip=0, limit=100)

        for i, pool in enumerate(pools, 1):
            print(f"{i}. {pool.name} - {pool.address}")

        return new_count + update_count

    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {json_file}")
        return 0
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        db.rollback()
        return 0
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    filename = sys.argv[1] if len(sys.argv) > 1 else "collected_pools.json"
    load_pools_to_db(filename)
