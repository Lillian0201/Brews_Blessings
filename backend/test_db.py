from db import get_conn

conn = get_conn()
cur = conn.cursor()
cur.execute("SELECT version();")
print(cur.fetchone()[0])
conn.close()