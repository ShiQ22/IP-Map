# app/routers/servers.py

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models import Admin
from app.database import get_db
from app.models import Server, IP
from app.schemas.server import (
    ServerCreate,
    ServerRead,
    IPCreate,
    IPRead,
    ServerFlat
)

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get(
    "/flat",
    response_model=List[ServerFlat],
    summary="Flat list of all server IP rows"
)
async def flat_servers(
    _ : Optional[str] = Query(None, alias="_"),
    db: AsyncSession = Depends(get_db)
) -> List[ServerFlat]:
    stmt = (
      select(IP, Server, Admin.username.label("updated_by_name"))
      .join(Server, (IP.owner_type=="server")&(IP.owner_id==Server.id))
      .outerjoin(Admin, Admin.id==IP.updated_by)
       .order_by(Server.server_name)
     )
    result = await db.execute(stmt)

    return [
        {
            "server_id":     srv.id,
            "server_name":   srv.server_name,
            "location":      srv.location,
            "description":   srv.description,
            "ip_id":         ip.id,
            "ip_address":    ip.ip_address,
            "mac_address":   ip.mac_address,
            "asset_tag":     ip.asset_tag,
            "added_on":      ip.created_at,
            "updated_by":    ip.updated_by,
        }
        for ip, srv in result.all()
    ]


@router.post(
    "/",
    response_model=ServerRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new server"
)
async def create_server(
    payload: ServerCreate,
    db: AsyncSession = Depends(get_db)
) -> ServerRead:
    # ensure unique server_name
    q = await db.execute(
        select(Server).where(Server.server_name == payload.server_name)
    )
    if q.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="server_name must be unique"
        )

    srv = Server(
        server_name=payload.server_name,
        location=payload.location,
        description=payload.description
    )
    db.add(srv)
    await db.commit()
    await db.refresh(srv)
    return srv


@router.get(
    "/",
    response_model=List[ServerRead],
    summary="List all servers with their IPs"
)
async def list_servers(
    db: AsyncSession = Depends(get_db)
) -> List[ServerRead]:
    # 1) load all servers
    result = await db.execute(
        select(Server).order_by(Server.server_name)
    )
    servers = result.scalars().all()

    # 2) load all IPs for these servers
    if servers:
        srv_ids = [s.id for s in servers]
        ip_rows = (await db.execute(
            select(IP).where(
                (IP.owner_type == "server") &
                (IP.owner_id.in_(srv_ids))
            )
        )).scalars().all()
    else:
        ip_rows = []

    # 3) group IPs by server_id
    ip_map: dict[int, List[IP]] = {}
    for ip in ip_rows:
        ip_map.setdefault(ip.owner_id, []).append(ip)

    # 4) attach IPs
    for s in servers:
        setattr(s, "ips", ip_map.get(s.id, []))

    return servers


@router.get(
    "/{server_id}",
    response_model=ServerRead,
    summary="Get a single server by ID"
)
async def read_server(
    server_id: int = Path(..., description="ID of the server"),
    db: AsyncSession = Depends(get_db)
) -> ServerRead:
    # 1) load server
    srv = await db.get(Server, server_id)
    if not srv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    # 2) load its IPs
    ip_rows = (await db.execute(
        select(IP).where(
            (IP.owner_type == "server") &
            (IP.owner_id == server_id)
        )
    )).scalars().all()

    setattr(srv, "ips", ip_rows)
    return srv


@router.put(
    "/{server_id}",
    response_model=ServerRead,
    summary="Update server metadata"
)
async def update_server(
    payload: ServerCreate,
    server_id: int = Path(..., description="ID of the server to update"),
    db: AsyncSession = Depends(get_db)
) -> ServerRead:
    srv = await db.get(Server, server_id)
    if not srv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    # ensure new name is unique
    if payload.server_name != srv.server_name:
        q = await db.execute(
            select(Server).where(Server.server_name == payload.server_name)
        )
        if q.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="server_name must be unique"
            )

    await db.execute(
        update(Server)
        .where(Server.id == server_id)
        .values(
            server_name=payload.server_name,
            location=payload.location,
            description=payload.description
        )
    )
    await db.commit()
    await db.refresh(srv)
    return srv


@router.delete(
    "/{server_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a server and all its IPs"
)
async def delete_server(
    server_id: int = Path(..., description="ID of the server to delete"),
    db: AsyncSession = Depends(get_db)
):
    srv = await db.get(Server, server_id)
    if not srv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )
    await db.delete(srv)
    await db.commit()


@router.post(
    "/{server_id}/ips",
    response_model=List[IPRead],
    status_code=status.HTTP_201_CREATED,
    summary="Add one or more IPs to a server"
)
async def add_server_ips(
    entries: List[IPCreate],
    server_id: int = Path(..., description="ID of the server"),
    db: AsyncSession = Depends(get_db)
) -> List[IPRead]:
    srv = await db.get(Server, server_id)
    if not srv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server not found"
        )

    created = []
    for e in entries:
        dup = await db.execute(
            select(IP).where(IP.ip_address == e.ip_address)
        )
        if dup.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"IP {e.ip_address!r} already exists"
            )
        ip = IP(
            ip_address=e.ip_address,
            mac_address=e.mac_address,
            asset_tag=e.asset_tag,
            owner_type="server",
            owner_id=server_id
        )
        db.add(ip)
        created.append(ip)

    await db.commit()
    return [await db.refresh(ip) or ip for ip in created]


@router.delete(
    "/ips/{ip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a single IP from a server"
)
async def delete_server_ip(
    ip_id: int = Path(..., description="ID of the IP record"),
    db: AsyncSession = Depends(get_db)
):
    ip = await db.get(IP, ip_id)
    if not ip or ip.owner_type != "server":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server IP not found"
        )
    await db.delete(ip)
    await db.commit()
