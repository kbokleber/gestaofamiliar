from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import create_access_token, verify_password, get_password_hash
from app.db.base import get_db
from app.models.user import User, Profile
from app.models.family import Family
from app.schemas.token import Token
from app.schemas.user import UserCreate, User as UserSchema
import secrets
import string

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login e geração de token JWT"""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register", response_model=Token)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Registro de novo usuário"""
    
    # Verificar se usuário já existe
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nome de usuário já existe"
        )
    
    if db.query(User).filter(User.email == user_data.email).first():
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
    
    # Se não forneceu família, criar uma nova automaticamente
    if not family_id:
        # Gerar código único
        alphabet = string.ascii_uppercase + string.digits
        codigo_unico = ''.join(secrets.choice(alphabet) for _ in range(8))
        
        # Garantir que o código seja único
        while db.query(Family).filter(Family.codigo_unico == codigo_unico).first():
            codigo_unico = ''.join(secrets.choice(alphabet) for _ in range(8))
        
        # Criar nova família
        new_family = Family(
            name=f"Família de {user_data.first_name or user_data.username}",
            codigo_unico=codigo_unico
        )
        db.add(new_family)
        db.commit()
        db.refresh(new_family)
        family_id = new_family.id
    
    # Criar novo usuário
    user = User(
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
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Criar perfil automaticamente
    profile = Profile(user_id=user.id)
    db.add(profile)
    db.commit()
    
    # Gerar token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}
