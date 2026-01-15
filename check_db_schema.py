
import sqlite3

def check_schema():
    try:
        conn = sqlite3.connect('swimming_pools.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(swimming_pools);")
        rows = cursor.fetchall()
        for row in rows:
            print(row)
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_schema()
