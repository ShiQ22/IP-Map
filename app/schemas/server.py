# app/schemas/server.py

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class IPServerCreate(BaseModel):
    ip_address: str
    mac_address: Optional[str] = None
    asset_tag:   Optional[str] = None

class ServerCreate(BaseModel):
    server_name: str
    location:    str
    description: Optional[str] = None

class IPReadServer(BaseModel):
    id:         int
    ip_address:str
    mac_address:Optional[str]
    asset_tag:  Optional[str]
    created_at: datetime
    updated_at: datetime
    updated_by_username: Optional[str]

    class Config:
        orm_mode = True

class ServerRead(BaseModel):
    id:          int
    server_name:str
    location:    str
    description: Optional[str]
    created_at:  datetime
    updated_at:  datetime
    ips:         List[IPReadServer] = []

    class Config:
        orm_mode = True

class ServerFlat(BaseModel):
    server_id:   int
    server_name: str
    location:    str
    description: Optional[str]
    ip_id:       int
    ip_address:  str
    mac_address: Optional[str]
    asset_tag:   Optional[str]
    added_on:    datetime
    updated_by:  Optional[str]
    updated_at:  datetime

    class Config:
        orm_mode = True
