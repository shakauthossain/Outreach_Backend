"""API version 1 package."""

from fastapi import APIRouter

from .endpoints import auth, leads, health, speedtest, punchlines, emails, tasks

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(speedtest.router, prefix="/speedtest", tags=["speedtest"])
api_router.include_router(punchlines.router, prefix="/punchlines", tags=["punchlines"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(tasks.router, prefix="/task-status", tags=["tasks"])
