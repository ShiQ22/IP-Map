# app/schemas/devices.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, constr, IPvAnyAddress


# ────────────────── shared base ──────────────────
class DeviceBase(BaseModel):
    account_name: constr(strip_whitespace=True, min_length=1)
    location:     constr(strip_whitespace=True, min_length=1)
    hostname:     constr(strip_whitespace=True, min_length=1)


# ────────────────── CREATE payload ───────────────
class DeviceCreate(DeviceBase):
    """
    Payload accepted by POST / PUT endpoints.
    Now includes IP/MAC/asset_tag fields so the router
    can create or update the associated IP row.
    """
    device_type: constr(strip_whitespace=True, min_length=1)
    ip_address:   IPvAnyAddress
    mac_address:  Optional[constr(strip_whitespace=True)] = None
    asset_tag:    Optional[constr(strip_whitespace=True)] = None


# ────────────────── READ / response ──────────────
class DeviceRead(DeviceBase):
    """
    What the API returns to the UI.  Columns that the
    DataTable looks for are included as Optional so
    their absence no longer raises ‘unknown parameter’ warnings.
    """
    id: int

    device_type:         Optional[str] = None
    ip_address:          Optional[str] = None
    mac_address:         Optional[str] = None
    asset_tag:           Optional[str] = None
    updated_by_username: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
