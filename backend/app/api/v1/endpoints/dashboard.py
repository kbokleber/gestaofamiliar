from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
from app.db.base import get_db
from app.models.user import User
from app.models.dashboard import DashboardPreference
from app.models.healthcare import FamilyMember, MedicalAppointment, Medication
from app.models.maintenance import Equipment, MaintenanceOrder
from app.schemas.dashboard import (
    DashboardPreference as DashboardPreferenceSchema,
    DashboardPreferenceCreate,
    DashboardPreferenceUpdate
)
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter estatísticas do dashboard em uma única requisição"""
    family_id = current_user.family_id
    now = datetime.now(timezone.utc)
    
    # Contar membros da família
    total_members = db.query(func.count(FamilyMember.id)).filter(
        FamilyMember.family_id == family_id
    ).scalar() or 0
    
    # Contar consultas futuras (via family_member)
    total_appointments = db.query(func.count(MedicalAppointment.id)).join(
        FamilyMember, MedicalAppointment.family_member_id == FamilyMember.id
    ).filter(
        FamilyMember.family_id == family_id,
        MedicalAppointment.appointment_date >= now
    ).scalar() or 0
    
    # Contar equipamentos
    total_equipment = db.query(func.count(Equipment.id)).filter(
        Equipment.family_id == family_id
    ).scalar() or 0
    
    # Contar medicações ativas (sem end_date ou com end_date no futuro)
    active_medications = db.query(func.count(Medication.id)).join(
        FamilyMember, Medication.family_member_id == FamilyMember.id
    ).filter(
        FamilyMember.family_id == family_id,
        (Medication.end_date == None) | (Medication.end_date >= now.date())
    ).scalar() or 0
    
    # Contar ordens de manutenção
    total_orders = db.query(func.count(MaintenanceOrder.id)).join(
        Equipment, MaintenanceOrder.equipment_id == Equipment.id
    ).filter(
        Equipment.family_id == family_id
    ).scalar() or 0
    
    return {
        "total_members": total_members,
        "total_appointments": total_appointments,
        "total_equipment": total_equipment,
        "active_medications": active_medications,
        "total_orders": total_orders
    }

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

