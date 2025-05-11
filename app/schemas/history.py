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
    pass

class HistoryRead(HistoryBase):
    id: int

    class Config:
        orm_mode = True
