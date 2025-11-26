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
    """Verifica se o usuário atual é administrador (apenas superuser, não staff)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Apenas administradores podem acessar este recurso."
        )
    return current_user

def get_user_family_ids(user: User, db: Session) -> list[int]:
    """Retorna lista de IDs das famílias que o usuário tem acesso"""
    if user.is_superuser:
        # Carregar relacionamento many-to-many
        db.refresh(user, ['families'])
        family_ids = [f.id for f in user.families] if user.families else []
        # Se não tiver famílias na relação many-to-many, usar family_id
        if not family_ids and user.family_id:
            family_ids = [user.family_id]
        return family_ids
    elif user.is_staff:
        # Staff tem apenas uma família
        return [user.family_id] if user.family_id else []
    else:
        # Usuário normal tem apenas uma família
        return [user.family_id] if user.family_id else []

async def get_current_family(
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Query(None, description="ID da família (apenas para admins)"),
    db: Session = Depends(get_db)
) -> Optional[int]:
    """
    Retorna o family_id do usuário atual.
    Para admins: permite escolher família via query param. Se não fornecer, retorna None (será tratado nos endpoints).
    Para usuários normais: usa a família do usuário.
    Em desenvolvimento: cria família automaticamente se usuário não tiver uma.
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
        
        # Se for superuser, validar que tem acesso a essa família
        if current_user.is_superuser:
            # Carregar relacionamento many-to-many
            from sqlalchemy.orm import joinedload
            db.refresh(current_user, ['families'])
            # Verificar se a família está nas famílias do admin ou é a família principal
            has_access = (
                family_id == current_user.family_id or
                any(f.id == family_id for f in current_user.families)
            )
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem acesso a esta família"
                )
        
        return family_id
    
    # Para admins sem family_id, retornar None (os endpoints tratarão para buscar todas as famílias)
    if (current_user.is_superuser or current_user.is_staff) and family_id is None:
        return None
    
    # Para usuários normais, usar a família do usuário
    if current_user.family_id is None:
        # Em desenvolvimento: criar família automaticamente
        import secrets
        import string
        from app.core.config import settings
        
        # Gerar código único
        alphabet = string.ascii_uppercase + string.digits
        codigo_unico = ''.join(secrets.choice(alphabet) for _ in range(8))
        
        # Garantir que o código seja único
        while db.query(Family).filter(Family.codigo_unico == codigo_unico).first():
            codigo_unico = ''.join(secrets.choice(alphabet) for _ in range(8))
        
        # Criar nova família
        new_family = Family(
            name=f"Família de {current_user.first_name or current_user.username}",
            codigo_unico=codigo_unico
        )
        db.add(new_family)
        db.commit()
        db.refresh(new_family)
        
        # Associar usuário à família
        current_user.family_id = new_family.id
        db.commit()
        db.refresh(current_user)
        
        return new_family.id
    
    return current_user.family_id

