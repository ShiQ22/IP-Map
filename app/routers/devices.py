# app/routers/devices.py

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Device
from app.schemas.devices import DeviceCreate, DeviceRead
from app.utils.security import require_admin, require_viewer_or_admin

router = APIRouter(prefix="/devices", tags=["devices"])

@router.get(
    "/",
    response_model=list[DeviceRead],
    dependencies=[Depends(require_viewer_or_admin)]
)
async def list_devices(db: AsyncSession = Depends(get_db)):
    """List all devices."""
    result = await db.execute(select(Device))
    return result.scalars().all()

@router.post(
    "/",
    response_model=DeviceRead,
    dependencies=[Depends(require_admin)]
)
async def create_device(
    payload: DeviceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new device."""
    dev = Device(**payload.dict())
    db.add(dev)
    await db.commit()
    await db.refresh(dev)
    return dev
