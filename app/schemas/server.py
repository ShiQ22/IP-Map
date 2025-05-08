# app/schemas/server.py

from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
from app.models import OwnerType

class ServerBase(BaseModel):
    server_name: str
    location: str

class ServerCreate(ServerBase):
    """Fields required to create a new Server."""
    ips: Optional[List[str]] = []

class ServerRead(ServerBase):
    """Fields returned when reading servers."""
    id: int
    created_at: datetime
    updated_at: datetime
    ips: List[str]  # we’ll return the list of IP addresses

    class Config:
        orm_mode = True
