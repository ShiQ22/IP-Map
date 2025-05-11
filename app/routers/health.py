# app/routers/health.py

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from app.utils.security import require_viewer_or_admin

router = APIRouter(tags=["debug"])

@router.get("/api/me")
async def read_current_user(current_user=Depends(require_viewer_or_admin)):
    """
    Debug endpoint: returns the username of the authenticated user.
    """
    return JSONResponse({"username": current_user.username})
