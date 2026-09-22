from fastapi import APIRouter, HTTPException
from app.schemas.loan import LoanLockRequest, LoanUpdateRequest
from app.services.mortgage_service import LoanLockedError, MortgageService
router = APIRouter()
@router.get("/loans")
def list_loans():
    with MortgageService() as s: return {"items": s.list_loans()}
@router.get("/loans/{loan_id}")
def get_loan(loan_id: int):
    with MortgageService() as s:
        row = s.loan(loan_id)
        if not row: raise HTTPException(404)
        return row
@router.patch("/loans/{loan_id}")
def patch_loan(loan_id: int, body: LoanUpdateRequest):
    with MortgageService() as s:
        try:
            row = s.update_loan_params(loan_id, body.principal, body.annual_rate, body.months)
        except LoanLockedError as e:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": str(e),
                    "loan_id": e.loan_id,
                    "loan_name": e.name,
                    "read_only_fields": e.fields,
                    "locked": True,
                },
            )
        if not row: raise HTTPException(404)
        return row
@router.post("/loans/{loan_id}/lock")
def lock_loan(loan_id: int, body: LoanLockRequest):
    with MortgageService() as s:
        row = s.set_loan_locked(loan_id, body.locked)
        if not row: raise HTTPException(404)
        return row
