from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.api.v1.api import api_router
from app.db.base import Base, engine

# Registrar todos os modelos para create_all criar as tabelas (inclui family_telegram_config, family_ai_config)
from app.models import *  # noqa: F401, F403

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configurar CORS de forma simples
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todas as origens
    allow_credentials=False,  # Desabilitar credentials temporariamente
    allow_methods=["*"],
    allow_headers=["*"],
)

# Adicionar logging de requisições - com arquivo para debug
import logging
import sys

# Configurar logging para console E arquivo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app_debug.log', mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"[REQUEST] {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"[RESPONSE] {request.method} {request.url} - Status: {response.status_code}")
    return response

# Incluir rotas da API
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
def startup_create_tables():
    """Cria tabelas que não existem (ex.: family_telegram_config, family_ai_config)."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tabelas do banco verificadas/criadas.")
    except Exception as e:
        logger.exception("Erro ao criar tabelas: %s", e)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Loga o traceback completo e devolve 500 com detalhe em desenvolvimento."""
    logger.exception("Erro não tratado: %s", exc)
    is_dev = getattr(settings, "ENVIRONMENT", "") == "development"
    detail = str(exc) if is_dev else "Erro interno do servidor."
    return JSONResponse(
        status_code=500,
        content={"detail": detail, "type": type(exc).__name__},
    )


@app.get("/")
async def root():
    return {
        "message": "Gestão Familiar API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

