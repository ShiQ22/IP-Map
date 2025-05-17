# app/main.py


from pydantic.json import ENCODERS_BY_TYPE
from datetime import datetime, timezone
# -- ensure all datetimes are emitted as UTC ISO strings with offset --
ENCODERS_BY_TYPE[datetime] = lambda dt: dt.astimezone(timezone.utc).isoformat()
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.routers.admins import router as admins_router
from app.routers.health import router as health_router
from app.routers import (
    ui,      # HTML UI routes
    auth,    # JSON/auth endpoints
    users,
    devices,
    servers,
    ips,
    live,
    history,
    map as ip_map,
    ranges,
)

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    # Serve your CSS/images folder at /css
    app.mount(
        "/css",
        StaticFiles(directory="app/CSS"),
        name="css",
    )

    # 1) UI router for HTML pages (/login, /map-ui, etc.)
    app.include_router(ui.router)

    # 2) JSON/API routers
    app.include_router(auth.router)
    app.include_router(users.router, prefix="/api", tags=["users"])
    app.include_router(devices.router, prefix="/api", tags=["devices"])
    app.include_router(servers.router, prefix="/api")
    app.include_router(ips.router, prefix="/api", tags=["ips"])
    app.include_router(history.router, prefix="/api", tags=["history"])
    app.include_router(ip_map.router)
    app.include_router(ranges.router)
    app.include_router(admins_router)
    app.include_router(health_router)
    app.include_router(live.router, prefix="/api", tags=["live"])


    # Global exception handler to redirect unauthorized HTML requests to /login
    @app.exception_handler(StarletteHTTPException)
    async def auth_redirect_handler(request: Request, exc: StarletteHTTPException):
        # Redirect browser-based (HTML) 401/403 to login page
        if exc.status_code in (401, 403):
            accept = request.headers.get("accept", "")
            if "text/html" in accept:
                return RedirectResponse(url="/login")
        # Otherwise return JSON error
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    return app

app = create_app()
