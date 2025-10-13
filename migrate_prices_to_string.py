# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3

conn = sqlite3.connect('swimming_pools.db')
cursor = conn.cursor()

print("=" * 80)
print("DB 마이그레이션: 가격 컬럼을 INTEGER → STRING으로 변경")
print("=" * 80)

try:
    # 1. 기존 테이블 백업
    print("\n1. 기존 테이블 백업 중...")
    cursor.execute('CREATE TABLE swimming_pools_backup AS SELECT * FROM swimming_pools')
    print("✅ 백업 완료")

    # 2. 기존 테이블 삭제
    print("\n2. 기존 테이블 삭제 중...")
    cursor.execute('DROP TABLE swimming_pools')
    print("✅ 삭제 완료")

    # 3. 새로운 테이블 생성 (가격 필드를 TEXT로 변경)
    print("\n3. 새로운 테이블 생성 중...")
    cursor.execute('''
    CREATE TABLE swimming_pools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR,
        address VARCHAR,
        lat FLOAT,
        lng FLOAT,
        phone VARCHAR,
        operating_hours JSON,
        lanes INTEGER,
        pool_size VARCHAR,
        water_temp VARCHAR,
        facilities JSON,
        membership_prices JSON,
        monthly_lesson_price TEXT,
        free_swim_times JSON,
        free_swim_price TEXT,
        lessons JSON,
        source VARCHAR,
        url VARCHAR,
        image_url VARCHAR,
        description VARCHAR,
        last_updated DATETIME,
        is_active BOOLEAN,
        rating FLOAT,
        review_count INTEGER DEFAULT 0
    )
    ''')
    print("✅ 새 테이블 생성 완료")

    # 4. 백업 데이터를 새 테이블로 복사 (INTEGER 값을 TEXT로 변환)
    print("\n4. 데이터 복사 중 (INTEGER → TEXT 변환)...")
    cursor.execute('''
    INSERT INTO swimming_pools (
        id, name, address, lat, lng, phone,
        operating_hours, lanes, pool_size, water_temp, facilities,
        membership_prices, monthly_lesson_price,
        free_swim_times, free_swim_price,
        lessons, source, url, image_url, description,
        last_updated, is_active, rating, review_count
    )
    SELECT
        id, name, address, lat, lng, phone,
        operating_hours, lanes, pool_size, water_temp, facilities,
        membership_prices,
        CAST(monthly_lesson_price AS TEXT),
        free_swim_times,
        CAST(free_swim_price AS TEXT),
        lessons, source, url, image_url, description,
        last_updated, is_active, rating, review_count
    FROM swimming_pools_backup
    ''')
    affected_rows = cursor.rowcount
    print(f"✅ {affected_rows}개 행 복사 완료")

    # 5. 백업 테이블 삭제
    print("\n5. 백업 테이블 삭제 중...")
    cursor.execute('DROP TABLE swimming_pools_backup')
    print("✅ 백업 테이블 삭제 완료")

    # 6. 인덱스 재생성
    print("\n6. 인덱스 재생성 중...")
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_swimming_pools_id ON swimming_pools (id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS ix_swimming_pools_name ON swimming_pools (name)')
    print("✅ 인덱스 재생성 완료")

    conn.commit()
    print("\n" + "=" * 80)
    print("✅ 마이그레이션 완료")
    print("=" * 80)
    print("\n변경 사항:")
    print("- monthly_lesson_price: INTEGER → TEXT")
    print("- free_swim_price: INTEGER → TEXT")
    print("\n이제 다음과 같은 값을 입력할 수 있습니다:")
    print("- 숫자: '150000', '8000'")
    print("- 문자열: '가격 다양, 표 참조', '시간대별 상이', '문의' 등")

except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    conn.rollback()
    print("변경사항이 롤백되었습니다.")

    # 에러 발생 시 백업 테이블이 있으면 복구 시도
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='swimming_pools_backup'")
    if cursor.fetchone():
        print("\n백업 테이블 발견! 복구를 시도하시겠습니까?")
        print("복구하려면 다음 명령어를 실행하세요:")
        print("  DROP TABLE swimming_pools;")
        print("  ALTER TABLE swimming_pools_backup RENAME TO swimming_pools;")

finally:
    conn.close()
