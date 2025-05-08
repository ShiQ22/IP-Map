# app/routers/server.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import Server, IP  
from app.schemas.server import ServerCreate, ServerRead

router = APIRouter(prefix="/servers", tags=["servers"])

@router.post("/", response_model=ServerRead)
async def create_server(payload: ServerCreate, db: AsyncSession = Depends(get_db)):
    # مثال: تأكد إن اسم السيرفر غير مكرر
    q = await db.execute(select(Server).where(Server.server_name == payload.server_name))
    if q.scalars().first():
        raise HTTPException(400, "server_name must be unique")

    # أنشئ كيان السيرفر
    srv = Server(
        server_name=payload.server_name,
        location=payload.location,
        mac_address=payload.mac_address,
    )
    db.add(srv)
    await db.commit()
    await db.refresh(srv)

    # أضف الـ IPs المرتبطة (لو payload.ips موجودة)
    for ip in payload.ips:
        sip = ServerIP(server_id=srv.id, ip=ip)
        db.add(sip)
    await db.commit()

    # جلب الـ IPs الحديثة وعرضها
    await db.refresh(srv)
    return srv

@router.get("/", response_model=list[ServerRead])
async def list_servers(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(Server).options(selectinload(Server.ips)))
    return q.scalars().all()

@router.get("/{id}", response_model=ServerRead)
async def read_server(id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(
        select(Server).where(Server.id == id).options(selectinload(Server.ips))
    )
    srv = q.scalars().first()
    if not srv:
        raise HTTPException(404, "Server not found")
    return srv
