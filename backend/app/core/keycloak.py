"""Validação de access token do Keycloak (realm família) via JWKS."""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

_jwks_lock = threading.Lock()
_jwks_cache: dict[str, Any] = {"keys": None, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 3600
_APP_ROLES = frozenset({"admin", "user"})


class KeycloakTokenError(Exception):
    """Token Bearer não é um JWT válido deste realm."""


def keycloak_issuer() -> str:
    if settings.KEYCLOAK_ISSUER:
        return settings.KEYCLOAK_ISSUER
    realm = quote(settings.KEYCLOAK_REALM, safe="")
    return f"{settings.KEYCLOAK_URL.rstrip('/')}/realms/{realm}"


def _jwks_url() -> str:
    return f"{keycloak_issuer().rstrip('/')}/protocol/openid-connect/certs"


def get_jwks(*, force: bool = False) -> dict:
    now = time.time()
    with _jwks_lock:
        cached = _jwks_cache["keys"]
        if (
            not force
            and cached is not None
            and now - float(_jwks_cache["fetched_at"]) < _JWKS_TTL_SECONDS
        ):
            return cached

    with httpx.Client(timeout=10.0) as client:
        response = client.get(_jwks_url())
        response.raise_for_status()
        data = response.json()

    with _jwks_lock:
        _jwks_cache["keys"] = data
        _jwks_cache["fetched_at"] = time.time()
    return data


def _unverified_claims(token: str) -> Optional[dict]:
    try:
        claims = jwt.get_unverified_claims(token)
    except JWTError:
        return None
    return claims if isinstance(claims, dict) else None


def is_keycloak_access_token(token: str) -> bool:
    """True quando o `iss` do token é o deste realm (sem validar assinatura)."""
    if not settings.AUTH_KEYCLOAK_ENABLED:
        return False
    claims = _unverified_claims(token)
    if not claims:
        return False
    return claims.get("iss") == keycloak_issuer()


def decode_keycloak_token(token: str) -> dict:
    """Valida assinatura (JWKS), iss, aud e exp. Uma nova busca de chaves se o kid falhar."""
    audience = settings.KEYCLOAK_AUDIENCE or settings.KEYCLOAK_CLIENT_ID
    issuer = keycloak_issuer()
    last_error: Optional[Exception] = None

    for force in (False, True):
        try:
            payload = jwt.decode(
                token,
                get_jwks(force=force),
                algorithms=["RS256"],
                audience=audience,
                issuer=issuer,
                options={"verify_aud": True, "verify_exp": True, "verify_iss": True},
            )
            return payload
        except JWTError as exc:
            last_error = exc
            logger.info("Token Keycloak rejeitado (refresh_jwks=%s): %s", force, exc)
        except httpx.HTTPError as exc:
            logger.exception("Falha ao buscar JWKS do Keycloak")
            raise KeycloakTokenError("Não foi possível validar o token") from exc

    raise KeycloakTokenError("Token Keycloak inválido") from last_error


def app_roles(payload: dict) -> set[str]:
    realm_access = payload.get("realm_access") or {}
    roles = realm_access.get("roles") or []
    return {role for role in roles if role in _APP_ROLES}


def assert_app_role(payload: dict) -> set[str]:
    roles = app_roles(payload)
    if not roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado. Usuário sem papel admin ou user.",
        )
    return roles


def sync_local_roles(user, payload: dict) -> bool:
    """Espelha realm roles no usuário local. Retorna True se alterou flags."""
    roles = assert_app_role(payload)
    is_admin = "admin" in roles
    changed = False
    if user.is_superuser != is_admin:
        user.is_superuser = is_admin
        changed = True
    if user.is_staff != is_admin:
        user.is_staff = is_admin
        changed = True
    return changed
