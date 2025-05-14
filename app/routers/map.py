# app/routers/map.py

import os
from ipaddress import ip_network

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import IPRange, IP, History, User, Device, Server
from app.utils.security import require_viewer_or_admin

# locate your templates folder just like in ui.py
TOP = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEMPLATE_DIR = os.path.join(TOP, "app", "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

router = APIRouter(tags=["map"])


@router.get(
    "/map",
    response_class=HTMLResponse,
    dependencies=[Depends(require_viewer_or_admin)],
)
async def view_map(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Render the IP Map page, injecting `nets` as a list of active CIDR strings.
    """
    result = await db.execute(
        select(IPRange.cidr).where(IPRange.active.is_(True)).order_by(IPRange.id)
    )
    cidrs = result.scalars().all()

    return templates.TemplateResponse(
        "ip_map.html",
        {"request": request, "nets": cidrs},
    )


@router.get(
    "/api/ip_map",
    dependencies=[Depends(require_viewer_or_admin)],
)
async def get_ip_map(
    range: str = Query(..., description="CIDR block, e.g. 192.168.6.0/24"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return JSON array of every host IP in the given CIDR:
      - `short`: e.g. "6.16"
      - `taken`: true if assigned in `ips` table
      - `kind` & `name` for tooltip
    """
    # 1) verify this CIDR exists and is active
    rng_q = await db.execute(
        select(IPRange).where(IPRange.cidr == range, IPRange.active.is_(True))
    )
    rng = rng_q.scalars().first()
    if not rng:
        raise HTTPException(status_code=404, detail="Range not found")

    # 2) parse the network
    try:
        network = ip_network(range)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid CIDR format")

    # 3) fetch all assigned IPs in this block
    prefix = ".".join(str(network.network_address).split(".")[:3])
    assigned_q = await db.execute(
        select(IP).where(IP.ip_address.like(f"{prefix}.%"))
    )
    assigned = {ip.ip_address: ip for ip in assigned_q.scalars().all()}

    # 4) fetch active-on-network IPs from history (status == "up")
    hist_q = await db.execute(select(History).order_by(History.scan_time.desc()))
    active = {
        h.ip
        for h in hist_q.scalars().all()
        if getattr(h, "status", "").lower() == "up"
    }

    # 5) build the response
    data: list[dict] = []
    for addr in network.hosts():
        ip_str = str(addr)
        parts = ip_str.split(".")
        short = f"{parts[2]}.{parts[3]}"

        # default values
        taken = False
        kind = ""
        name = ""

        if ip_str in assigned:
            ent = assigned[ip_str]
            kind = ent.owner_type.name.title()

            # lookup the real owner name
            if kind == "User":
                usr = await db.get(User, ent.owner_id)
                name = usr.username or getattr(usr, "full_name", None) or f"User {ent.owner_id}"
            elif kind == "Device":
                dev = await db.get(Device, ent.owner_id)
                name = dev.hostname or f"Device {ent.owner_id}"
            elif kind == "Server":
                srv = await db.get(Server, ent.owner_id)
                name = srv.server_name or f"Server {ent.owner_id}"
            else:
                name = f"{kind} {ent.owner_id}"

            taken = True

        elif ip_str in active:
            kind = "Network"
            name = ""
            taken = False

        data.append({
            "ip":    ip_str,
            "short": short,
            "taken": taken,
            "kind":  kind,
            "name":  name,
        })

    return JSONResponse(content=data)
