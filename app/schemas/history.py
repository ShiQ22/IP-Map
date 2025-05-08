# app/schemas/history.py

from pydantic import BaseModel
from datetime import datetime

class HistoryBase(BaseModel):
    ip: str
    hostname: str
    mac_address: str
    vendor: str
    status: str
    scan_time: datetime

class HistoryCreate(HistoryBase):
    """Fields required to create a new history record."""
    pass

class HistoryRead(HistoryBase):
    """Fields returned when reading history entries."""
    id: int

    class Config:
        orm_mode = True
