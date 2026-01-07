import sqlite3
import pandas as pd

# Connect to the database
conn = sqlite3.connect('translation_history.db')

try:
    # Query all data
    df = pd.read_sql_query("SELECT * FROM history", conn)
    
    if df.empty:
        print("\n[Database is empty]")
    else:
        print("\n=== TRANSLATION HISTORY DATABASE ===")
        print(df.to_string(index=False))
        print("====================================")
        print(f"\nTotal entries: {len(df)}")

except Exception as e:
    print(f"Error reading database: {e}")

finally:
    conn.close()
