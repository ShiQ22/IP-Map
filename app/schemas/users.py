from datetime import datetime
from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    naos_id: str
    department: str


class UserCreate(UserBase):
    """
    For POST /users and individual + button-driven creation.
    Fields: username, naos_id, department.
    """
    pass


class UserRead(UserBase):
    """
    For GET /users
    Exposes: id, username, naos_id, department, created_at, updated_at.
    """
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
