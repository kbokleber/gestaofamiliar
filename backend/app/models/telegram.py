"""
Vínculo do usuário com Telegram e preferência de IA.
Configuração do bot e da IA é por família; cada usuário vincula sua conta Telegram e escolhe usar IA ou não.

Tabelas no banco:
- family_telegram_config: token do bot e username por família (uma linha por família).
- family_ai_config: IA por família (enabled, provider, openai_*, azure_*, uma linha por família).
- telegram_user_link: vínculo user_id <-> telegram_user_id/chat_id e preferência use_ai.
- telegram_link_code: códigos de uso único para vincular conta Telegram (expiram).
"""
from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class FamilyTelegramConfig(Base):
    """Token do bot Telegram por família (cada família cria seu bot no @BotFather e cola o token aqui)."""
    __tablename__ = "family_telegram_config"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, unique=True, index=True)
    bot_token = Column(String(200), nullable=False)  # Token do BotFather
    webhook_secret = Column(String(100), nullable=True)  # Opcional para validar webhook
    bot_username = Column(String(100), nullable=True)  # Cache do @username do bot (getMe)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    family = relationship("Family", back_populates="telegram_config", uselist=False)


class FamilyAIConfig(Base):
    """Configuração de IA por família (OpenAI ou Azure; cada família cola sua API key)."""
    __tablename__ = "family_ai_config"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, default=True, nullable=False)
    provider = Column(String(20), nullable=False, default="openai")  # openai | azure | none
    # OpenAI
    openai_api_key = Column(Text, nullable=True)
    openai_model = Column(String(80), nullable=False, default="gpt-4o-mini")
    # Azure OpenAI
    azure_endpoint = Column(String(500), nullable=True)
    azure_api_key = Column(Text, nullable=True)
    azure_deployment = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    family = relationship("Family", back_populates="ai_config", uselist=False)


class TelegramUserLink(Base):
    """Vínculo entre usuário do sistema e conta Telegram."""
    __tablename__ = "telegram_user_link"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, unique=True, index=True)
    telegram_user_id = Column(BigInteger, nullable=False, unique=True, index=True)
    telegram_chat_id = Column(BigInteger, nullable=False, index=True)
    telegram_username = Column(String(100), nullable=True)
    use_ai = Column(Boolean, default=True, nullable=False)  # Preferência: usar IA nas mensagens
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="telegram_link")


class TelegramLinkCode(Base):
    """Código único de uso único para vincular Telegram ao usuário (expira em alguns minutos)."""
    __tablename__ = "telegram_link_code"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
