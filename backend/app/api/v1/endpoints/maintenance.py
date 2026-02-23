from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import json
from datetime import datetime, timezone
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
    family_id: Optional[int] = Depends(get_current_family)
):
    """Criar novo equipamento"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]  # Usar a primeira família
    elif family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
    
    try:
        equipment_dict = equipment_data.model_dump(exclude_none=False)
        equipment_dict['family_id'] = family_id
        
        # Remover campos que devem ser gerenciados pelo banco de dados
        equipment_dict.pop('created_at', None)
        equipment_dict.pop('updated_at', None)
        equipment_dict.pop('id', None)
        
        # Garantir que campos obrigatórios tenham valores padrão
        if 'service_provider' not in equipment_dict or equipment_dict['service_provider'] is None:
            equipment_dict['service_provider'] = ''
        if 'status' not in equipment_dict or equipment_dict['status'] is None:
            equipment_dict['status'] = 'OPERACIONAL'
        if 'notes' not in equipment_dict or equipment_dict['notes'] is None:
            equipment_dict['notes'] = ''
        
        # Definir created_at e updated_at explicitamente para garantir que não sejam None
        now = datetime.now(timezone.utc)
        equipment_dict['created_at'] = now
        equipment_dict['updated_at'] = now
        
        equipment = Equipment(**equipment_dict)
        if not equipment.owner_id:
            equipment.owner_id = current_user.id
        
        db.add(equipment)
        db.commit()
        db.refresh(equipment)
        return equipment
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar equipamento: {str(e)}"
        )

@router.get("/equipment", response_model=List[EquipmentSchema])
async def list_equipment(
    equipment_type: str = None,
    include_documents: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Listar todos os equipamentos (compartilhados entre usuários da mesma família).
    Use include_documents=false para carregamento mais rápido."""
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
    
    equipments = query.order_by(Equipment.created_at.desc()).all()
    
    # Se não incluir documentos, limpar para economizar banda
    if not include_documents:
        return [
            {
                "id": e.id,
                "family_id": e.family_id,
                "name": e.name,
                "type": e.type,
                "brand": e.brand,
                "model": e.model,
                "serial_number": e.serial_number,
                "purchase_date": e.purchase_date,
                "warranty_expiry": e.warranty_expiry,
                "service_provider": e.service_provider,
                "status": e.status,
                "owner_id": e.owner_id,
                "notes": e.notes,
                "documents": None,
                "has_documents": bool(e.documents and len(e.documents) > 2), # > 2 por causa de "[]"
                "created_at": e.created_at,
                "updated_at": e.updated_at
            }
            for e in equipments
        ]
    
    # Se incluir documentos, também marcar has_documents
    for e in equipments:
        e.has_documents = bool(e.documents and len(e.documents) > 2)
        
    return equipments

@router.get("/equipment/{equipment_id}", response_model=EquipmentDetail)
async def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Obter detalhes de um equipamento"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, verificar se o equipamento pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipamento não encontrado"
            )
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
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
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualizar equipamento"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, verificar se o equipamento pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipamento não encontrado"
            )
        equipment = db.query(Equipment).filter(
            Equipment.id == equipment_id,
            Equipment.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
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
    family_id: Optional[int] = Depends(get_current_family)
):
    """Excluir equipamento"""
    from app.api.deps import get_user_family_ids
    from sqlalchemy.orm import noload
    
    # Se for admin sem family_id especificado, verificar se o equipamento pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Equipamento não encontrado"
            )
        # Usar noload para evitar carregar relacionamentos que podem ter problemas de schema
        equipment = db.query(Equipment).options(
            noload(Equipment.maintenance_orders),
            noload(Equipment.attachments)
        ).filter(
            Equipment.id == equipment_id,
            Equipment.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        # Usar noload para evitar carregar relacionamentos que podem ter problemas de schema
        equipment = db.query(Equipment).options(
            noload(Equipment.maintenance_orders),
            noload(Equipment.attachments)
        ).filter(
            Equipment.id == equipment_id,
            Equipment.family_id == family_id
        ).first()
    
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipamento não encontrado"
        )
    
    try:
        db.delete(equipment)
        db.commit()
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir equipamento: {str(e)}"
        )

# ===== MAINTENANCE ORDERS =====
@router.post("/orders", response_model=MaintenanceOrderSchema, status_code=status.HTTP_201_CREATED)
async def create_maintenance_order(
    order_data: MaintenanceOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Criar nova ordem de manutenção"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]  # Usar a primeira família
    elif family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
    
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
    
    # Remover campos que devem ser gerenciados pelo código
    data_dict.pop('created_at', None)
    data_dict.pop('updated_at', None)
    data_dict.pop('id', None)
    
    # Normalizar status para maiúsculas
    if 'status' in data_dict and data_dict['status']:
        data_dict['status'] = data_dict['status'].upper()
    
    # Definir created_at e updated_at explicitamente para garantir que não sejam None
    now = datetime.now(timezone.utc)
    data_dict['created_at'] = now
    data_dict['updated_at'] = now
    
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
    include_documents: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Listar todas as ordens de manutenção (compartilhadas entre usuários da mesma família).
    Use include_documents=false para carregamento mais rápido."""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, buscar de todas as famílias que tem acesso
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            return []
        query = db.query(MaintenanceOrder).options(joinedload(MaintenanceOrder.equipment)).join(Equipment).filter(
            Equipment.family_id.in_(family_ids)
        )
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        query = db.query(MaintenanceOrder).options(joinedload(MaintenanceOrder.equipment)).join(Equipment).filter(
            Equipment.family_id == family_id
        )
    
    if equipment_id:
        query = query.filter(MaintenanceOrder.equipment_id == equipment_id)
    
    if status:
        query = query.filter(MaintenanceOrder.status == status)
    
    orders = query.order_by(MaintenanceOrder.completion_date.desc()).all()
    
    def equipment_name(o: MaintenanceOrder) -> str:
        return (o.equipment.name if o.equipment else "Desconhecido")
    
    # Se não incluir documentos, retornar dicts com equipment_name (evita N+1 e "Desconhecido" no front)
    if not include_documents:
        return [
            {
                "id": o.id,
                "equipment_id": o.equipment_id,
                "equipment_name": equipment_name(o),
                "title": o.title,
                "description": o.description,
                "status": o.status,
                "priority": o.priority,
                "service_provider": o.service_provider,
                "completion_date": o.completion_date,
                "cost": o.cost,
                "warranty_expiration": o.warranty_expiration,
                "warranty_terms": o.warranty_terms,
                "invoice_number": o.invoice_number,
                "invoice_file": o.invoice_file,
                "notes": o.notes,
                "documents": None,
                "has_documents": bool(o.documents and len(o.documents) > 2),
                "created_by_id": o.created_by_id,
                "created_at": o.created_at,
                "updated_at": o.updated_at
            }
            for o in orders
        ]
    
    # Se incluir documentos, preencher equipment_name para o schema e has_documents
    for o in orders:
        o.has_documents = bool(o.documents and len(o.documents) > 2)
        setattr(o, "equipment_name", equipment_name(o))
    return orders

@router.get("/orders/{order_id}", response_model=MaintenanceOrderDetail)
async def get_maintenance_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Obter detalhes de uma ordem de manutenção"""
    from app.api.deps import get_user_family_ids
    import logging
    logging.info(f"[DEBUG] ===== INICIO GET ORDER {order_id} =====")
    
    try:
        # Se for admin sem family_id especificado, verificar se a ordem pertence a alguma das famílias do admin
        if (current_user.is_superuser or current_user.is_staff) and family_id is None:
            family_ids = get_user_family_ids(current_user, db)
            if not family_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ordem de manutenção não encontrada"
                )
            order = db.query(MaintenanceOrder).join(Equipment).filter(
                MaintenanceOrder.id == order_id,
                Equipment.family_id.in_(family_ids)
            ).first()
        else:
            # Usuário normal ou admin com family_id específico
            if family_id is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
            order = db.query(MaintenanceOrder).join(Equipment).filter(
                MaintenanceOrder.id == order_id,
                Equipment.family_id == family_id
            ).first()
        
        if not order:
            logging.error(f"[ERROR] Ordem {order_id} nao encontrada")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de manutenção não encontrada"
            )
        
        logging.info(f"[DEBUG] Ordem {order_id} encontrada, serializando...")
        
        # Testar serialização manualmente para debug
        try:
            from app.schemas.maintenance import MaintenanceOrderDetail as DetailSchema
            DetailSchema.model_validate(order)
            logging.info(f"[DEBUG] Serializacao Pydantic OK")
        except Exception as e:
            logging.error(f"[ERROR] Falha na serializacao: {e}")
            import traceback
            logging.error(traceback.format_exc())
            # Não interromper aqui, deixar o FastAPI tentar retornar
            
        logging.info(f"[DEBUG] ===== FIM GET ORDER {order_id} (SUCESSO) =====")
        return order
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logging.error(f"[ERROR] Erro inesperado no GET ORDER {order_id}: {e}")
        logging.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao carregar detalhes da ordem: {str(e)}"
        )

@router.put("/orders/{order_id}", response_model=MaintenanceOrderSchema)
async def update_maintenance_order(
    order_id: int,
    order_data: MaintenanceOrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualizar ordem de manutenção"""
    from app.api.deps import get_user_family_ids
    import logging
    logging.info(f"[DEBUG] ===== INICIO UPDATE ORDER {order_id} =====")
    try:
        # Se for admin sem family_id especificado, verificar se a ordem pertence a alguma das famílias do admin
        if (current_user.is_superuser or current_user.is_staff) and family_id is None:
            family_ids = get_user_family_ids(current_user, db)
            if not family_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ordem de manutenção não encontrada"
                )
            order = db.query(MaintenanceOrder).join(Equipment).filter(
                MaintenanceOrder.id == order_id,
                Equipment.family_id.in_(family_ids)
            ).first()
        else:
            # Usuário normal ou admin com family_id específico
            if family_id is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
            order = db.query(MaintenanceOrder).join(Equipment).filter(
                MaintenanceOrder.id == order_id,
                Equipment.family_id == family_id
            ).first()
        
        if not order:
            logging.error(f"[ERROR] Ordem {order_id} nao encontrada")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de manutenção não encontrada"
            )
        
        logging.info(f"[DEBUG] Ordem {order_id} encontrada")
        
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
            logging.info(f"[DEBUG] UPDATE ORDER {order_id} - documents presente: {all_data['documents'] is not None}")
            if all_data['documents']:
                logging.info(f"[DEBUG] UPDATE ORDER {order_id} - documents tamanho: {len(str(all_data['documents']))} caracteres")
        
        # Atualizar campos (incluindo documents agora)
        for field, value in update_dict.items():
            # Normalizar status para maiúsculas se estiver sendo atualizado
            if field == 'status' and value:
                value = value.upper()
            setattr(order, field, value)
        
        try:
            import logging
            logging.info(f"[DEBUG] Fazendo commit da ordem {order_id}...")
            db.commit()
            logging.info(f"[DEBUG] Commit realizado com sucesso")
            db.refresh(order)
            logging.info(f"[DEBUG] Ordem {order_id} atualizada com sucesso")
            
            # Verificar se a serialização funciona antes de retornar
            from app.schemas.maintenance import MaintenanceOrder as MaintenanceOrderSchema
            logging.info(f"[DEBUG] Testando serializacao Pydantic...")
            try:
                test_schema = MaintenanceOrderSchema.model_validate(order)
                logging.info(f"[DEBUG] Serializacao OK, retornando order")
            except Exception as schema_err:
                logging.error(f"[ERROR] Falha na serializacao Pydantic: {schema_err}")
                raise
            
            logging.info(f"[DEBUG] ===== FIM UPDATE ORDER {order_id} (SUCESSO) =====")
            return order
        except Exception as e:
            db.rollback()
            import logging
            logging.error(f"Erro ao fazer commit da ordem {order_id}: {e}")
            logging.error(f"Tipo do erro: {type(e).__name__}")
            import traceback
            logging.error(traceback.format_exc())
            
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
        import logging
        logging.error(f"ERRO NAO TRATADO no update_maintenance_order: {e}")
        import traceback
        logging.error(traceback.format_exc())
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
    family_id: Optional[int] = Depends(get_current_family)
):
    """Excluir ordem de manutenção"""
    from app.api.deps import get_user_family_ids
    from sqlalchemy.orm import noload
    
    # Se for admin sem family_id especificado, verificar se a ordem pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ordem de manutenção não encontrada"
            )
        # Usar noload para evitar carregar o relacionamento images que pode ter problemas de schema
        order = db.query(MaintenanceOrder).options(noload(MaintenanceOrder.images)).join(Equipment).filter(
            MaintenanceOrder.id == order_id,
            Equipment.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        # Usar noload para evitar carregar o relacionamento images que pode ter problemas de schema
        order = db.query(MaintenanceOrder).options(noload(MaintenanceOrder.images)).join(Equipment).filter(
            MaintenanceOrder.id == order_id,
            Equipment.family_id == family_id
        ).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ordem de manutenção não encontrada"
        )
    
    try:
        db.delete(order)
        db.commit()
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao excluir ordem de manutenção: {str(e)}"
        )

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

