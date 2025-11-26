from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.family import Family
from app.models.user import User
from app.schemas.family import Family as FamilySchema, FamilyCreate, FamilyUpdate
from app.api.deps import get_current_admin
import secrets
import string

router = APIRouter()

def generate_unique_code(length: int = 8) -> str:
    """Gera um código único aleatório"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.get("/", response_model=List[FamilySchema])
async def list_families(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Listar todas as famílias (apenas administradores)"""
    families = db.query(Family).offset(skip).limit(limit).all()
    return families

@router.post("/", response_model=FamilySchema)
async def create_family(
    family_data: FamilyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Criar nova família (apenas administradores) - código único é gerado automaticamente"""
    # Gerar código único (hash) automaticamente até encontrar um disponível
    while True:
        codigo_unico = generate_unique_code()
        existing = db.query(Family).filter(Family.codigo_unico == codigo_unico).first()
        if not existing:
            break
    
    new_family = Family(
        name=family_data.name,
        codigo_unico=codigo_unico
    )
    
    db.add(new_family)
    db.commit()
    db.refresh(new_family)
    
    return new_family

@router.get("/{family_id}", response_model=FamilySchema)
async def read_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Obter informações de uma família específica (apenas administradores)"""
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Família não encontrada"
        )
    return family

@router.put("/{family_id}", response_model=FamilySchema)
async def update_family(
    family_id: int,
    family_data: FamilyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Atualizar família (apenas administradores) - código único não pode ser alterado"""
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Família não encontrada"
        )
    
    # Apenas o nome pode ser alterado - código único é imutável
    if family_data.name is not None:
        family.name = family_data.name
    
    db.commit()
    db.refresh(family)
    
    return family

@router.delete("/{family_id}", response_model=FamilySchema)
async def delete_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Deletar família (apenas administradores)"""
    family = db.query(Family).filter(Family.id == family_id).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Família não encontrada"
        )
    
    # Verificar se há usuários associados
    users_count = db.query(User).filter(User.family_id == family_id).count()
    if users_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Não é possível deletar família com {users_count} usuário(s) associado(s)"
        )
    
    db.delete(family)
    db.commit()
    
    return family

@router.get("/by-code/{codigo_unico}", response_model=FamilySchema)
async def get_family_by_code(
    codigo_unico: str,
    db: Session = Depends(get_db)
):
    """Obter família por código único (público, usado no registro)"""
    family = db.query(Family).filter(Family.codigo_unico == codigo_unico).first()
    if not family:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Família não encontrada"
        )
    return family

