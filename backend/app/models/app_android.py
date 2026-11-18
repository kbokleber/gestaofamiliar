"""APK do app Android da criança, enviado por um admin pelo site e baixado em /app."""
from sqlalchemy import Column, DateTime, ForeignKey, Integer, LargeBinary, String
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
