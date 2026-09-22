from pydantic import BaseModel, Field
class LoanUpdateRequest(BaseModel):
    principal: float | None = Field(default=None, gt=0)
    annual_rate: float | None = Field(default=None, ge=0)
    months: int | None = Field(default=None, gt=0, le=600)
class LockRequest(BaseModel):
    locked: bool
