from typing import Any, List, Optional
from datetime import datetime, timedelta
import ipaddress

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import History, IPRange
from app.schemas.history import HistoryRead, HistoryCreate
from app.utils.security import require_viewer_or_admin, require_admin

router = APIRouter(prefix="/history", tags=["history"])


@router.get(
    "/",
    response_model=List[HistoryRead],
    dependencies=[Depends(require_viewer_or_admin)],
    summary="List scan history, filtered by days/range/ip"
)
async def list_history(
    days: int = Query(14, ge=1, description="Number of days to look back"),
    range: Optional[str] = Query(None, description="CIDR to filter by"),
    ip: Optional[str]    = Query(None, description="Exact IP to filter by"),
    db: AsyncSession      = Depends(get_db),
) -> List[History]:
    """
    GET /api/history?days=14&range=192.168.6.0/24&ip=192.168.6.10
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    stmt = select(History).where(History.scan_time >= cutoff)

    filters = []

    if range:
        net = ipaddress.ip_network(range, strict=False)
        # build prefix like "192.168.6."
        prefix = ".".join(str(net.network_address).split(".")[:3]) + "."
        filters.append(History.ip.like(f"{prefix}%"))

    if ip:
        filters.append(History.ip == ip)

    if filters:
        stmt = stmt.where(and_(*filters))

    result = await db.execute(stmt.order_by(History.scan_time.desc()))
    return result.scalars().all()


@router.post(
    "/",
    response_model=HistoryRead,
    dependencies=[Depends(require_admin)],
    status_code=status.HTTP_201_CREATED,
    summary="(Admin) Create a new history entry"
)
async def create_history(
    payload: HistoryCreate,
    db: AsyncSession = Depends(get_db),
) -> History:
    hist = History(**payload.dict())
    db.add(hist)
    await db.commit()
    await db.refresh(hist)
    return hist


@router.get(
    "/{id}",
    response_model=HistoryRead,
    dependencies=[Depends(require_viewer_or_admin)],
    summary="Read a single history entry by ID"
)
async def read_history(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> History:
    q = await db.execute(select(History).where(History.id == id))
    hist = q.scalars().first()
    if not hist:
        raise HTTPException(status_code=404, detail="History entry not found")
    return hist
