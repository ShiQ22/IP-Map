# app/schemas/users.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    naos_id:  str

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    username: Optional[str] = None
    naos_id:  Optional[str] = None

class UserRead(UserBase):
    id:         int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
