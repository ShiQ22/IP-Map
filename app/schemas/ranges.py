# app/schemas/ranges.py
from pydantic import BaseModel, constr

class RangeBase(BaseModel):
    cidr: constr(strip_whitespace=True, min_length=1)

class RangeCreate(RangeBase):
    pass

class RangeRead(RangeBase):
    id: int
    active: bool

    class Config:
        orm_mode = True

class RangeUpdate(BaseModel):
    active: bool
