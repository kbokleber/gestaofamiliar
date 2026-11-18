"""Lembrete sonoro das atividades no celular do filho."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class FamilyLembreteConfig(Base):
    """De quanto em quanto tempo o celular do filho recebe o alerta."""

    __tablename__ = "family_lembrete_config"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=False)
    intervalo = Column(Integer, nullable=False, default=2)
    unidade = Column(String(10), nullable=False, default="horas")
    ultimo_envio = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    family = relationship("Family", back_populates="lembrete_config", uselist=False)


class PushInscricao(Base):
    """Inscrição de notificação do navegador de um usuário."""

    __tablename__ = "push_inscricao"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")


class AvisoApp(Base):
    """Aviso esperando o app Android da criança buscar, junto com o envio da localização."""

    __tablename__ = "app_aviso"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    child_user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False, default="lembrete")
    titulo = Column(String(120), nullable=False)
    texto = Column(String(500), nullable=False)
    url = Column(String(300), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expira_em = Column(DateTime(timezone=True), nullable=False)
    entregue_em = Column(DateTime(timezone=True), nullable=True)
