from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class Family(Base):
    """
    Família - Multi-tenancy
    Cada família é um tenant isolado no sistema
    """
    __tablename__ = "families"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    codigo_unico = Column(String(50), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relacionamentos
    users = relationship("User", back_populates="family", foreign_keys="[User.family_id]")  # Relação 1:N (família principal)
    users_many = relationship("User", secondary="user_families", back_populates="families")  # Relação N:N (múltiplas famílias)
    family_members = relationship("FamilyMember", back_populates="family", cascade="all, delete-orphan")
    equipment = relationship("Equipment", back_populates="family", cascade="all, delete-orphan")
    telegram_config = relationship("FamilyTelegramConfig", back_populates="family", uselist=False, cascade="all, delete-orphan")
    ai_config = relationship("FamilyAIConfig", back_populates="family", uselist=False, cascade="all, delete-orphan")

