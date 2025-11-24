from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.user import User
from app.models.dashboard import DashboardPreference
from app.schemas.dashboard import (
    DashboardPreference as DashboardPreferenceSchema,
    DashboardPreferenceCreate,
    DashboardPreferenceUpdate
)
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/preferences", response_model=DashboardPreferenceSchema)
async def get_dashboard_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter preferências do dashboard"""
    preference = db.query(DashboardPreference).filter(
        DashboardPreference.user_id == current_user.id
    ).first()
    
    if not preference:
        # Criar preferências padrão
        preference = DashboardPreference(user_id=current_user.id)
        db.add(preference)
        db.commit()
        db.refresh(preference)
    
    return preference

@router.put("/preferences", response_model=DashboardPreferenceSchema)
async def update_dashboard_preferences(
    preference_data: DashboardPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualizar preferências do dashboard"""
    preference = db.query(DashboardPreference).filter(
        DashboardPreference.user_id == current_user.id
    ).first()
    
    if not preference:
        preference = DashboardPreference(user_id=current_user.id)
        db.add(preference)
    
    # Atualizar campos
    for field, value in preference_data.dict(exclude_unset=True).items():
        setattr(preference, field, value)
    
    db.commit()
    db.refresh(preference)
    return preference

