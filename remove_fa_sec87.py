import sqlite3
conn = sqlite3.connect('backend/constructionos.db')
conn.execute("DELETE FROM regulatory_kb WHERE code = 'FA_SEC_87'")
conn.commit()
rows = conn.execute("SELECT code, trigger_condition FROM regulatory_kb").fetchall()
print("regulatory_kb after:", rows)
conn.close()
