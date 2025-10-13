# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3

conn = sqlite3.connect('swimming_pools.db')
cursor = conn.cursor()

print("=" * 80)
print("가격 분포 현황")
print("=" * 80)

cursor.execute('SELECT COUNT(*), daily_price FROM swimming_pools GROUP BY daily_price ORDER BY daily_price')
rows = cursor.fetchall()

print("\n가격별 수영장 개수:")
print("-" * 80)
for count, price in rows:
    if price:
        print(f'{count}개: {price:,}원')
    else:
        print(f'{count}개: 가격 정보 없음')

# 통계
cursor.execute('SELECT COUNT(*) FROM swimming_pools')
total = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM swimming_pools WHERE daily_price IS NOT NULL')
with_price = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM swimming_pools WHERE daily_price IS NULL')
no_price = cursor.fetchone()[0]

print(f"\n{'='*80}")
print(f"총 {total}개 수영장")
print(f"  • 가격 있음: {with_price}개 ({with_price/total*100:.1f}%)")
print(f"  • 가격 없음: {no_price}개 ({no_price/total*100:.1f}%)")
print(f"{'='*80}")

conn.close()
