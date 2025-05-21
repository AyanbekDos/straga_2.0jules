import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent.parent / "db" / "chunks.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cur.fetchall()

print("📦 Таблицы в базе:")
for name in tables:
    print("-", name[0])
