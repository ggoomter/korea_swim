# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3

conn = sqlite3.connect('swimming_pools.db')
cursor = conn.cursor()

print("=" * 80)
print("DB 마이그레이션: daily_price → monthly_lesson_price")
print("=" * 80)

try:
    # 1. 새로운 컬럼 추가
    print("\n1. monthly_lesson_price 컬럼 추가 중...")
    cursor.execute('ALTER TABLE swimming_pools ADD COLUMN monthly_lesson_price INTEGER')
    print("✅ 컬럼 추가 완료")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("⚠️  monthly_lesson_price 컬럼이 이미 존재합니다")
    else:
        raise

# 2. 기존 daily_price 값을 monthly_lesson_price로 복사
print("\n2. 데이터 복사 중 (daily_price → monthly_lesson_price)...")
cursor.execute('UPDATE swimming_pools SET monthly_lesson_price = daily_price WHERE daily_price IS NOT NULL')
affected_rows = cursor.rowcount
print(f"✅ {affected_rows}개 행 복사 완료")

# 3. daily_price 컬럼 데이터 확인
cursor.execute('SELECT COUNT(*) FROM swimming_pools WHERE daily_price IS NOT NULL')
count = cursor.fetchone()[0]
print(f"\n3. daily_price 데이터: {count}개")

# 4. SQLite는 컬럼 삭제를 직접 지원하지 않으므로, NULL로 설정만 하거나 그대로 둠
print("\n4. daily_price 컬럼은 그대로 유지됩니다 (SQLite 제약)")
print("   → 코드에서는 monthly_lesson_price를 사용하세요")

conn.commit()
conn.close()

print("\n" + "=" * 80)
print("✅ 마이그레이션 완료")
print("=" * 80)
print("\n다음 단계:")
print("1. 서버 재시작: uvicorn app.main:app --reload")
print("2. Excel 다운로드/업로드 시 '한달 수강권' 컬럼 사용")
