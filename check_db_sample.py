
import sqlite3

def check_db():
    try:
        conn = sqlite3.connect('swimming_pools.db')
        cursor = conn.cursor()
        # Get count
        cursor.execute("SELECT COUNT(*) FROM swimming_pools;")
        count = cursor.fetchone()[0]
        print(f"Total pools: {count}")
        
        cursor.execute("SELECT id, name, free_swim_price, monthly_lesson_price, address FROM swimming_pools LIMIT 30;")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
