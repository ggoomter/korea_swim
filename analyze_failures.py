# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3

conn = sqlite3.connect('swimming_pools.db')
cursor = conn.cursor()

print("=" * 80)
print("가격 크롤링 실패 분석")
print("=" * 80)

# 1. URL이 있지만 가격이 없는 경우
cursor.execute('''
    SELECT name, url
    FROM swimming_pools
    WHERE url IS NOT NULL
      AND url != ''
      AND url != 'https://example.com'
      AND (daily_price IN (5000, 10000) OR daily_price IS NULL)
    LIMIT 10
''')

print("\n1. URL은 있지만 가격 크롤링 실패:")
print("-" * 80)
rows = cursor.fetchall()
for i, (name, url) in enumerate(rows):
    print(f"{i+1}. {name}")
    print(f"   URL: {url[:80]}...")
    print()

# 2. URL이 없는 경우
cursor.execute('''
    SELECT name, address
    FROM swimming_pools
    WHERE url IS NULL OR url = '' OR url = 'https://example.com'
    LIMIT 10
''')

print("\n2. URL을 찾지 못한 경우:")
print("-" * 80)
rows = cursor.fetchall()
for i, (name, address) in enumerate(rows):
    print(f"{i+1}. {name}")
    print(f"   주소: {address}")
    print()

# 3. 통계
cursor.execute('SELECT COUNT(*) FROM swimming_pools WHERE url IS NOT NULL AND url != "" AND url != "https://example.com"')
has_url = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM swimming_pools WHERE url IS NULL OR url = "" OR url = "https://example.com"')
no_url = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM swimming_pools WHERE daily_price NOT IN (5000, 10000)')
has_real_price = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM swimming_pools')
total = cursor.fetchone()[0]

print("\n3. 통계 요약:")
print("-" * 80)
print(f"전체 수영장: {total}개")
print(f"URL 있음: {has_url}개 ({has_url/total*100:.1f}%)")
print(f"URL 없음: {no_url}개 ({no_url/total*100:.1f}%)")
print(f"실제 가격 있음: {has_real_price}개 ({has_real_price/total*100:.1f}%)")
print(f"가격 크롤링 필요: {total - has_real_price}개")

conn.close()
