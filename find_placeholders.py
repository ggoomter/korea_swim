
import sqlite3
import json

def get_needs_update():
    conn = sqlite3.connect('swimming_pools.db')
    cursor = conn.cursor()
    
    # Pools with estimated/default prices
    cursor.execute("""
        SELECT id, name, address, free_swim_price, monthly_lesson_price 
        FROM swimming_pools 
        WHERE free_swim_price LIKE '%8000%' 
           OR free_swim_price LIKE '%10000%'
           OR free_swim_price IS NULL
           OR monthly_lesson_price IS NULL
        LIMIT 20;
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    pools = get_needs_update()
    for pool in pools:
        print(pool)
