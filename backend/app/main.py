from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.api import api_router

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

# Adicionar logging de requisições
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"📥 {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"📤 {request.method} {request.url} - Status: {response.status_code}")
    return response

# Incluir rotas da API
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": "Sistema Familiar API",
        "version": "1.0.0",
        "docs": f"{settings.API_V1_STR}/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

