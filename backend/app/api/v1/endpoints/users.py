from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.user import User, Profile
from app.models.family import Family
from app.schemas.user import User as UserSchema, UserWithProfile, ProfileUpdate, PasswordUpdate, UserCreate, PermissionsUpdate
from app.api.deps import get_current_user, get_current_admin
from app.core.security import get_password_hash

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

@router.post("/", response_model=UserSchema)
async def create_user(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Criar novo usuário (apenas administradores)"""
    # Verificar se usuário já existe
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de usuário já existe"
        )
    
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    
    # Determinar family_id
    family_id = user_data.family_id
    if not family_id and user_data.family_code:
        # Buscar família por código
        family = db.query(Family).filter(Family.codigo_unico == user_data.family_code).first()
        if not family:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Família não encontrada com o código fornecido"
            )
        family_id = family.id
    
    if not family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="É necessário fornecer family_id ou family_code"
        )
    
    # Criar novo usuário
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password=get_password_hash(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        is_active=True,
        is_staff=False,
        is_superuser=False,
        family_id=family_id
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Criar perfil automaticamente
    profile = Profile(user_id=new_user.id)
    db.add(profile)
    db.commit()
    
    return new_user

# Rotas específicas devem vir ANTES das rotas genéricas
@router.put("/{user_id}/password", response_model=UserSchema)
async def update_user_password(
    user_id: int,
    password_data: PasswordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Atualizar senha de um usuário (apenas administradores)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Atualizar senha
    user.password = get_password_hash(password_data.new_password)
    db.commit()
    db.refresh(user)
    
    return user

@router.put("/{user_id}/activate", response_model=UserSchema)
async def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Ativar/desativar usuário (apenas administradores)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Não permitir desativar a si mesmo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode desativar sua própria conta"
        )
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return user

@router.put("/{user_id}/permissions", response_model=UserSchema)
async def update_user_permissions(
    user_id: int,
    permissions_data: PermissionsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Atualizar permissões de um usuário (apenas administradores)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Não permitir remover permissões de si mesmo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode alterar suas próprias permissões"
        )
    
    # Atualizar permissões
    if permissions_data.is_staff is not None:
        user.is_staff = permissions_data.is_staff
    
    if permissions_data.is_superuser is not None:
        user.is_superuser = permissions_data.is_superuser
        # Se for superuser, automaticamente é staff também
        if user.is_superuser:
            user.is_staff = True
    
    db.commit()
    db.refresh(user)
    
    return user

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
