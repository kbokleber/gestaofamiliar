from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.user_family import user_families

class User(Base):
    """
    Tabela auth_user do Django
    Modelo de usuário padrão do Django
    """
    __tablename__ = "auth_user"
    
    id = Column(Integer, primary_key=True, index=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    is_superuser = Column(Boolean, default=False, nullable=False)
    username = Column(String(150), unique=True, index=True, nullable=False)
    first_name = Column(String(150), nullable=False, default='')
    last_name = Column(String(150), nullable=False, default='')
    email = Column(String(254), nullable=False, default='')
    is_staff = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    date_joined = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    family_id = Column(Integer, ForeignKey("families.id"), nullable=True, index=True)  # Mantido para compatibilidade (família principal para staff)
    
    # Relacionamentos
    family = relationship("Family", back_populates="users", foreign_keys=[family_id])  # Família principal (para staff)
    families = relationship("Family", secondary=user_families, back_populates="users_many")  # Múltiplas famílias (para admins)
    profile = relationship("Profile", back_populates="user", uselist=False)
    dashboard_preference = relationship("DashboardPreference", back_populates="user", uselist=False)
    equipments_owned = relationship("Equipment", back_populates="owner")
    maintenance_orders = relationship("MaintenanceOrder", back_populates="created_by")
    uploaded_attachments = relationship("EquipmentAttachment", back_populates="uploaded_by")
    telegram_link = relationship("TelegramUserLink", back_populates="user", uselist=False, cascade="all, delete-orphan")

class Profile(Base):
    """
    Perfil estendido do usuário
    App: accounts
    """
    __tablename__ = "accounts_profile"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, unique=True)
    phone = Column(String(20), nullable=False, default='')
    address = Column(String(200), nullable=False, default='')
    city = Column(String(100), nullable=False, default='')
    state = Column(String(50), nullable=False, default='')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamento
    user = relationship("User", back_populates="profile")
