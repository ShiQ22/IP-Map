# app/routers/history.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import History
from app.schemas.history import HistoryRead, HistoryCreate
from app.utils.security import require_viewer_or_admin, require_admin

router = APIRouter(prefix="/history", tags=["history"])

@router.get("/", response_model=list[HistoryRead], dependencies=[Depends(require_viewer_or_admin)])
async def list_history(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(History))
    return q.scalars().all()

@router.post("/", response_model=HistoryRead, dependencies=[Depends(require_admin)])
async def create_history(payload: HistoryCreate, db: AsyncSession = Depends(get_db)):
    hist = History(**payload.dict())
    db.add(hist)
    await db.commit()
    await db.refresh(hist)
    return hist

@router.get("/{id}", response_model=HistoryRead, dependencies=[Depends(require_viewer_or_admin)])
async def read_history(id: int, db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(History).where(History.id == id))
    hist = q.scalars().first()
    if not hist:
        raise HTTPException(404, "History entry not found")
    return hist
