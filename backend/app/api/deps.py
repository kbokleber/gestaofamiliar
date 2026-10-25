from fastapi import Depends, HTTPException, status, Query, Security
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.core.config import settings
from app.core.keycloak import (
    KeycloakTokenError,
    decode_keycloak_token,
    is_keycloak_access_token,
    sync_local_roles,
)
from app.core.security import decode_access_token
from app.db.base import get_db
from app.models.user import User
from app.models.family import Family

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)


def require_menu(menu: str):
    """Bloqueia a API do menu quando o usuário não tem essa área liberada."""

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser or current_user.allowed_menus is None:
            return current_user
        if menu not in current_user.allowed_menus:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a este menu.",
            )
        return current_user

    return _dependency


def _bind_family_cache(user: User) -> User:
    if not hasattr(user, "_cached_family_ids"):
        if user.is_superuser:
            family_ids = [f.id for f in user.families] if user.families else []
            if not family_ids and user.family_id:
                family_ids = [user.family_id]
        else:
            family_ids = [user.family_id] if user.family_id else []
        user._cached_family_ids = family_ids
    return user


def _load_user_by_identity(db: Session, username: Optional[str], email: Optional[str]) -> Optional[User]:
    query = db.query(User).options(joinedload(User.families))
    if username:
        user = query.filter(func.lower(User.username) == username.lower()).first()
        if user:
            return user
    if email:
        return query.filter(func.lower(User.email) == email.lower()).first()
    return None


def _user_from_keycloak_token(token: str, db: Session) -> User:
    try:
        payload = decode_keycloak_token(token)
    except KeycloakTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível validar as credenciais",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload.get("preferred_username")
    email = payload.get("email")
    user = _load_user_by_identity(
        db,
        username if isinstance(username, str) else None,
        email if isinstance(email, str) else None,
    )
    if user is None:
        # Sem criação automática de auth_user, mesmo com KEYCLOAK_ALLOW_SIGNUP.
        detail = (
            "Cadastro automático pelo Keycloak ainda não está habilitado"
            if settings.KEYCLOAK_ALLOW_SIGNUP
            else "Usuário não cadastrado neste sistema"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo",
        )

    if sync_local_roles(user, payload):
        db.commit()
        db.refresh(user)
    return _bind_family_cache(user)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """Obtém o usuário atual a partir do token JWT ou X-API-Token header"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # --- Autenticação por API Token estático (X-API-Token header) ---
    if api_key:
        user = db.query(User).options(
            joinedload(User.families)
        ).filter(User.api_token == api_key, User.is_active == True).first()
        if user is None:
            raise credentials_exception
        return _bind_family_cache(user)

    if not token:
        raise credentials_exception

    if is_keycloak_access_token(token):
        return _user_from_keycloak_token(token, db)

    if not settings.AUTH_LEGACY_PASSWORD_ENABLED:
        raise credentials_exception

    # JWT antigo emitido por POST /auth/login (transição)
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).options(
        joinedload(User.families)
    ).filter(User.id == int(user_id)).first()

    if user is None:
        raise credentials_exception

    return _bind_family_cache(user)


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
    """Retorna lista de IDs das famílias que o usuário tem acesso - OTIMIZADO usando cache"""
    # Usar cache se já foi calculado no get_current_user
    if hasattr(user, '_cached_family_ids'):
        return user._cached_family_ids
    
    # Fallback se não foi cacheado (não deveria acontecer, mas por segurança)
    if user.is_superuser:
        family_ids = [f.id for f in user.families] if user.families else []
        if not family_ids and user.family_id:
            family_ids = [user.family_id]
        return family_ids
    elif user.is_staff:
        return [user.family_id] if user.family_id else []
    else:
        return [user.family_id] if user.family_id else []

async def get_current_family(
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Query(None, description="ID da família (apenas para admins)"),
    db: Session = Depends(get_db)
) -> Optional[int]:
    """
    Retorna o family_id do usuário atual - OTIMIZADO usando cache do usuário.
    Para admins: permite escolher família via query param. Se não fornecer, retorna None (será tratado nos endpoints).
    Para usuários normais: usa a família do usuário.
    Em desenvolvimento: cria família automaticamente se usuário não tiver uma.
    """
    # Se for admin e forneceu family_id, validar e retornar
    if (current_user.is_superuser or current_user.is_staff) and family_id is not None:
        # Usar cache de family_ids se disponível para validação rápida
        cached_family_ids = getattr(current_user, '_cached_family_ids', None)
        
        if cached_family_ids is not None:
            # Verificar acesso usando cache (sem query adicional)
            has_access = family_id in cached_family_ids or family_id == current_user.family_id
            if not has_access:
                # Se não está no cache, verificar se a família existe
                family = db.query(Family).filter(Family.id == family_id).first()
                if not family:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Família não encontrada"
                    )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Você não tem acesso a esta família"
                )
            return family_id
        
        # Fallback: validar que a família existe
        family = db.query(Family).filter(Family.id == family_id).first()
        if not family:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Família não encontrada"
            )
        
        # Se for superuser, validar que tem acesso a essa família
        if current_user.is_superuser:
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário não possui uma família associada. Entre em contato com o administrador."
        )
    
    return current_user.family_id

