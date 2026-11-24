from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.monitoramento import iniciar_monitoramento
from app.core.version import get_app_version_info

# Antes de criar o app, para pegar também os erros da inicialização. Sem DSN, não faz nada.
iniciar_monitoramento(
    settings.GF_SENTRY_DSN_BACKEND, settings.GF_SENTRY_ENVIRONMENT, get_app_version_info()["commit"],
)

from app.api.v1.api import api_router
from app.db.base import Base, engine

# Registrar todos os modelos para create_all criar as tabelas (inclui family_telegram_config, family_ai_config)
from app.models import *  # noqa: F401, F403

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
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
async def startup_lembretes():
    import asyncio
    from app.api.v1.endpoints.notificacoes import ciclo_de_lembretes
    asyncio.create_task(ciclo_de_lembretes())


@app.on_event("startup")
def startup_create_tables():
    """Cria tabelas que não existem (ex.: family_telegram_config, family_ai_config)."""
    try:
        Base.metadata.create_all(bind=engine)
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE auth_user ADD COLUMN IF NOT EXISTS allowed_menus JSON"
            ))
            conn.execute(text(
                "ALTER TABLE healthcare_familymember ADD COLUMN IF NOT EXISTS documents TEXT"
            ))
            conn.execute(text(
                "ALTER TABLE auth_user ADD COLUMN IF NOT EXISTS is_child BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pendente'"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ADD COLUMN IF NOT EXISTS concluida_em TIMESTAMPTZ"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ADD COLUMN IF NOT EXISTS anexos TEXT"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ADD COLUMN IF NOT EXISTS anexos_resumo TEXT"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ADD COLUMN IF NOT EXISTS tipo VARCHAR(20) NOT NULL DEFAULT 'atividade'"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ADD COLUMN IF NOT EXISTS autor VARCHAR(150)"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ADD COLUMN IF NOT EXISTS numero VARCHAR(40)"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ALTER COLUMN prazo_entrega DROP NOT NULL"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ALTER COLUMN disciplina DROP NOT NULL"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ALTER COLUMN status DROP NOT NULL"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_atividade ADD COLUMN IF NOT EXISTS "
                "criado_pelo_app BOOLEAN NOT NULL DEFAULT FALSE"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_avaliacao ADD COLUMN IF NOT EXISTS "
                "tipo_codigo_eclass VARCHAR(20)"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_avaliacao ADD COLUMN IF NOT EXISTS "
                "nota_alcancada NUMERIC(5, 2)"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_avaliacao ADD COLUMN IF NOT EXISTS "
                "professor VARCHAR(150)"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_avaliacao ADD COLUMN IF NOT EXISTS "
                "composicao JSON"
            ))
            conn.execute(text(
                "ALTER TABLE estudo_avaliacao ADD COLUMN IF NOT EXISTS "
                "fonte VARCHAR(20) NOT NULL DEFAULT 'pdf'"
            ))
            # App da criança: versão instalada e se as notificações estão liberadas.
            conn.execute(text(
                "ALTER TABLE location_device ADD COLUMN IF NOT EXISTS app_versao INTEGER"
            ))
            conn.execute(text(
                "ALTER TABLE location_device ADD COLUMN IF NOT EXISTS notificacoes_ativas BOOLEAN"
            ))
            conn.execute(text(
                "ALTER TABLE location_device ADD COLUMN IF NOT EXISTS alerta_sem_sinal_em TIMESTAMP WITH TIME ZONE"
            ))
            # Checklist de envio (app 2.0.7+).
            conn.execute(text(
                "ALTER TABLE location_device ADD COLUMN IF NOT EXISTS checklist TEXT"
            ))
            conn.execute(text(
                "ALTER TABLE location_device ADD COLUMN IF NOT EXISTS checklist_em TIMESTAMP WITH TIME ZONE"
            ))
            # Foto no mapa: qual membro da família (Saúde) é esta pessoa.
            conn.execute(text(
                "ALTER TABLE location_child_settings ADD COLUMN IF NOT EXISTS family_member_id INTEGER "
                "REFERENCES healthcare_familymember(id) ON DELETE SET NULL"
            ))
        from app.db.base import SessionLocal
        from app.api.v1.endpoints.maintenance import sincronizar_equipamentos_com_ordens_abertas
        db = SessionLocal()
        try:
            sincronizar_equipamentos_com_ordens_abertas(db)
            db.commit()
        finally:
            db.close()
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
    version_info = get_app_version_info()
    return {
        "message": "Gestão Familiar API",
        "version": version_info["version"],
        "commit": version_info["commit"],
        "releaseName": version_info["releaseName"],
        "docs": f"{settings.API_V1_STR}/docs"
    }

@app.get("/health")
async def health_check():
    version_info = get_app_version_info()
    return {
        "status": "healthy",
        "version": version_info["version"],
        "commit": version_info["commit"],
        "releaseName": version_info["releaseName"],
    }

