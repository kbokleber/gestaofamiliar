from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.user import User, Profile
from app.schemas.user import User as UserSchema, UserWithProfile, ProfileUpdate
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/me", response_model=UserWithProfile)
async def read_user_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Obter informações do usuário atual com perfil"""
    # Carregar perfil se não estiver carregado
    if not current_user.profile:
        profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if not profile:
            # Criar perfil se não existir
            profile = Profile(user_id=current_user.id)
            db.add(profile)
            db.commit()
            db.refresh(profile)
    
    return current_user

@router.put("/me/profile", response_model=UserWithProfile)
async def update_my_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualizar perfil do usuário atual"""
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
    
    # Atualizar campos
    for field, value in profile_data.dict(exclude_unset=True).items():
        setattr(profile, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@router.get("/{user_id}", response_model=UserSchema)
async def read_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obter informações de um usuário específico"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return user

@router.get("/", response_model=List[UserSchema])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Listar todos os usuários"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users
