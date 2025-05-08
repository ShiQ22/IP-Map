# app/schemas/live.py

from pydantic import BaseModel
from datetime import datetime

class LiveMonitorRead(BaseModel):
    ip: str
    hostname: str
    mac_address: str
    vendor: str
    status: str
    last_checked: datetime
    last_up: datetime | None

    class Config:
        orm_mode = True
