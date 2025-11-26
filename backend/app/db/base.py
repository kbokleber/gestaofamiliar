from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Configuração otimizada do pool de conexões para produção
# pool_size: número de conexões mantidas no pool
# max_overflow: conexões adicionais que podem ser criadas além do pool_size
# pool_pre_ping: verifica se a conexão está viva antes de usar (importante para conexões de longa duração)
# pool_recycle: recicla conexões após X segundos (evita conexões antigas)
# echo: desabilitado em produção para melhor performance
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,              # configurável via env
    max_overflow=settings.DB_MAX_OVERFLOW,         # configurável via env
    pool_pre_ping=True,                           # verifica conexão antes de usar
    pool_recycle=settings.DB_POOL_RECYCLE,        # configurável via env
    echo=settings.ENVIRONMENT == "development"     # logs SQL apenas em desenvolvimento
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """Dependency para obter sessão do banco"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

