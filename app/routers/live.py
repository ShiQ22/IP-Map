# app/routers/live.py

from typing import Any, List

from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import LiveMonitor, IPRange
from app.schemas.live import LiveMonitorRead
from app.utils.security import require_viewer_or_admin, require_admin
from app.services.scanner import scan_nets

router = APIRouter(prefix="/live", tags=["live"])


@router.get(
    "/",
    response_model=List[LiveMonitorRead],
    dependencies=[Depends(require_viewer_or_admin)],
    summary="List current live-monitor entries",
)
async def list_live(db: AsyncSession = Depends(get_db)) -> List[LiveMonitor]:
    """GET /live/ → return all rows from live_monitor."""
    result = await db.execute(select(LiveMonitor))
    return result.scalars().all()


@router.post(
    "/scan",
    dependencies=[Depends(require_admin)],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a network scan (admin only)",
    responses={202: {"description": "Scan started"}},
)
async def trigger_scan(
    nets: List[str] = Body(
        default=[],
        description="CIDR ranges to scan; if empty, all active ranges from the database are used"
    ),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    POST /live/scan
    Kick off a network scan over the given CIDRs.
    Only admins may call this.  If `nets` is empty, fetch all active
    ranges from the `ip_ranges` table.
    """

    # 1) If the client passed none, load active ranges from DB
    if not nets:
        q = await db.execute(select(IPRange).where(IPRange.active == True))
        nets = [r.cidr for r in q.scalars().all()]

    if not nets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No CIDR ranges configured for scanning."
        )

    # 2) Invoke your scanner (could be long-running; consider background tasks)
    await scan_nets(nets, db)

    return {"detail": "Scan started", "ranges_scanned": nets}
