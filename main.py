import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
