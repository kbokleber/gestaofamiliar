from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base

class DashboardPreference(Base):
    """
    Preferências do Dashboard do usuário
    App: dashboard
    """
    __tablename__ = "dashboard_dashboardpreference"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False, unique=True)
    show_pending_maintenance = Column(Boolean, default=True, nullable=False)
    show_equipment_stats = Column(Boolean, default=True, nullable=False)
    show_cost_analysis = Column(Boolean, default=True, nullable=False)
    show_upcoming_maintenance = Column(Boolean, default=True, nullable=False)
    days_to_alert = Column(Integer, default=7, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relacionamento
    user = relationship("User", back_populates="dashboard_preference")

