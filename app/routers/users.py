from fastapi import (
    APIRouter, Depends, HTTPException,
    Path, status, UploadFile, File
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import csv, io
from typing import List

from app.database import get_db
from app.models import User, IP, OwnerType, Admin
from app.schemas.users import UserCreate, UserRead
from app.schemas.ips import IPRead, IPUserCreate
from app.utils.security import (
    require_admin, require_viewer_or_admin, get_current_admin
)

router = APIRouter(prefix="/users", tags=["users"])

# ─────────────────────────  BASIC USER CRUD  ───────────────────────── #

@router.get("", response_model=List[UserRead],
            dependencies=[Depends(require_viewer_or_admin)])
@router.get("/", response_model=List[UserRead],
            dependencies=[Depends(require_viewer_or_admin)],
            include_in_schema=False)
async def list_users(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(User))).scalars().all()
    out: list[UserRead] = []
    for u in rows:
        if u.department is None:
            u.department = ""
        out.append(UserRead.from_orm(u))
    return out

@router.post("", response_model=UserRead,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(**payload.dict())
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

# allow trailing-slash variant so JS POST /api/users/ works
@router.post("/", response_model=UserRead,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)],
             include_in_schema=False)
async def create_user_slash(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(payload, db)

@router.put("/{user_id}", response_model=UserRead,
            dependencies=[Depends(require_admin)])
async def update_user(user_id: int, payload: UserCreate,
                      db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    for k, v in payload.dict().items():
        setattr(user, k, v)
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await db.delete(user)
    await db.commit()

# ─────────────────────────  CSV IMPORT  ─────────────────────────────── #

@router.post("/import", status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
async def import_users(file: UploadFile = File(...),
                       db:   AsyncSession = Depends(get_db)):
    reader = csv.DictReader(io.StringIO((await file.read()).decode()))
    created: list[User] = []
    for r in reader:
        if not r.get("username") or not r.get("naos_id"):
            continue
        dup = await db.execute(select(User).where(User.naos_id == r["naos_id"].strip()))
        if dup.scalars().first():
            continue
        user = User(
            username   = r["username"].strip(),
            naos_id    = r["naos_id"].strip(),
            department = (r.get("department") or "").strip()
        )
        db.add(user)
        created.append(user)

    await db.commit()
    for u in created:
        await db.refresh(u)
    return created

# ───────────────────────  HELPER  ───────────────────────────────────── #

def as_ipread(ip: IP, *, owner: User, updater_name: str | None) -> IPRead:
    if ip.department is None:
        ip.department = ""
    base = IPRead.from_orm(ip)
    return base.copy(update={
        "department":           ip.department,
        "owner_username":       owner.username,
        "owner_naos_id":        owner.naos_id,
        "updated_by_username":  updater_name,
    })

# ─────────────────────  USER-SCOPED IP ENDPOINTS  ───────────────────── #

@router.get("/{user_id}/ips", response_model=List[IPRead],
            dependencies=[Depends(require_viewer_or_admin)])
async def list_user_ips(user_id: int = Path(...),
                        db: AsyncSession = Depends(get_db)):
    owner = await db.get(User, user_id)
    if not owner:
        raise HTTPException(404, "User not found")
    q = await db.execute(select(IP).where(
        IP.owner_type == OwnerType.user,
        IP.owner_id   == user_id
    ))
    rows = q.scalars().all()
    out: list[IPRead] = []
    for ip in rows:
        upd = (await db.get(Admin, ip.updated_by)).username if ip.updated_by else None
        out.append(as_ipread(ip, owner=owner, updater_name=upd))
    return out

@router.post(
    "/{user_id}/ips",
    response_model=List[IPRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Add one or more IPs to a user"
)
async def add_user_ips(
    entries: List[IPUserCreate],
    user_id: int = Path(..., description="User ID"),
    admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> List[IPRead]:
    owner = await db.get(User, user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="User not found")

    created: list[IP] = []
    # 1) duplicate checks & create
    for e in entries:
        dup = await db.execute(select(IP).where(IP.ip_address == e.ip_address))
        if (d := dup.scalars().first()):
            raise HTTPException(
                status_code=400,
                detail=f"IP {e.ip_address} already assigned to {d.owner_type} #{d.owner_id}"
            )
        ip = IP(
            owner_type  = OwnerType.user,
            owner_id    = user_id,
            department  = e.department,
            device_type = e.device_type,
            ip_address  = e.ip_address,
            mac_address = e.mac_address,
            asset_tag   = e.asset_tag,
            updated_by  = admin.id
        )
        db.add(ip)
        created.append(ip)

        # sync department
        if owner.department == "" and e.department:
            owner.department = e.department

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Duplicate IP detected during save")

    # 2) build the response
    out: list[IPRead] = []
    for ip in created:
        await db.refresh(ip)
        out.append(as_ipread(ip, owner=owner, updater_name=admin.username))
    return out

@router.put("/{user_id}/ips/{ip_id}", response_model=IPRead,
            dependencies=[Depends(require_admin)])
async def update_user_ip(
    entry:   IPUserCreate,
    user_id: int = Path(...),
    ip_id:   int = Path(...),
    admin   = Depends(get_current_admin),
    db:      AsyncSession = Depends(get_db)
):
    ip = await db.get(IP, ip_id)
    if not ip or ip.owner_type != OwnerType.user or ip.owner_id != user_id:
        raise HTTPException(404, "User IP not found")

    for k, v in entry.dict().items():
        setattr(ip, k, v)
    ip.updated_by = admin.id

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(400, "Duplicate IP address")
    await db.refresh(ip)

    owner = await db.get(User, user_id)
    return as_ipread(ip, owner=owner, updater_name=admin.username)

@router.delete("/{user_id}/ips/{ip_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
async def delete_user_ip(user_id: int = Path(...), ip_id: int = Path(...),
                         db: AsyncSession = Depends(get_db)):
    ip = await db.get(IP, ip_id)
    if not ip or ip.owner_type != OwnerType.user or ip.owner_id != user_id:
        raise HTTPException(404, "User IP not found")
    await db.delete(ip)
    await db.commit()
