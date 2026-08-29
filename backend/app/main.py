import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    action_log,
    auth,
    dashboard,
    integrations,
    media,
    notifications,
    orphaned_files,
    pending_deletions,
    profile,
    rules,
    runs,
    settings as settings_routes,
    version,
)
from app.bootstrap import ensure_app_settings
from app.core.config import get_settings
from app.core.scheduler import start_scheduler
from app.db.base import async_session_factory

logging.basicConfig(level=get_settings().log_level)

# Requests that mutate state must carry this header. Combined with the
# session cookie's SameSite=Strict, this is a cheap second layer against
# CSRF for a same-origin single-page app (no separate CORS setup needed).
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
_CSRF_HEADER = "x-requested-with"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session_factory() as db:
        await ensure_app_settings(db)
    scheduler = await start_scheduler()
    app.state.scheduler = scheduler
    yield
    scheduler.shutdown()


app = FastAPI(title="Evictarr", lifespan=lifespan)


@app.middleware("http")
async def require_csrf_header(request: Request, call_next):
    if request.method not in _SAFE_METHODS and request.url.path.startswith("/api/"):
        if _CSRF_HEADER not in request.headers:
            return JSONResponse({"detail": "Missing required header"}, status_code=400)
    return await call_next(request)


app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(integrations.router)
app.include_router(rules.router)
app.include_router(runs.router)
app.include_router(pending_deletions.router)
app.include_router(settings_routes.router)
app.include_router(notifications.router)
app.include_router(action_log.router)
app.include_router(orphaned_files.router)
app.include_router(dashboard.router)
app.include_router(media.router)
app.include_router(version.router)

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa_catch_all(full_path: str):
        # Files copied verbatim from frontend/public (favicon, logo, etc.) live
        # at the dist root alongside index.html - serve them directly instead
        # of falling through to the SPA shell. Anything else (client-side
        # routes like /rules) falls back to index.html.
        candidate = (FRONTEND_DIST / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(FRONTEND_DIST):
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
