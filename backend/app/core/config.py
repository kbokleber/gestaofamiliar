from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Gestão Familiar"
    APP_VERSION: str = "dev"
    APP_COMMIT_SHORT: str = "local"
    APP_RELEASE_NAME: Optional[str] = None
    SOURCE_COMMIT: Optional[str] = None
    COMMIT_SHA: Optional[str] = None
    GITHUB_SHA: Optional[str] = None
    
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

    # Keycloak (realm família). Desligado por padrão para não alterar produção
    # até as variáveis serem definidas no ambiente.
    KEYCLOAK_URL: str = ""
    KEYCLOAK_REALM: str = ""
    KEYCLOAK_ISSUER: str = ""
    KEYCLOAK_CLIENT_ID: str = "gestaofamiliar"
    KEYCLOAK_AUDIENCE: str = "gestaofamiliar"
    KEYCLOAK_ADMIN_CLIENT_ID: str = ""
    KEYCLOAK_ADMIN_CLIENT_SECRET: str = ""
    AUTH_KEYCLOAK_ENABLED: bool = False
    AUTH_LEGACY_PASSWORD_ENABLED: bool = True
    KEYCLOAK_ALLOW_SIGNUP: bool = False
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # ----- Telegram / IA (config por família; esta URL é usada para registrar webhook) -----
    BACKEND_PUBLIC_URL: Optional[str] = None  # ex: https://api.seudominio.com (para setWebhook por família)

    # Alertas no navegador dos filhos. As chaves ficam só no ambiente, nunca no git.
    VAPID_PUBLIC_KEY: str = ""
    VAPID_PRIVATE_KEY: str = ""
    VAPID_SUBJECT: str = "mailto:gestaofamiliar@localhost"

    # Busca de endereço dos lugares (OpenStreetMap). Sem chave. Dá para trocar a URL
    # se a família passar a usar outro serviço compatível com a busca do Nominatim.
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"
    NOMINATIM_USER_AGENT: str = "GestaoFamiliar-Localizacao/1.0"
    # Dias que os pontos de localização e os avisos de chegada/saída ficam guardados.
    LOCALIZACAO_RETENCAO_DIAS: int = 90
    # Proxies na frente da API (Traefik + nginx do frontend). Define de onde sai o IP do cliente.
    PROXIES_CONFIAVEIS: int = 2
    # SHA-256 do certificado que assina o app da família (separe vários por vírgula). Vazio = não confere.
    APP_ASSINATURA_SHA256: str = "2ec1e1ef0c72cd1f3d22f0989a0ac159ce0d53a38bed1810ada3fbb03181466a"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

