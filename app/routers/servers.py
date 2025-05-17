# app/routers/servers.py

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    status
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import List

from app.database import get_db
from app.models import Server, IP, OwnerType, Admin
from app.schemas.server import (
    ServerCreate,
    ServerRead,
    ServerFlat,
    IPServerCreate,
    IPReadServer
)
from app.utils.security import (
    require_admin,
    require_viewer_or_admin,
    get_current_admin
)

router = APIRouter(prefix="/servers", tags=["servers"])


# ─────────────── BASIC SERVER CRUD ─────────────── #

@router.get("", response_model=List[ServerRead],
            dependencies=[Depends(require_viewer_or_admin)])
async def list_servers(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Server))).scalars().all()
    return [ServerRead.from_orm(s) for s in rows]


@router.post("", response_model=ServerRead,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_admin)])
async def create_server(
    payload: ServerCreate,
    db: AsyncSession = Depends(get_db)
):
    srv = Server(**payload.dict())
    db.add(srv)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        # likely duplicate server_name
        raise HTTPException(
            status_code=400,
            detail="server_name must be unique"
        )
    await db.refresh(srv)
    return srv


@router.put("/{srv_id}", response_model=ServerRead,
            dependencies=[Depends(require_admin)])
async def update_server(
    srv_id: int,
    payload: ServerCreate,
    db: AsyncSession = Depends(get_db)
):
    srv = await db.get(Server, srv_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    for field, val in payload.dict().items():
        setattr(srv, field, val)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="server_name must be unique"
        )
    await db.refresh(srv)
    return srv


@router.delete("/{srv_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_admin)])
async def delete_server(
    srv_id: int,
    db: AsyncSession = Depends(get_db)
):
    srv = await db.get(Server, srv_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    await db.delete(srv)
    await db.commit()


# ─────────────── FLAT LIST FOR DATATABLE ─────────────── #

@router.get("/flat", response_model=List[ServerFlat],
            dependencies=[Depends(require_viewer_or_admin)])
async def flat_list(db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(IP, Server, Admin.username)
        .join(
            Server,
            (IP.owner_id == Server.id) &
            (IP.owner_type == OwnerType.server)
        )
        .outerjoin(Admin, IP.updated_by == Admin.id)
    )
    out: List[ServerFlat] = []
    for ip, srv, updater in q.all():
        out.append(ServerFlat(
            server_id   = srv.id,
            server_name = srv.server_name,
            location    = srv.location,
            description = srv.description,
            ip_id       = ip.id,
            ip_address  = ip.ip_address,
            mac_address = ip.mac_address,
            asset_tag   = ip.asset_tag,
            added_on    = ip.created_at,
            updated_by  = updater,
            updated_at  = ip.updated_at 
        ))
    return out


# ────────── GET SINGLE SERVER (with trailing‐slash alias) ────────── #

@router.get(
    "/{srv_id}",
    response_model=ServerRead,
    dependencies=[Depends(require_viewer_or_admin)]
)
@router.get(
    "/{srv_id}/",
    response_model=ServerRead,
    dependencies=[Depends(require_viewer_or_admin)]
)
async def get_server(
    srv_id: int = Path(..., description="Server ID"),
    db: AsyncSession = Depends(get_db)
) -> ServerRead:
    srv = await db.get(Server, srv_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    # load its IPs
    q = await db.execute(
        select(IP, Admin.username)
        .where(
            IP.owner_type == OwnerType.server,
            IP.owner_id == srv_id
        )
        .outerjoin(Admin, IP.updated_by == Admin.id)
    )
    ips: List[IPReadServer] = []
    for ip, updater in q.all():
        rec = IPReadServer.from_orm(ip)
        rec.updated_by_username = updater
        ips.append(rec)

    return ServerRead(
        id          = srv.id,
        server_name = srv.server_name,
        location    = srv.location,
        description = srv.description,
        created_at  = srv.created_at,
        updated_at  = srv.updated_at,
        ips         = ips
    )


# ──────────────── SERVER-SCOPED IPs ──────────────── #

def _as_ip(ip: IP, updater: str | None) -> IPReadServer:
    rec = IPReadServer.from_orm(ip)
    rec.updated_by_username = updater
    return rec


@router.get("/{srv_id}/ips", response_model=List[IPReadServer],
            dependencies=[Depends(require_viewer_or_admin)])
async def list_server_ips(
    srv_id: int = Path(..., description="Server ID"),
    db: AsyncSession = Depends(get_db)
):
    srv = await db.get(Server, srv_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    q = await db.execute(
        select(IP, Admin.username)
        .where(
            IP.owner_type == OwnerType.server,
            IP.owner_id == srv_id
        )
        .outerjoin(Admin, IP.updated_by == Admin.id)
    )
    out = []
    for ip, updater in q.all():
        out.append(_as_ip(ip, updater))
    return out


@router.post(
    "/{srv_id}/ips",
    response_model=List[IPReadServer],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Add one or more IPs to a server"
)
async def add_server_ips(
    entries: List[IPServerCreate],
    srv_id: int = Path(..., description="Server ID"),
    admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> List[IPReadServer]:
    srv = await db.get(Server, srv_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    created = []
    for e in entries:
        dup = await db.execute(
            select(IP).where(IP.ip_address == e.ip_address)
        )
        if (d := dup.scalars().first()):
            raise HTTPException(
                status_code=400,
                detail=f"IP {e.ip_address} already assigned to {d.owner_type} #{d.owner_id}"
            )
        ip = IP(
            owner_type  = OwnerType.server,
            owner_id    = srv_id,
            ip_address  = e.ip_address,
            mac_address = e.mac_address,
            asset_tag   = e.asset_tag,
            updated_by  = admin.id
        )
        db.add(ip)
        created.append(ip)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Duplicate IP detected during save"
        )

    out = []
    for ip in created:
        await db.refresh(ip)
        out.append(_as_ip(ip, admin.username))
    return out


@router.put("/{srv_id}/ips/{ip_id}", response_model=IPReadServer,
            dependencies=[Depends(require_admin)])
async def update_server_ip(
    payload:   IPServerCreate,
    srv_id:    int = Path(..., description="Server ID"),
    ip_id:     int = Path(..., description="IP ID"),
    admin     = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    ip = await db.get(IP, ip_id)
    if not ip or ip.owner_type != OwnerType.server or ip.owner_id != srv_id:
        raise HTTPException(status_code=404, detail="Server IP not found")

    for field, val in payload.dict().items():
        setattr(ip, field, val)
    ip.updated_by = admin.id

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Duplicate IP address"
        )

    await db.refresh(ip)
    return _as_ip(ip, admin.username)


@router.delete(
    "/{srv_id}/ips/{ip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)]
)
async def delete_server_ip(
    srv_id: int = Path(..., description="Server ID"),
    ip_id:  int = Path(..., description="IP ID"),
    db: AsyncSession = Depends(get_db),
):
    ip = await db.get(IP, ip_id)
    if not ip or ip.owner_type != OwnerType.server or ip.owner_id != srv_id:
        raise HTTPException(status_code=404, detail="Server IP not found")

    await db.delete(ip)
    await db.commit()
