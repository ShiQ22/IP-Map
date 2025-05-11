# app/routers/ui.py
import os
from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.utils.security import require_viewer_or_admin, require_admin
from app.database import get_db
from app.models import IPRange, Admin

# resolve the templates directory
TOP = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
TEMPLATE_DIR = os.path.join(TOP, "app", "templates")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

router = APIRouter()

@router.get("/", include_in_schema=False, name="root")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/login")

@router.get(
    "/login",
    response_class=HTMLResponse,
    include_in_schema=False,
    name="login"
)
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("login.html", {"request": request})

@router.get(
    "/logout",
    include_in_schema=False,
    name="logout"
)
async def logout_page() -> RedirectResponse:
    response = RedirectResponse(url="/login")
    response.delete_cookie(key="access_token")
    return response

async def load_active_nets(db: AsyncSession) -> list[str]:
    stmt = select(IPRange.cidr).where(IPRange.active == True).order_by(IPRange.id)
    result = await db.execute(stmt)
    return [row[0] for row in result.all()]

@router.get(
    "/users",
    response_class=HTMLResponse,
    name="users"
)
async def users_page(
    request: Request,
    current_user=Depends(require_viewer_or_admin),
) -> HTMLResponse:
    return templates.TemplateResponse("users.html", {
        "request": request,
        "current_user": current_user
    })

@router.get(
    "/devices",
    response_class=HTMLResponse,
    name="devices"
)
async def devices_page(
    request: Request,
    current_user=Depends(require_viewer_or_admin),
) -> HTMLResponse:
    return templates.TemplateResponse("devices.html", {
        "request": request,
        "current_user": current_user
    })

@router.get(
    "/servers",
    response_class=HTMLResponse,
    name="servers"
)
async def servers_page(
    request: Request,
    current_user=Depends(require_viewer_or_admin),
) -> HTMLResponse:
    return templates.TemplateResponse("servers.html", {
        "request": request,
        "current_user": current_user
    })

@router.get(
    "/history",
    response_class=HTMLResponse,
    name="history"
)
async def history_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_viewer_or_admin),
) -> HTMLResponse:
    nets = await load_active_nets(db)
    return templates.TemplateResponse("history.html", {
        "request": request,
        "nets": nets,
        "current_user": current_user
    })

@router.get(
    "/live",
    response_class=HTMLResponse,
    name="live"
)
async def live_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_viewer_or_admin),
) -> HTMLResponse:
    nets = await load_active_nets(db)
    return templates.TemplateResponse("live.html", {
        "request": request,
        "nets": nets,
        "current_user": current_user
    })

@router.get(
    "/map",
    response_class=HTMLResponse,
    name="map"
)
async def map_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_viewer_or_admin),
) -> HTMLResponse:
    nets = await load_active_nets(db)
    return templates.TemplateResponse("ip_map.html", {
        "request": request,
        "nets": nets,
        "current_user": current_user
    })

@router.get(
    "/admin",
    response_class=HTMLResponse,
    name="admin"
)
async def admin_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_admin),
) -> HTMLResponse:
    ranges = (await db.execute(select(IPRange))).scalars().all()
    admins = (await db.execute(select(Admin))).scalars().all()
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "ranges": ranges,
        "admins": admins,
        "current_user": current_user
    })
