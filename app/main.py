# app/main.py

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings
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
    # (so URLs like /css/naos.png, /css/background.png, /css/naos.ico)
    app.mount(
        "/css",
        StaticFiles(directory="app/CSS"),
        name="css",
    )

    # 1) UI router for HTML pages (/login, /map-ui, etc.)
    app.include_router(ui.router)

    # 2) JSON/API routers
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(devices.router)
    app.include_router(servers.router)
    app.include_router(ips.router)
    app.include_router(live.router)
    app.include_router(history.router)
    app.include_router(ip_map.router)
    app.include_router(ranges.router)

    return app

app = create_app()
