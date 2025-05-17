# app/routers/ranges.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import IPRange
from app.schemas.ranges import RangeCreate, RangeRead, RangeUpdate
from app.utils.security import require_admin

router = APIRouter(prefix="/api/ranges", tags=["ranges"])


@router.get("", response_model=list[RangeRead], dependencies=[Depends(require_admin)])
async def list_ranges(db: AsyncSession = Depends(get_db)):
    q = await db.execute(select(IPRange).order_by(IPRange.id))
    return q.scalars().all()


@router.post(
    "",
    response_model=RangeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_range(r: RangeCreate, db: AsyncSession = Depends(get_db)):
    new = IPRange(cidr=r.cidr)
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return new


@router.put(
    "/{rid}",
    response_model=RangeRead,
    dependencies=[Depends(require_admin)],
)
async def update_range(
    rid: int, u: RangeUpdate, db: AsyncSession = Depends(get_db)
):
    # 1) apply the update
    stmt = update(IPRange).where(IPRange.id == rid).values(active=u.active)
    res = await db.execute(stmt)
    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Not found")

    # 2) commit
    await db.commit()

    # 3) re-fetch the object
    obj = await db.get(IPRange, rid)
    if not obj:
        # super unlikely, but guard anyway
        raise HTTPException(status_code=404, detail="Not found")
    return obj


@router.delete(
    "/{rid}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_range(rid: int, db: AsyncSession = Depends(get_db)):
    ip_range = await db.get(IPRange, rid)
    if not ip_range:
        raise HTTPException(status_code=404, detail="Not found")

    # 1) delete the object
    await db.delete(ip_range)

    # 2) persist immediately
    await db.commit()
