# app/routers/ips.py
# --------------------------------------------------------------------------- #
#  Global & user-scoped CRUD for IP entries                                   #
# --------------------------------------------------------------------------- #
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List          
from fastapi import status  
from app.database import get_db
from app.config import settings
from app.snipe   import get_hardware_id
from app.models import IP, User, Device, Server, Admin, OwnerType
from app.schemas.ips import IPCreate, IPRead, IPUserCreate
from app.utils.security import require_viewer_or_admin, require_admin

router = APIRouter(prefix="/ips", tags=["ips"])


# ─── NEW: list ALL user-scoped IPs ───────────────────────────── #
@router.get(
    "/users",
    response_model=list[IPRead],
    dependencies=[Depends(require_viewer_or_admin)],
    summary="List *all* IP entries whose owner_type is 'user'"
)
async def list_all_user_ips(db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(IP).where(IP.owner_type == OwnerType.user)
    )
    rows = q.scalars().all()
    return [await enrich_row(ip, db) for ip in rows]


# ─────────────────────────────  HELPERS  ──────────────────────────────────── #

from app.config import settings
from app.snipe   import get_hardware_id

async def enrich_row(ip: IP, db: AsyncSession) -> IPRead:
    """
    Build an `IPRead` object and include:
      - owner_username / owner_naos_id for users,
      - hostname for devices/servers,
      - plus the admin username who last updated,
      - and snipe_url if asset_tag exists in Snipe-IT.
    """
    updater = await db.get(Admin, ip.updated_by) if ip.updated_by else None
    if ip.department is None:
        ip.department = ""

    if ip.owner_type == OwnerType.user:
        owner = await db.get(User, ip.owner_id)
        if not owner:
            raise HTTPException(404, "Owner user not found")
        owner_username = owner.username
        owner_naos_id  = owner.naos_id

    elif ip.owner_type == OwnerType.device:
        owner = await db.get(Device, ip.owner_id)
        if not owner:
            raise HTTPException(404, "Owner device not found")
        owner_username = owner.hostname
        owner_naos_id  = None

    elif ip.owner_type == OwnerType.server:
        owner = await db.get(Server, ip.owner_id)
        if not owner:
            raise HTTPException(404, "Owner server not found")
        owner_username = owner.hostname
        owner_naos_id  = None

    else:
        owner_username = None
        owner_naos_id  = None

    # 1) Base Pydantic conversion
    base = IPRead.from_orm(ip)

    # 2) Lookup Snipe-IT hardware ID (cached) and build full URL (or None)
    hw_id     = get_hardware_id(ip.asset_tag or "")
    snipe_url = f"{settings.SNIPE_UI}/hardware/{hw_id}" if hw_id else None

    # 3) Return enriched model including snipe_url
    return base.copy(update={
        "department":           ip.department,
        "owner_username":       owner_username,
        "owner_naos_id":        owner_naos_id,
        "updated_by_username":  updater.username if updater else None,
        "snipe_url":            snipe_url,
    })

# ─────────────────────────  GLOBAL IP CRUD  ──────────────────────────────── #

@router.get("/", response_model=list[IPRead],
            dependencies=[Depends(require_viewer_or_admin)])
async def list_ips(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(IP))
    rows = q.scalars().all()
    return [await enrich_row(ip, db) for ip in rows]


@router.post("/", response_model=IPRead,
             dependencies=[Depends(require_admin)])
async def create_ip(
    payload: IPCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Create a standalone IP entry."""
    ip = IP(**payload.dict(), updated_by=admin.id)
    db.add(ip)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "IP address already exists")
    await db.refresh(ip)
    return await enrich_row(ip, db)


@router.get("/{ip_id}", response_model=IPRead,
            dependencies=[Depends(require_viewer_or_admin)])
async def read_ip(ip_id: int, db: AsyncSession = Depends(get_db)):
    """Read a single IP entry by its ID."""
    ip = await db.get(IP, ip_id)
    if not ip:
        raise HTTPException(404, "IP not found")
    return await enrich_row(ip, db)


@router.put("/{ip_id}", response_model=IPRead,
            dependencies=[Depends(require_admin)])
async def update_ip(
    ip_id: int,
    payload: IPCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Update any IP entry by ID."""
    ip = await db.get(IP, ip_id)
    if not ip:
        raise HTTPException(404, "IP not found")

    for field, val in payload.dict().items():
        setattr(ip, field, val)
    ip.updated_by = admin.id

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "IP address already exists")
    await db.refresh(ip)
    return await enrich_row(ip, db)


@router.delete("/{ip_id}", dependencies=[Depends(require_admin)])
async def delete_ip(ip_id: int, db: AsyncSession = Depends(get_db)):
    """Delete an IP entry by ID."""
    ip = await db.get(IP, ip_id)
    if not ip:
        raise HTTPException(404, "IP not found")
    await db.delete(ip)
    await db.commit()
    return {"detail": "IP deleted"}


# ────────────────────────  USER-SCOPED IP CRUD  ─────────────────────────── #




@router.delete("/users/{user_id}/ips/{ip_id}",
               dependencies=[Depends(require_admin)])
async def delete_user_ip(
    user_id: int = Path(..., description="User ID"),
    ip_id: int = Path(..., description="IP entry ID"),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific IP entry for a user."""
    ip = await db.get(IP, ip_id)
    if (
        not ip
        or ip.owner_type != OwnerType.user
        or ip.owner_id != user_id
    ):
        raise HTTPException(404, "IP entry not found for this user")
    await db.delete(ip)
    await db.commit()
    return {"detail": "User-scoped IP deleted"}
