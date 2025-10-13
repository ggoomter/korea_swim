# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3

conn = sqlite3.connect('swimming_pools.db')
cursor = conn.cursor()

# 실제 크롤링된 가격 확인
cursor.execute('''
    SELECT name, daily_price, free_swim_price, url
    FROM swimming_pools
    WHERE url IS NOT NULL
      AND url != ''
      AND daily_price IS NOT NULL
      AND daily_price NOT IN (10000, 5000)
    LIMIT 15
''')

rows = cursor.fetchall()
print('Successfully crawled pools with real prices:')
print('='*80)
for i, row in enumerate(rows):
    name, daily, free_swim, url = row
    print(f'{i+1}. {name}')
    print(f'   일일권: {daily:,}원 | 자유수영: {free_swim:,}원' if free_swim else f'   일일권: {daily:,}원')
    print(f'   URL: {url[:70]}...')
    print()

# 통계
cursor.execute('SELECT COUNT(*) FROM swimming_pools WHERE daily_price NOT IN (10000, 5000) AND daily_price IS NOT NULL')
real_price_count = cursor.fetchone()[0]

cursor.execute('SELECT COUNT(*) FROM swimming_pools')
total_count = cursor.fetchone()[0]

print(f'\n통계:')
print(f'  • 실제 가격 수집 완료: {real_price_count}개')
print(f'  • 전체 수영장: {total_count}개')
print(f'  • 진행률: {real_price_count/total_count*100:.1f}%')

conn.close()
