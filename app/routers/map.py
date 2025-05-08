# app/routers/map.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.utils.security import require_viewer_or_admin

templates = Jinja2Templates(directory="templates")
router = APIRouter(prefix="/map", tags=["map"])

# Handle GET /map  (no slash) *and* GET /map/ (with slash)
@router.get("", response_class=HTMLResponse, dependencies=[Depends(require_viewer_or_admin)])
@router.get("/", response_class=HTMLResponse, dependencies=[Depends(require_viewer_or_admin)])
async def view_map(request: Request):
    return templates.TemplateResponse("ip_map.html", {"request": request})
