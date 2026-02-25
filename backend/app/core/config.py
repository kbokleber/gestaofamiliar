from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Gestão Familiar"
    
    # Database
    DATABASE_URL: str
    
    # Database Pool Settings (opcional - valores padrão otimizados)
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 3600  # 1 hora
    
    # Debug SQL (desabilitado por padrão para performance)
    SQL_DEBUG: bool = False
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # ----- Telegram / IA (config por família; esta URL é usada para registrar webhook) -----
    BACKEND_PUBLIC_URL: Optional[str] = None  # ex: https://api.seudominio.com (para setWebhook por família)
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

