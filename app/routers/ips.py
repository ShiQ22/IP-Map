# app/routers/ips.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import IP
from app.schemas.ips import IPCreate, IPRead
from app.utils.security import require_viewer_or_admin, require_admin

router = APIRouter(prefix="/ips", tags=["ips"])

@router.get("/", response_model=list[IPRead], dependencies=[Depends(require_viewer_or_admin)])
async def list_ips(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(IP))
    return q.scalars().all()

@router.post("/", response_model=IPRead, dependencies=[Depends(require_admin)])
async def create_ip(payload: IPCreate, db: AsyncSession = Depends(get_db)):
    ip = IP(**payload.dict())
    db.add(ip)
    await db.commit()
    await db.refresh(ip)
    return ip

@router.get("/{id}", response_model=IPRead, dependencies=[Depends(require_viewer_or_admin)])
async def read_ip(id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(IP).where(IP.id == id))
    ip = q.scalars().first()
    if not ip:
        raise HTTPException(404, "IP not found")
    return ip
