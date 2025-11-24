from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, healthcare, maintenance, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(healthcare.router, prefix="/healthcare", tags=["healthcare"])
api_router.include_router(maintenance.router, prefix="/maintenance", tags=["maintenance"])
