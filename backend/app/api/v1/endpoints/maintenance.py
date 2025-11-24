from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.user import User
from app.models.maintenance import Equipment, MaintenanceOrder, EquipmentAttachment, MaintenanceImage
from app.schemas.maintenance import (
    Equipment as EquipmentSchema,
    EquipmentCreate, EquipmentUpdate, EquipmentDetail,
    MaintenanceOrder as MaintenanceOrderSchema,
    MaintenanceOrderCreate, MaintenanceOrderUpdate, MaintenanceOrderDetail
)
from app.api.deps import get_current_user

router = APIRouter()

# ===== EQUIPMENT =====
@router.post("/equipment", response_model=EquipmentSchema, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    equipment_data: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Criar novo equipamento"""
    equipment = Equipment(**equipment_data.model_dump(exclude_none=False))
    if not equipment.owner_id:
        equipment.owner_id = current_user.id
    
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment

@router.get("/equipment", response_model=List[EquipmentSchema])
async def list_equipment(
    equipment_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Listar todos os equipamentos (compartilhados)"""
    query = db.query(Equipment)
    
    if equipment_type:
        query = query.filter(Equipment.type == equipment_type)
    
    return query.order_by(Equipment.created_at.desc()).all()

@router.get("/equipment/{equipment_id}", response_model=EquipmentDetail)
async def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter detalhes de um equipamento"""
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id,
        Equipment.owner_id == current_user.id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipamento não encontrado"
        )
    
    return equipment

@router.put("/equipment/{equipment_id}", response_model=EquipmentSchema)
async def update_equipment(
    equipment_id: int,
    equipment_data: EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualizar equipamento"""
    # Buscar equipamento sem filtrar por owner_id (equipamentos são compartilhados)
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipamento não encontrado"
        )
    
    # Se o equipamento não tem owner_id, atribuir ao usuário atual
    if not equipment.owner_id:
        equipment.owner_id = current_user.id
    
    # Atualizar campos, garantindo que documents seja processado mesmo se None
    update_data = equipment_data.model_dump(exclude_unset=True)
    
    # Garantir que documents seja processado explicitamente
    if 'documents' in equipment_data.model_dump(exclude_unset=False):
        update_data['documents'] = equipment_data.documents
    
    for field, value in update_data.items():
        setattr(equipment, field, value)
    
    db.commit()
    db.refresh(equipment)
    return equipment

@router.delete("/equipment/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Excluir equipamento"""
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id,
        Equipment.owner_id == current_user.id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipamento não encontrado"
        )
    
    db.delete(equipment)
    db.commit()

# ===== MAINTENANCE ORDERS =====
@router.post("/orders", response_model=MaintenanceOrderSchema, status_code=status.HTTP_201_CREATED)
async def create_maintenance_order(
    order_data: MaintenanceOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Criar nova ordem de manutenção"""
    # Verificar se o equipamento pertence ao usuário
    equipment = db.query(Equipment).filter(
        Equipment.id == order_data.equipment_id,
        Equipment.owner_id == current_user.id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipamento não encontrado"
        )
    
    order_data_dict = order_data.model_dump(exclude_none=False)
    # Normalizar status para maiúsculas
    if 'status' in order_data_dict and order_data_dict['status']:
        order_data_dict['status'] = order_data_dict['status'].upper()
    
    order = MaintenanceOrder(**order_data_dict, created_by_id=current_user.id)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

@router.get("/orders", response_model=List[MaintenanceOrderSchema])
async def list_maintenance_orders(
    equipment_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Listar todas as ordens de manutenção (compartilhadas)"""
    query = db.query(MaintenanceOrder)
    
    if equipment_id:
        query = query.filter(MaintenanceOrder.equipment_id == equipment_id)
    
    if status:
        query = query.filter(MaintenanceOrder.status == status)
    
    return query.order_by(MaintenanceOrder.completion_date.desc()).all()

@router.get("/orders/{order_id}", response_model=MaintenanceOrderDetail)
async def get_maintenance_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter detalhes de uma ordem de manutenção"""
    order = db.query(MaintenanceOrder).join(Equipment).filter(
        MaintenanceOrder.id == order_id,
        Equipment.owner_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordem de manutenção não encontrada"
        )
    
    return order

@router.put("/orders/{order_id}", response_model=MaintenanceOrderSchema)
async def update_maintenance_order(
    order_id: int,
    order_data: MaintenanceOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualizar ordem de manutenção"""
    order = db.query(MaintenanceOrder).join(Equipment).filter(
        MaintenanceOrder.id == order_id,
        Equipment.owner_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordem de manutenção não encontrada"
        )
    
    for field, value in order_data.model_dump(exclude_unset=True).items():
        # Normalizar status para maiúsculas se estiver sendo atualizado
        if field == 'status' and value:
            value = value.upper()
        setattr(order, field, value)
    
    db.commit()
    db.refresh(order)
    return order

@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Excluir ordem de manutenção"""
    order = db.query(MaintenanceOrder).join(Equipment).filter(
        MaintenanceOrder.id == order_id,
        Equipment.owner_id == current_user.id
    ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordem de manutenção não encontrada"
        )
    
    db.delete(order)
    db.commit()

# ===== DASHBOARD & STATS =====
@router.get("/dashboard/stats")
async def get_maintenance_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter estatísticas de manutenção"""
    from sqlalchemy import func
    from datetime import datetime, timedelta
    
    # Total de equipamentos
    total_equipment = db.query(func.count(Equipment.id)).filter(
        Equipment.owner_id == current_user.id
    ).scalar()
    
    # Total de ordens de manutenção
    total_orders = db.query(func.count(MaintenanceOrder.id)).join(Equipment).filter(
        Equipment.owner_id == current_user.id
    ).scalar()
    
    # Ordens pendentes
    pending_orders = db.query(func.count(MaintenanceOrder.id)).join(Equipment).filter(
        Equipment.owner_id == current_user.id,
        MaintenanceOrder.status == 'pendente'
    ).scalar()
    
    # Ordens em andamento
    in_progress_orders = db.query(func.count(MaintenanceOrder.id)).join(Equipment).filter(
        Equipment.owner_id == current_user.id,
        MaintenanceOrder.status == 'em_andamento'
    ).scalar()
    
    # Custo total dos últimos 30 dias
    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_cost = db.query(func.sum(MaintenanceOrder.cost)).join(Equipment).filter(
        Equipment.owner_id == current_user.id,
        MaintenanceOrder.completion_date >= thirty_days_ago.date()
    ).scalar() or 0
    
    # Equipamentos por tipo
    equipment_by_type = db.query(
        Equipment.type,
        func.count(Equipment.id).label('count')
    ).filter(
        Equipment.owner_id == current_user.id
    ).group_by(Equipment.type).all()
    
    return {
        "total_equipment": total_equipment,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "in_progress_orders": in_progress_orders,
        "recent_cost": float(recent_cost),
        "equipment_by_type": [{"type": t, "count": c} for t, c in equipment_by_type]
    }

