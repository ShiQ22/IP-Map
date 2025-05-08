# app/schemas/devices.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class DeviceBase(BaseModel):
    account_name: str
    location:     str
    hostname:     str

class DeviceCreate(DeviceBase):
    pass

class DeviceRead(DeviceBase):
    id:         int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
