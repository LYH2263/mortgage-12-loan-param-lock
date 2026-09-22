import sqlite3
def list_all(conn): return [dict(r) for r in conn.execute("SELECT * FROM loans ORDER BY id").fetchall()]
def get(conn, lid):
    row = conn.execute("SELECT * FROM loans WHERE id=?", (lid,)).fetchone()
    return dict(row) if row else None
def update_params(conn, lid, principal, annual_rate, months):
    conn.execute("UPDATE loans SET principal=?, annual_rate=?, months=? WHERE id=?",
        (principal, annual_rate, months, lid))
    conn.commit()
def set_locked(conn, lid, locked):
    conn.execute("UPDATE loans SET locked=? WHERE id=?", (1 if locked else 0, lid))
    conn.commit()
