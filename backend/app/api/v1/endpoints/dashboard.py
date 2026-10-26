from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_
from app.db.base import get_db
from app.models.user import User
from app.models.dashboard import DashboardPreference
from app.models.estudo import Atividade
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
    
    # No painel, equipamentos são só os operacionais
    total_equipment = db.query(func.count(Equipment.id)).filter(
        Equipment.family_id == family_id,
        func.upper(Equipment.status) == "OPERACIONAL",
    ).scalar() or 0
    
    # Contar medicações ativas (sem end_date ou com end_date no futuro)
    active_medications = db.query(func.count(Medication.id)).join(
        FamilyMember, Medication.family_member_id == FamilyMember.id
    ).filter(
        FamilyMember.family_id == family_id,
        (Medication.end_date == None) | (Medication.end_date >= now.date())
    ).scalar() or 0
    
    # Ordens ativas são as que ainda estão pendentes
    total_orders = db.query(func.count(MaintenanceOrder.id)).join(
        Equipment, MaintenanceOrder.equipment_id == Equipment.id
    ).filter(
        Equipment.family_id == family_id,
        func.upper(MaintenanceOrder.status) == "PENDENTE",
    ).scalar() or 0

    pendentes, comunicados_semana = _contagens_estudos(db, current_user)
    
    return {
        "total_members": total_members,
        "total_appointments": total_appointments,
        "total_equipment": total_equipment,
        "active_medications": active_medications,
        "total_orders": total_orders,
        "atividades_pendentes": pendentes,
        "comunicados_semana": comunicados_semana,
    }


def _consulta_estudos(db: Session, usuario: User):
    consulta = db.query(func.count(Atividade.id)).filter(Atividade.family_id == usuario.family_id)
    if usuario.is_child:
        return consulta.filter(Atividade.aluno_id == usuario.id)
    if usuario.is_superuser:
        filhos = db.query(User.id).filter(
            User.family_id == usuario.family_id,
            User.is_child.is_(True),
            User.is_active.is_(True),
        )
        return consulta.filter(Atividade.aluno_id.in_(filhos))
    return None


def _contagens_estudos(db: Session, usuario: User) -> tuple[int, int]:
    """Pendências dos filhos e comunicados cuja data cai na semana de segunda a domingo."""
    if usuario.family_id is None:
        return 0, 0
    hoje = datetime.now(timezone(timedelta(hours=-3))).date()
    inicio = hoje - timedelta(days=hoje.weekday())
    fim = inicio + timedelta(days=6)
    if not usuario.is_child and not usuario.is_superuser:
        comunicados = db.query(func.count(Atividade.id)).filter(
            Atividade.family_id == usuario.family_id,
            Atividade.tipo == "comunicado",
            Atividade.data >= inicio,
            Atividade.data <= fim,
        ).scalar() or 0
        return 0, comunicados
    pendentes = _consulta_estudos(db, usuario).filter(
        Atividade.tipo != "comunicado",
        or_(Atividade.status.is_(None), Atividade.status != "concluida"),
    ).scalar() or 0
    comunicados = _consulta_estudos(db, usuario).filter(
        Atividade.tipo == "comunicado",
        Atividade.data >= inicio,
        Atividade.data <= fim,
    ).scalar() or 0
    return pendentes, comunicados

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

