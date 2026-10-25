from fastapi import APIRouter, Depends
from app.api.deps import require_menu
from app.api.v1.endpoints import auth, users, healthcare, maintenance, dashboard, families, telegram, finance, system

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(families.router, prefix="/families", tags=["families"])
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(require_menu("dashboard"))],
)
api_router.include_router(
    healthcare.router,
    prefix="/healthcare",
    tags=["healthcare"],
    dependencies=[Depends(require_menu("saude"))],
)
api_router.include_router(
    maintenance.router,
    prefix="/maintenance",
    tags=["maintenance"],
    dependencies=[Depends(require_menu("manutencao"))],
)
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
api_router.include_router(
    finance.router,
    prefix="/finance",
    tags=["finance"],
    dependencies=[Depends(require_menu("financas"))],
)
api_router.include_router(system.router, prefix="/system", tags=["system"])
