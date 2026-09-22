from app.db import connect
from app.engines.amortization import equal_payment_schedule
from app.repositories import loans, runs, settings

FIELD_LABELS = {"principal": "本金(principal)", "annual_rate": "年利率(annual_rate)", "months": "期数(months)"}

class LoanNotFound(LookupError):
    def __init__(self, lid): self.lid = lid
    def __str__(self): return f"贷款档案 #{self.lid} 不存在"

class LoanLockedError(PermissionError):
    def __init__(self, lid, name, fields):
        self.lid = lid
        self.name = name
        self.fields = list(fields)
    def __str__(self):
        names = "、".join(FIELD_LABELS.get(f, f) for f in self.fields)
        return f"贷款档案 #{self.lid}（{self.name}）已锁定，只读字段不可修改：{names}"

class MortgageService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_loans(self): return loans.list_all(self._c)
    def loan(self, lid): return loans.get(self._c, lid)
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50): return runs.list_recent(self._c, limit)
    def update_loan(self, lid, principal=None, annual_rate=None, months=None):
        row = loans.get(self._c, lid)
        if not row: raise LoanNotFound(lid)
        changes = {"principal": principal, "annual_rate": annual_rate, "months": months}
        provided = {k: v for k, v in changes.items() if v is not None}
        if row.get("locked"):
            blocked = [k for k, v in provided.items() if v != row[k]]
            if blocked: raise LoanLockedError(lid, row["name"], blocked)
        merged = {k: (provided.get(k, row[k])) for k in changes}
        if provided:
            loans.update_params(self._c, lid, merged["principal"], merged["annual_rate"], merged["months"])
        return loans.get(self._c, lid)
    def set_lock(self, lid, locked):
        row = loans.get(self._c, lid)
        if not row: raise LoanNotFound(lid)
        loans.set_locked(self._c, lid, locked)
        return loans.get(self._c, lid)
    def schedule(self, principal, annual_rate, months, loan_id, persist, preview_rows=12):
        full = equal_payment_schedule(principal, annual_rate, months)
        out = {k: full[k] for k in ("monthly_payment", "total_interest", "total_payment")}
        out["preview"] = full["rows"][:preview_rows]
        out["row_count"] = len(full["rows"])
        locked = False
        if loan_id is not None:
            row = loans.get(self._c, loan_id)
            if row: locked = bool(row.get("locked"))
        out["locked"] = locked
        rid = None
        if persist:
            rid = runs.insert(self._c, "schedule", {"principal": principal, "annual_rate": annual_rate, "months": months}, out, loan_id)
        return {"run_id": rid, **out}
    def dashboard(self):
        items = loans.list_all(self._c)
        return {"loan_count": len(items), "clean": len([x for x in items if "种子" not in x["name"]]), "dirty": len([x for x in items if "种子" in x["name"]])}
