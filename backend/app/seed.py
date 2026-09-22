import json
from app.db import connect
from app.engines.amortization import equal_payment_schedule

def _column_exists(conn, table, column):
    return any(r["name"] == column for r in conn.execute(f"PRAGMA table_info({table})").fetchall())

def init_db():
    conn = connect()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS loans(id INTEGER PRIMARY KEY, name TEXT, principal REAL, annual_rate REAL, months INTEGER, locked INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    CREATE TABLE IF NOT EXISTS calc_runs(id INTEGER PRIMARY KEY, kind TEXT, loan_id INTEGER, input_json TEXT, result_json TEXT, created_at TEXT);
    """)
    if not _column_exists(conn, "loans", "locked"):
        conn.execute("ALTER TABLE loans ADD COLUMN locked INTEGER NOT NULL DEFAULT 0")
    if conn.execute("SELECT COUNT(*) c FROM loans").fetchone()["c"] == 0:
        conn.execute("INSERT INTO loans(name,principal,annual_rate,months,locked) VALUES ('首套样例',1000000,3.5,360,0)")
        conn.execute("INSERT INTO loans(name,principal,annual_rate,months,locked) VALUES ('高利率种子',800000,6.8,240,0)")
        conn.execute("INSERT INTO settings(key,value) VALUES ('method','equal_payment')")
        sch = equal_payment_schedule(1000000, 3.5, 360)
        slim = {"monthly_payment": sch["monthly_payment"], "total_interest": sch["total_interest"], "preview": sch["rows"][:3]}
        conn.execute("INSERT INTO calc_runs(kind,loan_id,input_json,result_json,created_at) VALUES ('schedule',1,?,?,datetime('now'))",
            (json.dumps({"principal": 1000000, "annual_rate": 3.5, "months": 360}), json.dumps(slim)))
    conn.commit()
    conn.close()
