from fastapi import Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.base import get_db
from app.models.user import User
from app.models.family import Family

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Obtém o usuário atual a partir do token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Verifica se o usuário atual é administrador"""
    if not current_user.is_superuser and not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem acessar este recurso."
        )
    return current_user

async def get_current_family(
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Query(None, description="ID da família (apenas para admins)"),
    db: Session = Depends(get_db)
) -> int:
    """
    Retorna o family_id do usuário atual.
    Para admins: permite escolher família via query param.
    Para usuários normais: usa a família do usuário.
    """
    # Se for admin e forneceu family_id, validar e retornar
    if (current_user.is_superuser or current_user.is_staff) and family_id is not None:
        # Validar que a família existe
        family = db.query(Family).filter(Family.id == family_id).first()
        if not family:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Família não encontrada"
            )
        return family_id
    
    # Para usuários normais ou admins sem family_id, usar a família do usuário
    if current_user.family_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário não está associado a uma família"
        )
    
    return current_user.family_id

