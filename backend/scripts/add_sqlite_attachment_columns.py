import sqlite3
from pathlib import Path

DB = Path('D:/itdesk/backend/dev_local.db')
if not DB.exists():
    print('DB not found:', DB)
    raise SystemExit(1)

con = sqlite3.connect(DB)
cur = con.cursor()

# Helper: get existing columns
cur.execute("PRAGMA table_info('attachments')")
cols = [r[1] for r in cur.fetchall()]
print('Existing columns:', cols)

to_add = [
    ("sensitivity_level", "TEXT", "'REGULAR'"),
    ("retention_days", "INTEGER", None),
    ("status", "TEXT", "'ACTIVE'"),
    ("redacted_at", "TEXT", None),
    ("expires_at", "TEXT", None),
]

for name, typ, default in to_add:
    if name in cols:
        print('Already present:', name)
        continue
    sql = f"ALTER TABLE attachments ADD COLUMN {name} {typ}"
    if default is not None:
        sql += f" DEFAULT {default}"
    try:
        print('Adding column:', name)
        cur.execute(sql)
    except Exception as e:
        print('Failed to add', name, e)

con.commit()
con.close()
print('Done')
