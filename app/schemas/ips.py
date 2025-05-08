# app/schemas/ips.py

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models import OwnerType

class IPBase(BaseModel):
    ip_address: str
    mac_address: Optional[str] = None
    asset_tag: Optional[str] = None
    owner_type: OwnerType
    owner_id: int

class IPCreate(IPBase):
    """Fields required to create a new IP."""
    pass

class IPRead(IPBase):
    """Fields returned when reading an IP."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
