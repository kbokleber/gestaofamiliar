from fastapi import APIRouter

from app.core.version import get_app_version_info

router = APIRouter()


@router.get("/version")
async def get_system_version():
    return get_app_version_info()
