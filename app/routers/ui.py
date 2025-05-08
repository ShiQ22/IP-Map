# app/routers/ui.py
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.utils.security import require_viewer_or_admin
from app.database import get_db
from app.models import IPRange

# resolve the templates directory
TOP = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEMPLATE_DIR = os.path.join(TOP, "app", "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

router = APIRouter()

@router.get("/", include_in_schema=False, name="root")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/login")

@router.get("/login", response_class=HTMLResponse, include_in_schema=False, name="login")
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("login.html", {"request": request})

async def load_active_nets(db: AsyncSession) -> list[str]:
    stmt = select(IPRange.cidr).where(IPRange.active == True).order_by(IPRange.id)
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]

@router.get(
    "/users",
    response_class=HTMLResponse,
    dependencies=[Depends(require_viewer_or_admin)],
    name="users"
)
async def users_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("users.html", {"request": request})

@router.get(
    "/devices",
    response_class=HTMLResponse,
    dependencies=[Depends(require_viewer_or_admin)],
    name="devices"
)
async def devices_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("devices.html", {"request": request})

@router.get(
    "/servers",
    response_class=HTMLResponse,
    dependencies=[Depends(require_viewer_or_admin)],
    name="servers"
)
async def servers_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("servers.html", {"request": request})

@router.get(
    "/history",
    response_class=HTMLResponse,
    dependencies=[Depends(require_viewer_or_admin)],
    name="history"
)
async def history_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    nets = await load_active_nets(db)
    return templates.TemplateResponse("history.html", {"request": request, "nets": nets})

@router.get(
    "/live",
    response_class=HTMLResponse,
    dependencies=[Depends(require_viewer_or_admin)],
    name="live"
)
async def live_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    nets = await load_active_nets(db)
    return templates.TemplateResponse("live.html", {"request": request, "nets": nets})

@router.get(
    "/map",
    response_class=HTMLResponse,
    dependencies=[Depends(require_viewer_or_admin)],
    name="map"
)
async def map_page(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> HTMLResponse:
    nets = await load_active_nets(db)
    return templates.TemplateResponse("ip_map.html", {"request": request, "nets": nets})
