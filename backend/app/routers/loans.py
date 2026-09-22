from fastapi import APIRouter, HTTPException
from app.schemas.loan import LoanUpdateRequest, LockRequest
from app.services.mortgage_service import MortgageService, LoanNotFound, LoanLockedError
router = APIRouter()
def _view(row):
    row["locked"] = bool(row.get("locked"))
    return row
@router.get("/loans")
def list_loans():
    with MortgageService() as s: return {"items": [_view(x) for x in s.list_loans()]}
@router.get("/loans/{loan_id}")
def get_loan(loan_id: int):
    with MortgageService() as s:
        row = s.loan(loan_id)
        if not row: raise HTTPException(404)
        return _view(row)
@router.patch("/loans/{loan_id}")
def patch_loan(loan_id: int, body: LoanUpdateRequest):
    with MortgageService() as s:
        try:
            row = s.update_loan(loan_id, body.principal, body.annual_rate, body.months)
        except LoanNotFound as e:
            raise HTTPException(404, detail=str(e))
        except LoanLockedError as e:
            raise HTTPException(409, detail=str(e))
        return _view(row)
@router.post("/loans/{loan_id}/lock")
def post_lock(loan_id: int, body: LockRequest):
    with MortgageService() as s:
        try:
            row = s.set_lock(loan_id, body.locked)
        except LoanNotFound as e:
            raise HTTPException(404, detail=str(e))
        return _view(row)
