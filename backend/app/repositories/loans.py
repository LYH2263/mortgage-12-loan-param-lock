LOCKED_FIELDS = ("principal", "annual_rate", "months")

def _to_dict(row):
    d = dict(row)
    d["locked"] = bool(d.get("locked", 0))
    return d

def list_all(conn):
    return [_to_dict(r) for r in conn.execute("SELECT * FROM loans ORDER BY id").fetchall()]

def get(conn, lid):
    row = conn.execute("SELECT * FROM loans WHERE id=?", (lid,)).fetchone()
    return _to_dict(row) if row else None

def update_params(conn, lid, fields):
    assignments = ", ".join(f"{k}=?" for k in fields)
    values = [fields[k] for k in fields] + [lid]
    conn.execute(f"UPDATE loans SET {assignments} WHERE id=?", values)
    conn.commit()
    return get(conn, lid)

def set_locked(conn, lid, locked):
    conn.execute("UPDATE loans SET locked=? WHERE id=?", (1 if locked else 0, lid))
    conn.commit()
    return get(conn, lid)
