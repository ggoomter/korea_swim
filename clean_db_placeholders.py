
import sqlite3

def clean_db():
    conn = sqlite3.connect('swimming_pools.db')
    cursor = conn.cursor()
    
    # 1. Clear prices that are exactly placeholder values
    # Note: price columns in DB are TEXT according to schema
    cursor.execute("UPDATE swimming_pools SET free_swim_price = NULL WHERE free_swim_price IN ('8000', '8,000', '8000.0', '8000원');")
    cursor.execute("UPDATE swimming_pools SET monthly_lesson_price = NULL WHERE monthly_lesson_price IN ('10000', '10,000', '10000.0', '10000원');")
    
    # 2. Clear operating_hours if it's the exact default JSON
    default_hours = '{"mon-fri": "06:00-22:00", "sat": "07:00-21:00", "sun": "08:00-20:00"}'
    cursor.execute("UPDATE swimming_pools SET operating_hours = NULL WHERE operating_hours LIKE ? OR operating_hours = ?", (f"%{default_hours}%", default_hours))
    
    # 3. Clear free_swim_times if it's the exact default JSON
    # The default had a long JSON structure. Let's just clear common ones.
    cursor.execute("UPDATE swimming_pools SET free_swim_times = NULL WHERE free_swim_times LIKE '%06:00-08:00%' AND free_swim_times LIKE '%13:00-15:00%';")
    
    conn.commit()
    print(f"Cleaned {cursor.rowcount} rows with potential placeholder data.")
    conn.close()

if __name__ == "__main__":
    clean_db()
