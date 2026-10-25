"""API administrativa do Keycloak para criar, alterar e excluir usuários do realm."""
from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import quote

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class KeycloakAdminError(Exception):
    def __init__(self, detail: str, status_code: int = 502):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def admin_configured() -> bool:
    return bool(settings.KEYCLOAK_ADMIN_CLIENT_ID and settings.KEYCLOAK_ADMIN_CLIENT_SECRET)


def _require_config() -> None:
    if not settings.AUTH_KEYCLOAK_ENABLED:
        return
    if not admin_configured():
        raise KeycloakAdminError(
            "Keycloak administrativo não configurado. Defina KEYCLOAK_ADMIN_CLIENT_ID e KEYCLOAK_ADMIN_CLIENT_SECRET.",
            status_code=503,
        )


def _realm() -> str:
    return quote(settings.KEYCLOAK_REALM, safe="")


def _base() -> str:
    return settings.KEYCLOAK_URL.rstrip("/")


def _admin_url(path: str) -> str:
    return f"{_base()}/admin/realms/{_realm()}{path}"


def _token() -> str:
    _require_config()
    url = f"{_base()}/realms/{_realm()}/protocol/openid-connect/token"
    try:
        response = httpx.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.KEYCLOAK_ADMIN_CLIENT_ID,
                "client_secret": settings.KEYCLOAK_ADMIN_CLIENT_SECRET,
            },
            timeout=15.0,
        )
    except httpx.HTTPError as exc:
        logger.exception("Falha ao obter token administrativo do Keycloak")
        raise KeycloakAdminError("Não foi possível conectar ao Keycloak") from exc
    if response.status_code >= 400:
        logger.error("Token administrativo Keycloak %s: %s", response.status_code, response.text[:300])
        raise KeycloakAdminError(
            "Credencial administrativa do Keycloak recusada. Confira o client confidencial e o secret.",
            status_code=502,
        )
    access_token = response.json().get("access_token")
    if not access_token:
        raise KeycloakAdminError("Keycloak não devolveu access token administrativo")
    return access_token


def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    token = _token()
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    try:
        response = httpx.request(method, _admin_url(path), headers=headers, timeout=20.0, **kwargs)
    except httpx.HTTPError as exc:
        logger.exception("Falha na API administrativa do Keycloak")
        raise KeycloakAdminError("Não foi possível conectar ao Keycloak") from exc
    if response.status_code in (401, 403):
        raise KeycloakAdminError(
            "O client administrativo não tem permissão para gerenciar usuários neste realm.",
            status_code=502,
        )
    return response


def find_user_id(username: str) -> Optional[str]:
    response = _request(
        "GET",
        "/users",
        params={"username": username, "exact": "true"},
    )
    if response.status_code >= 400:
        raise KeycloakAdminError("Não foi possível consultar usuários no Keycloak")
    users = response.json()
    if not users:
        return None
    wanted = username.lower()
    for item in users:
        if str(item.get("username", "")).lower() == wanted:
            return item.get("id")
    return users[0].get("id")


def _role(name: str) -> dict:
    response = _request("GET", f"/roles/{quote(name, safe='')}")
    if response.status_code == 404:
        raise KeycloakAdminError(
            f"A role '{name}' não existe no realm do Keycloak.",
            status_code=502,
        )
    if response.status_code >= 400:
        raise KeycloakAdminError(f"Não foi possível ler a role '{name}' no Keycloak")
    payload = response.json()
    return {"id": payload["id"], "name": payload["name"]}


def set_app_roles(user_id: str, *, is_admin: bool) -> None:
    desired = [_role("user")]
    if is_admin:
        desired.append(_role("admin"))
    current = _request("GET", f"/users/{user_id}/role-mappings/realm")
    if current.status_code >= 400:
        raise KeycloakAdminError("Não foi possível ler as roles do usuário no Keycloak")
    removable = [
        {"id": role["id"], "name": role["name"]}
        for role in current.json()
        if role.get("name") in {"admin", "user"}
    ]
    if removable:
        removed = _request(
            "DELETE",
            f"/users/{user_id}/role-mappings/realm",
            json=removable,
        )
        if removed.status_code >= 400:
            raise KeycloakAdminError("Não foi possível atualizar as roles no Keycloak")
    added = _request(
        "POST",
        f"/users/{user_id}/role-mappings/realm",
        json=desired,
    )
    if added.status_code >= 400:
        raise KeycloakAdminError("Não foi possível atribuir as roles no Keycloak")


def set_password(user_id: str, password: str) -> None:
    response = _request(
        "PUT",
        f"/users/{user_id}/reset-password",
        json={"type": "password", "value": password, "temporary": False},
    )
    if response.status_code >= 400:
        raise KeycloakAdminError("Não foi possível definir a senha no Keycloak")


def reset_password(username: str, password: str) -> None:
    user_id = find_user_id(username)
    if not user_id:
        raise KeycloakAdminError(
            "Usuário não encontrado no Keycloak. Cadastre-o de novo pela tela de usuários.",
            status_code=404,
        )
    set_password(user_id, password)


def upsert_user(
    *,
    username: str,
    email: str,
    first_name: str,
    last_name: str,
    password: Optional[str] = None,
    enabled: bool = True,
    is_admin: bool = False,
) -> str:
    """Cria ou atualiza o usuário no Keycloak e devolve o id de lá."""
    existing_id = find_user_id(username)
    body = {
        "username": username,
        "email": email,
        "firstName": first_name or "",
        "lastName": last_name or "",
        "enabled": enabled,
        "emailVerified": True,
    }
    if existing_id:
        response = _request("PUT", f"/users/{existing_id}", json=body)
        if response.status_code >= 400:
            raise KeycloakAdminError("Não foi possível atualizar o usuário no Keycloak")
        user_id = existing_id
    else:
        response = _request("POST", "/users", json=body)
        if response.status_code == 409:
            user_id = find_user_id(username)
            if not user_id:
                raise KeycloakAdminError("Usuário já existe no Keycloak, mas não foi localizado")
        elif response.status_code >= 400:
            detail = "Não foi possível criar o usuário no Keycloak"
            try:
                payload = response.json()
                if isinstance(payload.get("errorMessage"), str):
                    detail = payload["errorMessage"]
            except Exception:
                pass
            raise KeycloakAdminError(detail)
        else:
            location = response.headers.get("Location", "")
            user_id = location.rstrip("/").split("/")[-1] if location else find_user_id(username)
            if not user_id:
                raise KeycloakAdminError("Keycloak criou o usuário sem devolver o id")
    if password:
        set_password(user_id, password)
    set_app_roles(user_id, is_admin=is_admin)
    return user_id


def update_profile(
    username: str,
    *,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> None:
    user_id = find_user_id(username)
    if not user_id:
        raise KeycloakAdminError(
            "Usuário não encontrado no Keycloak. Cadastre-o de novo pela tela de usuários.",
            status_code=404,
        )
    current = _request("GET", f"/users/{user_id}")
    if current.status_code >= 400:
        raise KeycloakAdminError("Não foi possível ler o usuário no Keycloak")
    body = current.json()
    if email is not None:
        body["email"] = email
    if first_name is not None:
        body["firstName"] = first_name
    if last_name is not None:
        body["lastName"] = last_name
    if enabled is not None:
        body["enabled"] = enabled
    response = _request("PUT", f"/users/{user_id}", json=body)
    if response.status_code >= 400:
        raise KeycloakAdminError("Não foi possível atualizar o usuário no Keycloak")


def set_enabled(username: str, enabled: bool) -> None:
    update_profile(username, enabled=enabled)


def sync_admin_role(username: str, *, is_admin: bool) -> None:
    user_id = find_user_id(username)
    if not user_id:
        raise KeycloakAdminError(
            "Usuário não encontrado no Keycloak. Cadastre-o de novo pela tela de usuários.",
            status_code=404,
        )
    set_app_roles(user_id, is_admin=is_admin)


def delete_user(username: str) -> None:
    user_id = find_user_id(username)
    if not user_id:
        return
    response = _request("DELETE", f"/users/{user_id}")
    if response.status_code in (204, 404):
        return
    if response.status_code >= 400:
        raise KeycloakAdminError("Não foi possível excluir o usuário no Keycloak")
