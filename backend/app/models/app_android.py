"""APK do app Android da criança, enviado por um admin pelo site e baixado em /app."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.sql import func

from app.db.base import Base


class AppAndroid(Base):
    __tablename__ = "app_android"

    id = Column(Integer, primary_key=True, index=True)
    versao = Column(String(30), nullable=False)
    tamanho_bytes = Column(Integer, nullable=False)
    sha256 = Column(String(64), nullable=False)
    conteudo = Column(LargeBinary, nullable=False)
    enviado_por_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AppPublicacaoToken(Base):
    """Token que só serve para publicar versões do app. Gerado por um admin no site; aqui fica só o hash."""

    __tablename__ = "app_publicacao_token"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    criado_por_id = Column(Integer, ForeignKey("auth_user.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revogado_em = Column(DateTime(timezone=True), nullable=True)


class AppDispositivoAdulto(Base):
    """Celular de um adulto com o app: não envia localização, só busca avisos (alertas) para notificar."""

    __tablename__ = "app_dispositivo_adulto"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    label = Column(String(80), nullable=False, default="")
    app_versao = Column(Integer, nullable=True)
    notificacoes_ativas = Column(Boolean, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
