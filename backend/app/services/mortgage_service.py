from app.db import connect
from app.engines.amortization import equal_payment_schedule
from app.repositories import loans, runs, settings

READ_ONLY_FIELDS = ("principal", "annual_rate", "months")

class LoanLockedError(Exception):
    def __init__(self, loan_id, name, fields):
        self.loan_id = loan_id
        self.name = name
        self.fields = fields
        super().__init__(
            f"贷款档案 #{loan_id}（{name}）已锁定，只读字段 {', '.join(fields)} 不可修改"
        )

class MortgageService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_loans(self): return loans.list_all(self._c)
    def loan(self, lid): return loans.get(self._c, lid)
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50): return runs.list_recent(self._c, limit)
    def update_loan_params(self, lid, principal=None, annual_rate=None, months=None):
        row = loans.get(self._c, lid)
        if not row: return None
        changes = {k: v for k, v in (
            ("principal", principal), ("annual_rate", annual_rate), ("months", months),
        ) if v is not None}
        if not changes: return row
        if row["locked"]:
            blocked = [f for f in READ_ONLY_FIELDS if f in changes]
            raise LoanLockedError(row["id"], row["name"], blocked)
        return loans.update_params(self._c, lid, changes)
    def set_loan_locked(self, lid, locked):
        row = loans.get(self._c, lid)
        if not row: return None
        # 锁定/解锁只翻转档案状态，绝不写 calc_runs 历史
        return loans.set_locked(self._c, lid, locked)
    def schedule(self, principal, annual_rate, months, loan_id, persist, preview_rows=12):
        full = equal_payment_schedule(principal, annual_rate, months)
        out = {k: full[k] for k in ("monthly_payment", "total_interest", "total_payment")}
        out["preview"] = full["rows"][:preview_rows]
        out["row_count"] = len(full["rows"])
        locked = None
        if loan_id is not None:
            loan_row = loans.get(self._c, loan_id)
            if loan_row is not None:
                locked = loan_row["locked"]
        rid = None
        # 锁定不禁止只读测算，也不禁止 persist 写入
        if persist:
            rid = runs.insert(self._c, "schedule", {"principal": principal, "annual_rate": annual_rate, "months": months}, out, loan_id)
        return {"run_id": rid, "locked": locked, **out}
    def dashboard(self):
        items = loans.list_all(self._c)
        return {"loan_count": len(items), "clean": len([x for x in items if "种子" not in x["name"]]), "dirty": len([x for x in items if "种子" in x["name"]])}
