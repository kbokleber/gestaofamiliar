from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.base import get_db
from app.models.user import User
from app.models.healthcare import FamilyMember, MedicalAppointment, MedicalProcedure, Medication
from app.schemas.healthcare import (
    FamilyMember as FamilyMemberSchema, 
    FamilyMemberCreate, FamilyMemberUpdate, FamilyMemberDetail,
    FamilyMemberOrderItem,
    MedicalAppointment as MedicalAppointmentSchema,
    MedicalAppointmentCreate, MedicalAppointmentUpdate,
    MedicalProcedure as MedicalProcedureSchema,
    MedicalProcedureCreate, MedicalProcedureUpdate,
    Medication as MedicationSchema,
    MedicationCreate, MedicationUpdate
)
from app.api.deps import get_current_user, get_current_family

router = APIRouter()

# ===== FAMILY MEMBERS =====
@router.post("/members", response_model=FamilyMemberSchema, status_code=status.HTTP_201_CREATED)
async def create_family_member(
    member_data: FamilyMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Criar novo membro da família (compartilhado entre todos os usuários da mesma família)"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]  # Usar a primeira família
    elif family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
    
    member_data_dict = member_data.model_dump(exclude_none=False)
    member_data_dict['family_id'] = family_id
    
    # Remover campos que devem ser gerenciados pelo banco de dados
    member_data_dict.pop('created_at', None)
    member_data_dict.pop('updated_at', None)
    member_data_dict.pop('id', None)
    
    member = FamilyMember(**member_data_dict)
    
    db.add(member)
    db.commit()
    db.refresh(member)
    return member

@router.get("/members", response_model=List[FamilyMemberSchema])
async def list_family_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Listar todos os membros da família (compartilhados entre usuários da mesma família) ordenados por 'order' e depois nome"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, buscar de todas as famílias que tem acesso
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            return []
        members = db.query(FamilyMember).filter(FamilyMember.family_id.in_(family_ids)).order_by(FamilyMember.order, FamilyMember.name).all()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        members = db.query(FamilyMember).filter(FamilyMember.family_id == family_id).order_by(FamilyMember.order, FamilyMember.name).all()
    return members

@router.get("/members/{member_id}", response_model=FamilyMemberDetail)
async def get_family_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Obter detalhes de um membro da família"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, verificar se o membro pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membro da família não encontrado"
            )
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.family_id == family_id
        ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro da família não encontrado"
        )
    
    return member

# IMPORTANTE: Rota específica /members/reorder DEVE vir ANTES de /members/{member_id}
@router.put("/members/reorder", status_code=status.HTTP_200_OK)
async def reorder_family_members(
    order_data: List[FamilyMemberOrderItem],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualizar a ordem de exibição dos membros da família"""
    from app.api.deps import get_user_family_ids
    
    try:
        # Se for admin sem family_id especificado, buscar de todas as famílias que tem acesso
        if (current_user.is_superuser or current_user.is_staff) and family_id is None:
            family_ids = get_user_family_ids(current_user, db)
            if not family_ids:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        else:
            if family_id is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
            family_ids = [family_id]
        
        for item in order_data:
            member = db.query(FamilyMember).filter(
                FamilyMember.id == item.id,
                FamilyMember.family_id.in_(family_ids)
            ).first()
            if member:
                member.order = item.order
        
        db.commit()
        return {"status": "success", "message": "Ordem atualizada com sucesso"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao atualizar ordem: {str(e)}"
        )

@router.put("/members/{member_id}", response_model=FamilyMemberSchema)
async def update_family_member(
    member_id: int,
    member_data: FamilyMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualizar membro da família"""
    import logging
    from app.api.deps import get_user_family_ids
    logger = logging.getLogger("uvicorn")
    
    # Se for admin sem family_id especificado, verificar se o membro pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membro da família não encontrado"
            )
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.family_id == family_id
        ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro da família não encontrado"
        )
    
    update_dict = member_data.model_dump(exclude_unset=True)
    
    # Log especial para foto (não mostrar a string inteira pois é muito grande)
    log_dict = update_dict.copy()
    if 'photo' in log_dict and log_dict['photo']:
        log_dict['photo'] = f"<base64 string com {len(log_dict['photo'])} caracteres>"
    logger.info(f"🔄 Atualizando membro {member_id} com dados: {log_dict}")
    
    for field, value in update_dict.items():
        if field == 'photo' and value:
            logger.info(f"   ➡️ Setando {field} = <base64 string com {len(value)} caracteres>")
        else:
            logger.info(f"   ➡️ Setando {field} = {value} (tipo: {type(value)})")
        setattr(member, field, value)
    
    db.commit()
    db.refresh(member)
    logger.info(f"✅ Membro atualizado - ID={member.id}, name={member.name}, order={member.order}")
    return member

@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_family_member(
    member_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Excluir membro da família"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, verificar se o membro pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Membro da família não encontrado"
            )
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        member = db.query(FamilyMember).filter(
            FamilyMember.id == member_id,
            FamilyMember.family_id == family_id
        ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro da família não encontrado"
        )
    
    db.delete(member)
    db.commit()

# ===== MEDICAL APPOINTMENTS =====
@router.post("/appointments", response_model=MedicalAppointmentSchema, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: MedicalAppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Criar nova consulta médica"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]  # Usar a primeira família
    elif family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
    
    # Verificar se o membro existe e pertence à família do usuário
    member = db.query(FamilyMember).filter(
        FamilyMember.id == appointment_data.family_member_id,
        FamilyMember.family_id == family_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro da família não encontrado"
        )
    
    # Usar model_dump para garantir que campos opcionais sejam incluídos
    appointment_dict = appointment_data.model_dump(exclude_none=False)
    
    # Remover campos que devem ser gerenciados pelo banco de dados
    appointment_dict.pop('created_at', None)
    appointment_dict.pop('updated_at', None)
    appointment_dict.pop('id', None)
    
    appointment = MedicalAppointment(**appointment_dict)
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment

@router.get("/appointments", response_model=List[MedicalAppointmentSchema])
async def list_appointments(
    member_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Listar consultas médicas (apenas da família do usuário)"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, buscar de todas as famílias que tem acesso
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            return []
        query = db.query(MedicalAppointment).join(FamilyMember).filter(
            FamilyMember.family_id.in_(family_ids)
        )
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        query = db.query(MedicalAppointment).join(FamilyMember).filter(
            FamilyMember.family_id == family_id
        )
    
    if member_id:
        query = query.filter(MedicalAppointment.family_member_id == member_id)
    
    return query.order_by(MedicalAppointment.appointment_date.desc()).all()

@router.put("/appointments/{appointment_id}", response_model=MedicalAppointmentSchema)
async def update_appointment(
    appointment_id: int,
    appointment_data: MedicalAppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualizar consulta médica"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, verificar se a consulta pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consulta não encontrada"
            )
        appointment = db.query(MedicalAppointment).join(FamilyMember).filter(
            MedicalAppointment.id == appointment_id,
            FamilyMember.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        appointment = db.query(MedicalAppointment).join(FamilyMember).filter(
            MedicalAppointment.id == appointment_id,
            FamilyMember.family_id == family_id
        ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada"
        )
    
    for field, value in appointment_data.model_dump(exclude_unset=True).items():
        setattr(appointment, field, value)
    
    db.commit()
    db.refresh(appointment)
    return appointment

@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Excluir consulta médica"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, verificar se a consulta pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Consulta não encontrada"
            )
        appointment = db.query(MedicalAppointment).join(FamilyMember).filter(
            MedicalAppointment.id == appointment_id,
            FamilyMember.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        appointment = db.query(MedicalAppointment).join(FamilyMember).filter(
            MedicalAppointment.id == appointment_id,
            FamilyMember.family_id == family_id
        ).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta não encontrada"
        )
    
    db.delete(appointment)
    db.commit()

# ===== MEDICATIONS =====
@router.post("/medications", response_model=MedicationSchema, status_code=status.HTTP_201_CREATED)
async def create_medication(
    medication_data: MedicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Criar novo medicamento"""
    import logging
    from app.api.deps import get_user_family_ids
    logger = logging.getLogger("uvicorn")
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]  # Usar a primeira família
    elif family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
    
    member = db.query(FamilyMember).filter(
        FamilyMember.id == medication_data.family_member_id,
        FamilyMember.family_id == family_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro da família não encontrado"
        )
    
    # Usar model_dump (Pydantic v2) para garantir que campos None sejam incluídos
    # Isso é importante para campos opcionais como documents
    data_dict = medication_data.model_dump(exclude_none=False)
    
    # Remover campos que devem ser gerenciados pelo banco de dados
    data_dict.pop('created_at', None)
    data_dict.pop('updated_at', None)
    data_dict.pop('id', None)
    
    # Log detalhado para debug
    logger.info(f"🔵 CREATE MEDICATION - Recebido:")
    logger.info(f"   - Campo 'documents' presente: {'documents' in data_dict}")
    logger.info(f"   - Valor de 'documents': {data_dict.get('documents', 'NÃO ENCONTRADO')}")
    if data_dict.get('documents'):
        logger.info(f"   - Tipo: {type(data_dict.get('documents'))}")
        logger.info(f"   - Tamanho: {len(str(data_dict.get('documents')))} caracteres")
    
    medication = Medication(**data_dict)
    db.add(medication)
    db.commit()
    db.refresh(medication)
    
    # Verificar se foi salvo
    logger.info(f"🟢 CREATE MEDICATION - Salvo no banco:")
    logger.info(f"   - ID: {medication.id}")
    logger.info(f"   - Campo 'documents' no objeto: {hasattr(medication, 'documents')}")
    logger.info(f"   - Valor de 'documents': {medication.documents if hasattr(medication, 'documents') else 'ATRIBUTO NÃO EXISTE'}")
    if hasattr(medication, 'documents') and medication.documents:
        logger.info(f"   - Tamanho no banco: {len(medication.documents)} caracteres")
    
    return medication

@router.get("/medications", response_model=List[MedicationSchema])
async def list_medications(
    member_id: int = None,
    active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Listar medicamentos (apenas da família do usuário)"""
    from datetime import date
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, buscar de todas as famílias que tem acesso
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            return []
        query = db.query(Medication).join(FamilyMember).filter(
            FamilyMember.family_id.in_(family_ids)
        )
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        query = db.query(Medication).join(FamilyMember).filter(
            FamilyMember.family_id == family_id
        )
    
    if member_id:
        query = query.filter(Medication.family_member_id == member_id)
    
    if active_only:
        today = date.today()
        query = query.filter(
            Medication.start_date <= today,
            (Medication.end_date.is_(None)) | (Medication.end_date >= today)
        )
    
    return query.order_by(Medication.created_at.desc()).all()

@router.put("/medications/{medication_id}", response_model=MedicationSchema)
async def update_medication(
    medication_id: int,
    medication_data: MedicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualizar medicamento"""
    import logging
    from app.api.deps import get_user_family_ids
    logger = logging.getLogger("uvicorn")
    
    # Se for admin sem family_id especificado, verificar se o medicamento pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medicamento não encontrado"
            )
        medication = db.query(Medication).join(FamilyMember).filter(
            Medication.id == medication_id,
            FamilyMember.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        medication = db.query(Medication).join(FamilyMember).filter(
            Medication.id == medication_id,
            FamilyMember.family_id == family_id
        ).first()
    
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicamento não encontrado"
        )
    
    # IMPORTANTE: Para campos opcionais como documents, precisamos garantir que sejam processados
    # mesmo quando são None. O problema é que exclude_unset=True pode não incluir campos None
    # se eles não foram explicitamente definidos no request.
    
    # Primeiro, obter todos os dados (incluindo None)
    all_data = medication_data.model_dump(exclude_unset=False)
    
    # Depois, obter apenas campos que foram definidos (exclude_unset=True)
    update_dict = medication_data.model_dump(exclude_unset=True)
    
    # Log detalhado para debug
    logger.info(f"🟡 UPDATE MEDICATION {medication_id} - Recebido:")
    logger.info(f"   - Campo 'documents' em exclude_unset=True: {'documents' in update_dict}")
    logger.info(f"   - Campo 'documents' em exclude_unset=False: {'documents' in all_data}")
    logger.info(f"   - Valor de 'documents' (unset): {update_dict.get('documents', 'NÃO ENCONTRADO')}")
    logger.info(f"   - Valor de 'documents' (all): {all_data.get('documents', 'NÃO ENCONTRADO')}")
    
    # CRÍTICO: Se documents está presente em all_data (mesmo que None), significa que foi enviado
    # e deve ser atualizado. Se não está em update_dict mas está em all_data, adicionar.
    if 'documents' in all_data:
        update_dict['documents'] = all_data['documents']
        logger.info(f"   - Documents incluído no update: {all_data['documents'] is not None}")
        if all_data['documents']:
            logger.info(f"   - Tamanho: {len(str(all_data['documents']))} caracteres")
    
    # Atualizar campos
    for field, value in update_dict.items():
        logger.info(f"   - Atualizando {field} = {value if field != 'documents' else ('<JSON>' if value else 'None')}")
        setattr(medication, field, value)
    
    db.commit()
    db.refresh(medication)
    
    # Verificar se foi salvo
    logger.info(f"🟢 UPDATE MEDICATION - Salvo no banco:")
    logger.info(f"   - Campo 'documents' no objeto: {hasattr(medication, 'documents')}")
    logger.info(f"   - Valor de 'documents': {medication.documents if hasattr(medication, 'documents') else 'ATRIBUTO NÃO EXISTE'}")
    if hasattr(medication, 'documents') and medication.documents:
        logger.info(f"   - Tamanho no banco: {len(medication.documents)} caracteres")
    
    return medication

@router.delete("/medications/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medication(
    medication_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Excluir medicamento"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, verificar se o medicamento pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Medicamento não encontrado"
            )
        medication = db.query(Medication).join(FamilyMember).filter(
            Medication.id == medication_id,
            FamilyMember.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        medication = db.query(Medication).join(FamilyMember).filter(
            Medication.id == medication_id,
            FamilyMember.family_id == family_id
        ).first()
    
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicamento não encontrado"
        )
    
    db.delete(medication)
    db.commit()

# ===== PROCEDURES =====
@router.post("/procedures", response_model=MedicalProcedureSchema, status_code=status.HTTP_201_CREATED)
async def create_procedure(
    procedure_data: MedicalProcedureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Criar novo procedimento médico"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, usar a primeira família do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nenhuma família encontrada")
        family_id = family_ids[0]  # Usar a primeira família
    elif family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
    
    member = db.query(FamilyMember).filter(
        FamilyMember.id == procedure_data.family_member_id,
        FamilyMember.family_id == family_id
    ).first()
    
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membro da família não encontrado"
        )
    
    procedure_dict = procedure_data.model_dump(exclude_none=False)
    
    # Remover campos que devem ser gerenciados pelo banco de dados
    procedure_dict.pop('created_at', None)
    procedure_dict.pop('updated_at', None)
    procedure_dict.pop('id', None)
    
    procedure = MedicalProcedure(**procedure_dict)
    db.add(procedure)
    db.commit()
    db.refresh(procedure)
    return procedure

@router.get("/procedures", response_model=List[MedicalProcedureSchema])
async def list_procedures(
    member_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Listar procedimentos médicos (apenas da família do usuário)"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, buscar de todas as famílias que tem acesso
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            return []
        query = db.query(MedicalProcedure).join(FamilyMember).filter(
            FamilyMember.family_id.in_(family_ids)
        )
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        query = db.query(MedicalProcedure).join(FamilyMember).filter(
            FamilyMember.family_id == family_id
        )
    
    if member_id:
        query = query.filter(MedicalProcedure.family_member_id == member_id)
    
    return query.order_by(MedicalProcedure.procedure_date.desc()).all()

@router.put("/procedures/{procedure_id}", response_model=MedicalProcedureSchema)
async def update_procedure(
    procedure_id: int,
    procedure_data: MedicalProcedureUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Atualizar procedimento médico"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, verificar se o procedimento pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Procedimento não encontrado"
            )
        procedure = db.query(MedicalProcedure).join(FamilyMember).filter(
            MedicalProcedure.id == procedure_id,
            FamilyMember.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        procedure = db.query(MedicalProcedure).join(FamilyMember).filter(
            MedicalProcedure.id == procedure_id,
            FamilyMember.family_id == family_id
        ).first()
    
    if not procedure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedimento não encontrado"
        )
    
    # Atualizar campos, garantindo que documents seja processado mesmo se None
    update_data = procedure_data.model_dump(exclude_unset=True)
    
    # Garantir que documents seja processado explicitamente
    if 'documents' in procedure_data.model_dump(exclude_unset=False):
        update_data['documents'] = procedure_data.documents
    
    for field, value in update_data.items():
        setattr(procedure, field, value)
    
    db.commit()
    db.refresh(procedure)
    return procedure

@router.delete("/procedures/{procedure_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_procedure(
    procedure_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family)
):
    """Excluir procedimento médico"""
    from app.api.deps import get_user_family_ids
    
    # Se for admin sem family_id especificado, verificar se o procedimento pertence a alguma das famílias do admin
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        family_ids = get_user_family_ids(current_user, db)
        if not family_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Procedimento não encontrado"
            )
        procedure = db.query(MedicalProcedure).join(FamilyMember).filter(
            MedicalProcedure.id == procedure_id,
            FamilyMember.family_id.in_(family_ids)
        ).first()
    else:
        # Usuário normal ou admin com family_id específico
        if family_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não especificada")
        procedure = db.query(MedicalProcedure).join(FamilyMember).filter(
            MedicalProcedure.id == procedure_id,
            FamilyMember.family_id == family_id
        ).first()
    
    if not procedure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Procedimento não encontrado"
        )
    
    db.delete(procedure)
    db.commit()

