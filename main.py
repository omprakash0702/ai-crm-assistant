import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router
from app.auth.router import router as auth_router
from app.core.auth import APIKeyMiddleware
from app.core.logging_config import setup_logging, RequestLoggingMiddleware

setup_logging()

app = FastAPI()

# Middleware execution order (last-added runs first):
#   APIKeyMiddleware → RequestLoggingMiddleware → CORSMiddleware → route
# RequestLoggingMiddleware is intentionally inner to APIKeyMiddleware so that
# request.state.user is already populated when the log entry is written.
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(APIKeyMiddleware)

app.include_router(auth_router)
app.include_router(router)

# Serve React frontend — must come after API routers so API routes take priority
_DIST = Path("frontend/dist")
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(_DIST / "index.html")
