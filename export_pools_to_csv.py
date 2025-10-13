# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3
import csv

conn = sqlite3.connect('swimming_pools.db')
cursor = conn.cursor()

# 모든 수영장 정보 가져오기
cursor.execute('''
    SELECT
        id,
        name,
        address,
        phone,
        daily_price,
        free_swim_price,
        url
    FROM swimming_pools
    ORDER BY id
''')

rows = cursor.fetchall()

# CSV 파일로 저장
with open('pools_for_manual_update.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)

    # 헤더
    writer.writerow([
        'ID',
        '수영장명',
        '주소',
        '전화번호',
        '일일권(현재)',
        '자유수영(현재)',
        '웹사이트',
        '일일권(실제)',  # 빈 칸 - 직접 입력용
        '자유수영(실제)',  # 빈 칸 - 직접 입력용
        '비고'  # 빈 칸 - 메모용
    ])

    # 데이터
    for row in rows:
        writer.writerow([
            row[0],  # id
            row[1],  # name
            row[2],  # address
            row[3] or '',  # phone
            row[4] or '',  # daily_price
            row[5] or '',  # free_swim_price
            row[6] or '',  # url
            '',  # 일일권(실제) - 직접 입력
            '',  # 자유수영(실제) - 직접 입력
            ''   # 비고
        ])

conn.close()

print(f"✅ CSV 파일 생성 완료: pools_for_manual_update.csv")
print(f"   총 {len(rows)}개 수영장")
print()
print("사용 방법:")
print("1. Excel에서 pools_for_manual_update.csv 열기")
print("2. '일일권(실제)', '자유수영(실제)' 칸에 실제 가격 입력")
print("3. 저장 후 'python update_prices_from_csv.py' 실행")
