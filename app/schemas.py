from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import Optional, List

class UnitBase(BaseModel):
    name: str

class UnitCreate(UnitBase):
    pass

class UnitOut(UnitBase):
    id: int
    class Config:
        from_attributes = True

class UserBase(BaseModel):
    full_name: str
    role: str

class UserCreate(UserBase):
    pass

class UserOut(UserBase):
    id: int
    class Config:
        from_attributes = True

class LegalRequestBase(BaseModel):
    title: str
    description: Optional[str] = None
    unit_id: int
    complexity: int = Field(2, ge=1, le=3)
    due_date: Optional[date] = None
    status: str = "PENDIENTE"

class LegalRequestCreate(LegalRequestBase):
    pass

class LegalRequestOut(LegalRequestBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class AssignmentBase(BaseModel):
    request_id: int
    assignee_id: int

class AssignmentCreate(AssignmentBase):
    pass

class AssignmentOut(AssignmentBase):
    id: int
    class Config:
        from_attributes = True

class PrioritizedTask(BaseModel):
    request: LegalRequestOut
    assignees: List[UserOut]
    score: float
