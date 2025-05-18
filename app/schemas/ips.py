# app/schemas/ips.py
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class OwnerType(str, Enum):
    user   = "user"
    device = "device"
    server = "server"


class DeviceType(str, Enum):
    pc      = "pc"
    laptop  = "laptop"
    mobile  = "mobile"
    tablet  = "tablet"
    wifi    = "wifi"
    other   = "other"


class IPBase(BaseModel):
    # ← make it a plain string with a default, **not** Optional
    department: str = ""
    device_type: DeviceType
    ip_address: str
    mac_address: Optional[str] = None
    asset_tag:   Optional[str] = None


class IPCreate(IPBase):
    owner_type: OwnerType
    owner_id:   int


class IPUserCreate(IPBase):
    pass


class IPRead(IPBase):
    id: int
    owner_type: OwnerType
    owner_id: int
    created_at: datetime
    updated_at: datetime

    # these can truly be optional
    owner_username:       Optional[str] = None
    owner_naos_id:        Optional[str] = None
    updated_by_username:  Optional[str] = None
    snipe_url:            Optional[str] = None
    class Config:
        orm_mode = True
