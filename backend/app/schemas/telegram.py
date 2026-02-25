from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ----- Configuração da família (bot + IA) -----


class FamilyBotConfigResponse(BaseModel):
    """Estado da config do bot Telegram da família (token nunca é retornado)."""
    configured: bool
    bot_username: Optional[str] = None


class FamilyBotConfigUpdate(BaseModel):
    """Atualizar token do bot da família (criar no @BotFather e colar aqui)."""
    bot_token: str = Field(..., min_length=1)


class FamilyAIConfigResponse(BaseModel):
    """Estado da config de IA da família (chaves nunca retornadas)."""
    enabled: bool = True
    provider: str = "openai"  # openai | azure | none
    openai_model: Optional[str] = None
    has_openai_key: bool = False
    has_azure_config: bool = False


class FamilyAIConfigUpdate(BaseModel):
    """Atualizar config de IA da família."""
    enabled: Optional[bool] = None
    provider: Optional[str] = Field(None, pattern="^(openai|azure|none)$")
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    azure_endpoint: Optional[str] = None
    azure_api_key: Optional[str] = None
    azure_deployment: Optional[str] = None


# ----- Vínculo do usuário com Telegram -----


class TelegramMeResponse(BaseModel):
    """Status do vínculo Telegram do usuário e preferência de IA."""
    linked: bool
    telegram_username: Optional[str] = None
    use_ai: bool = True
    ai_available: bool = False  # Se a IA está configurada no servidor (OPENAI_* ou AZURE_*)


class TelegramLinkCodeResponse(BaseModel):
    """Código gerado para vincular Telegram."""
    code: str
    expires_at: datetime
    bot_username: Optional[str] = None  # Nome do bot para exibir (ex: @MeuBot)


class TelegramUpdatePreferences(BaseModel):
    """Atualizar preferência de uso de IA no Telegram."""
    use_ai: bool
