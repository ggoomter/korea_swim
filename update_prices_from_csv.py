# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3
import csv

conn = sqlite3.connect('swimming_pools.db')
cursor = conn.cursor()

print("=" * 80)
print("CSV 파일에서 가격 정보 업데이트")
print("=" * 80)

updated_count = 0
skipped_count = 0

with open('pools_for_manual_update.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)

    for row in reader:
        pool_id = int(row['ID'])
        name = row['수영장명']
        daily_price_real = row['일일권(실제)'].strip()
        free_swim_price_real = row['자유수영(실제)'].strip()

        # 빈 칸이면 스킵
        if not daily_price_real and not free_swim_price_real:
            skipped_count += 1
            continue

        updates = []
        params = []

        if daily_price_real:
            try:
                price = int(daily_price_real)
                updates.append("daily_price = ?")
                params.append(price)
            except ValueError:
                print(f"⚠️  {name}: 일일권 가격 형식 오류 ({daily_price_real})")
                continue

        if free_swim_price_real:
            try:
                price = int(free_swim_price_real)
                updates.append("free_swim_price = ?")
                params.append(price)
            except ValueError:
                print(f"⚠️  {name}: 자유수영 가격 형식 오류 ({free_swim_price_real})")
                continue

        if updates:
            params.append(pool_id)
            query = f"UPDATE swimming_pools SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            updated_count += 1
            print(f"✓ {name}: {daily_price_real or '-'}원 / {free_swim_price_real or '-'}원")

conn.commit()
conn.close()

print()
print("=" * 80)
print(f"✅ 업데이트 완료")
print(f"   • 업데이트: {updated_count}개")
print(f"   • 스킵: {skipped_count}개")
print("=" * 80)
