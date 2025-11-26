from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json
from app.db.base import get_db
from app.models.user import User
from app.models.maintenance import Equipment, MaintenanceOrder, EquipmentAttachment
from app.schemas.maintenance import (
    Equipment as EquipmentSchema,
    EquipmentCreate, EquipmentUpdate, EquipmentDetail,
    MaintenanceOrder as MaintenanceOrderSchema,
    MaintenanceOrderCreate, MaintenanceOrderUpdate, MaintenanceOrderDetail
)
from app.api.deps import get_current_user, get_current_family

router = APIRouter()

# ===== EQUIPMENT =====
@router.post("/equipment", response_model=EquipmentSchema, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    equipment_data: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Criar novo equipamento"""
    equipment_dict = equipment_data.model_dump(exclude_none=False)
    equipment_dict['family_id'] = family_id
    equipment = Equipment(**equipment_dict)
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
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Listar todos os equipamentos (compartilhados entre usuários da mesma família)"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, buscar de todas as famílias que tem acesso
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            return []
        query = db.query(Equipment).filter(Equipment.family_id.in_(family_ids))
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        query = db.query(Equipment).filter(Equipment.family_id == family_id)
    
    if equipment_type:
        query = query.filter(Equipment.type == equipment_type)
    
    return query.order_by(Equipment.created_at.desc()).all()

@router.get("/equipment/{equipment_id}", response_model=EquipmentDetail)
async def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Obter detalhes de um equipamento"""
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id,
        Equipment.family_id == family_id
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
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Atualizar equipamento"""
    # Filtrar por família (equipamentos são compartilhados entre usuários da mesma família)
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id,
        Equipment.family_id == family_id
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
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Excluir equipamento"""
    equipment = db.query(Equipment).filter(
        Equipment.id == equipment_id,
        Equipment.family_id == family_id
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
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Criar nova ordem de manutenção"""
    # Verificar se o equipamento pertence à família do usuário
    equipment = db.query(Equipment).filter(
        Equipment.id == order_data.equipment_id,
        Equipment.family_id == family_id
    ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipamento não encontrado"
        )
    
    # Usar model_dump (Pydantic v2) para garantir que campos None sejam incluídos
    # Isso é importante para campos opcionais como documents
    data_dict = order_data.model_dump(exclude_none=False)
    
    # Normalizar status para maiúsculas
    if 'status' in data_dict and data_dict['status']:
        data_dict['status'] = data_dict['status'].upper()
    
    # Log para debug
    print(f"[DEBUG] CREATE ORDER - documents presente: {'documents' in data_dict}")
    if data_dict.get('documents'):
        print(f"[DEBUG] CREATE ORDER - documents tamanho: {len(str(data_dict.get('documents')))} caracteres")
    
    order = MaintenanceOrder(**data_dict, created_by_id=current_user.id)
    db.add(order)
    db.commit()
    db.refresh(order)
    
    print(f"[DEBUG] CREATE ORDER - Salvo com ID: {order.id}")
    if hasattr(order, 'documents') and order.documents:
        print(f"[DEBUG] CREATE ORDER - documents salvo: {len(order.documents)} caracteres")
    
    return order

@router.get("/orders", response_model=List[MaintenanceOrderSchema])
async def list_maintenance_orders(
    equipment_id: int = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Listar todas as ordens de manutenção (compartilhadas entre usuários da mesma família)"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, buscar de todas as famílias que tem acesso
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            return []
        query = db.query(MaintenanceOrder).join(Equipment).filter(
            Equipment.family_id.in_(family_ids)
        )
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        query = db.query(MaintenanceOrder).join(Equipment).filter(
            Equipment.family_id == family_id
        )
    
    if equipment_id:
        query = query.filter(MaintenanceOrder.equipment_id == equipment_id)
    
    if status:
        query = query.filter(MaintenanceOrder.status == status)
    
    return query.order_by(MaintenanceOrder.completion_date.desc()).all()

@router.get("/orders/{order_id}", response_model=MaintenanceOrderDetail)
async def get_maintenance_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Obter detalhes de uma ordem de manutenção"""
    # Filtrar por família através do Equipment
    order = db.query(MaintenanceOrder).join(Equipment).filter(
        MaintenanceOrder.id == order_id,
        Equipment.family_id == family_id
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
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Atualizar ordem de manutenção"""
    print(f"[DEBUG] ===== INÍCIO UPDATE ORDER {order_id} =====")
    try:
        # Filtrar por família através do Equipment
        order = db.query(MaintenanceOrder).join(Equipment).filter(
            MaintenanceOrder.id == order_id,
            Equipment.family_id == family_id
        ).first()
        
        if not order:
            print(f"[ERROR] Ordem {order_id} não encontrada")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de manutenção não encontrada"
            )
        
        print(f"[DEBUG] Ordem {order_id} encontrada")
        
        # IMPORTANTE: Para campos opcionais como documents, precisamos garantir que sejam processados
        # mesmo quando são None. O problema é que exclude_unset=True pode não incluir campos None
        # se eles não foram explicitamente definidos no request.
        
        # Primeiro, obter todos os dados (incluindo None)
        all_data = order_data.model_dump(exclude_unset=False)
        
        # Depois, obter apenas campos que foram definidos (exclude_unset=True)
        update_dict = order_data.model_dump(exclude_unset=True)
        
        # CRÍTICO: Se documents está presente em all_data (mesmo que None), significa que foi enviado
        # e deve ser atualizado. Se não está em update_dict mas está em all_data, adicionar.
        if 'documents' in all_data:
            update_dict['documents'] = all_data['documents']
            print(f"[DEBUG] UPDATE ORDER {order_id} - documents presente: {all_data['documents'] is not None}")
            if all_data['documents']:
                print(f"[DEBUG] UPDATE ORDER {order_id} - documents tamanho: {len(str(all_data['documents']))} caracteres")
        
        # Atualizar campos (incluindo documents agora)
        for field, value in update_dict.items():
            # Normalizar status para maiúsculas se estiver sendo atualizado
            if field == 'status' and value:
                value = value.upper()
            setattr(order, field, value)
        
        try:
            print(f"[DEBUG] Fazendo commit da ordem {order_id}...")
            db.commit()
            print(f"[DEBUG] ✅ Commit realizado com sucesso")
            db.refresh(order)
            print(f"[DEBUG] ✅ Ordem {order_id} atualizada com sucesso")
            print(f"[DEBUG] ===== FIM UPDATE ORDER {order_id} (SUCESSO) =====")
            return order
        except Exception as e:
            db.rollback()
            print(f"[ERROR] ❌ Erro ao fazer commit da ordem {order_id}: {e}")
            print(f"[ERROR] Tipo do erro: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            
            # Verificar se é erro de tamanho de campo
            error_str = str(e).lower()
            if 'value too long' in error_str or 'string too long' in error_str or 'data too long' in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Documento muito grande. O campo image no banco pode não ter sido atualizado corretamente. Execute: python backend/update_image_field.py"
                )
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao salvar ordem de manutenção: {str(e)}"
            )
    except HTTPException:
        # Re-raise HTTPException para que FastAPI trate corretamente
        raise
    except Exception as e:
        # Capturar qualquer outro erro não tratado
        print(f"[ERROR] ❌❌❌ ERRO NÃO TRATADO no update_maintenance_order: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro inesperado ao atualizar ordem de manutenção: {str(e)}"
        )

@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_maintenance_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: int = Depends(get_current_family)
):
    """Excluir ordem de manutenção"""
    # Filtrar por família através do Equipment
    order = db.query(MaintenanceOrder).join(Equipment).filter(
        MaintenanceOrder.id == order_id,
        Equipment.family_id == family_id
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

