# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')
from database.connection import get_db
from app.models.swimming_pool import SwimmingPool
import json

db = next(get_db())
pools = db.query(SwimmingPool).filter(
    SwimmingPool.url.isnot(None),
    SwimmingPool.url != '',
    SwimmingPool.url != '정보 없음'
).all()

result = [{'id': p.id, 'name': p.name, 'url': p.url} for p in pools]

with open('pools_with_urls.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print(f'Total: {len(result)} pools with URLs')
print('Saved to: pools_with_urls.json')
