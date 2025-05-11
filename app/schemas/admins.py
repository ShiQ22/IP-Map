# app/schemas/admins.py
from pydantic import BaseModel

class AdminCreate(BaseModel):
    username: str
    password: str

class AdminPasswordUpdate(BaseModel):
    password: str
