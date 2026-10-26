"""Aviso de atividade concluída no WhatsApp da família."""
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class FamilyWhatsAppConfig(Base):
    """URL e grupo ou número para avisar quando um filho conclui uma atividade."""

    __tablename__ = "family_whatsapp_config"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=False, unique=True, index=True)
    enabled = Column(Boolean, nullable=False, default=False)
    url = Column(Text, nullable=False, default="")
    destino = Column(String(120), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    family = relationship("Family", back_populates="whatsapp_config", uselist=False)
