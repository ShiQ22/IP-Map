# app/routers/live.py

from typing import Any, List, Optional
import ipaddress

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import LiveMonitor, IPRange
from app.schemas.live import LiveMonitorRead
from app.utils.security import require_viewer_or_admin, require_admin
from app.services.scanner import scan_nets

router = APIRouter(prefix="/live",      tags=["live"])


class ScanRequest(BaseModel):
    nets: List[str] = []


@router.get(
    "/",
    response_model=List[LiveMonitorRead],
    dependencies=[Depends(require_viewer_or_admin)],
    summary="List live-monitor entries (optionally filtered by CIDRs)"
)
@router.get("", include_in_schema=False)
async def list_live(
    db: AsyncSession        = Depends(get_db),
    nets: Optional[List[str]] = Query(
        None,
        description="List of CIDR ranges to limit results "
                    "(e.g. ?nets=192.168.6.0/24&nets=10.0.0.0/8)"
    ),
) -> List[LiveMonitorRead]:
    # if the user didn’t pass any nets, load *all* active CIDRs
    if not nets:
        q = await db.execute(select(IPRange).where(IPRange.active == True))
        nets = [r.cidr for r in q.scalars().all()]

    stmt = select(LiveMonitor)
    if nets:
        filters = []
        for cidr in nets:
            net = ipaddress.ip_network(cidr, strict=False)
            prefix = ".".join(str(net.network_address).split(".")[:3]) + "."
            filters.append(LiveMonitor.ip.like(f"{prefix}%"))
        stmt = stmt.where(or_(*filters))

    result = await db.execute(stmt)
    return result.scalars().all()



@router.post(
    "/scan",
    dependencies=[Depends(require_admin)],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a network scan (admin only)"
)
async def trigger_scan(
    req: ScanRequest = Body(...),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Kick off a network scan over the given CIDRs.
    If `req.nets` is empty, scans all active ranges from the database.
    """
    nets = req.nets or []
    if not nets:
        q = await db.execute(select(IPRange).where(IPRange.active == True))
        nets = [r.cidr for r in q.scalars().all()]

    if not nets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CIDR ranges configured for scanning."
        )

    await scan_nets(nets, db)
    return {"detail": "Scan started", "ranges_scanned": nets}
