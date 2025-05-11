from typing import List, Optional
from datetime import datetime

from pydantic import BaseModel, IPvAnyAddress

#
# ---- REQUEST BODIES ----
#
class IPCreate(BaseModel):
    ip_address: IPvAnyAddress
    mac_address: Optional[str] = None
    asset_tag: Optional[str] = None


class ServerCreate(BaseModel):
    server_name: str
    location: str
    description: Optional[str] = None


#
# ---- RESPONSE SCHEMAS ----
#
class IPRead(BaseModel):
    id: int
    ip_address: IPvAnyAddress
    mac_address: Optional[str]
    asset_tag: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ServerRead(BaseModel):
    id: int
    server_name: str
    location: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    ips: List[IPRead] = []

    class Config:
        orm_mode = True


#
# ---- FLAT SCHEMA ----
#
class ServerFlat(BaseModel):
    server_id:   int
    server_name: str
    location:    str
    description: Optional[str]
    ip_id:       int
    ip_address:  IPvAnyAddress
    mac_address: Optional[str]
    asset_tag:   Optional[str]
    added_on:    datetime
    updated_by:  Optional[int]

    class Config:
        orm_mode = True
