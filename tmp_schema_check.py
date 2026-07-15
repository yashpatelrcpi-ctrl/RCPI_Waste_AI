import sqlite3
conn = sqlite3.connect('waste_ai.db')
cur = conn.cursor()
for table in ['users', 'citizens', 'households', 'waste_collection', 'complaints']:
    row = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
    print(table, '->', bool(row))
conn.close()
