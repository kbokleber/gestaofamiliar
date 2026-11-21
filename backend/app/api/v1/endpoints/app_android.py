"""Download público do app Android da criança e envio de nova versão (só admin).

O APK não fica no git: um admin envia pelo site e o servidor guarda no banco.
"""
import hashlib
import re
from datetime import datetime, timezone

import secrets
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, Security, UploadFile, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, defer

from app.api.deps import get_current_admin, get_current_user, get_db
from app.core.config import settings
from app.models.app_android import AppAndroid, AppDispositivoAdulto, AppPublicacaoToken
from app.models.user import User
from app.services import apk_assinatura, avisos_app

router = APIRouter()

TAMANHO_MAXIMO = 50 * 1024 * 1024
VERSOES_GUARDADAS = 3
VERSAO_VALIDA = re.compile(r"^\d+(\.\d+){0,3}$")


def _info(app: AppAndroid) -> dict:
    criado = app.created_at
    if criado is not None and criado.tzinfo is None:
        criado = criado.replace(tzinfo=timezone.utc)
    return {
        "versao": app.versao,
        "tamanho_bytes": app.tamanho_bytes,
        "sha256": app.sha256,
        "publicado_em": criado.isoformat() if criado else None,
        "arquivo": "/api/v1/app-android/download",
    }


def _ultima(db: Session, com_conteudo: bool = False):
    consulta = db.query(AppAndroid)
    if not com_conteudo:
        consulta = consulta.options(defer(AppAndroid.conteudo))
    return consulta.order_by(AppAndroid.id.desc()).first()


@router.get("/ultima")
def ultima_versao(response: Response, db: Session = Depends(get_db)):
    """Versão disponível para download. Público: o celular da criança não precisa de login.
    no-store: nenhum proxy ou cache guarda a versão antiga; toda publicação nova aparece na hora."""
    response.headers["Cache-Control"] = "no-store"
    app = _ultima(db)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma versão do app foi enviada ainda.")
    return _info(app)


@router.get("/download")
def baixar(db: Session = Depends(get_db)):
    app = _ultima(db, com_conteudo=True)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma versão do app foi enviada ainda.")
    nome = f"GestaoFamiliar-crianca-{app.versao}.apk"
    return Response(
        content=app.conteudo,
        media_type="application/vnd.android.package-archive",
        headers={
            "Content-Disposition": f'attachment; filename="{nome}"',
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def enviar_versao(
    versao: str = Form(...),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Admin envia o APK assinado de uma versão nova; ela passa a ser a baixada em /app."""
    return await _guardar_versao(db, versao, arquivo, admin.id)


publicacao_header = APIKeyHeader(name="X-App-Publish-Token", auto_error=False)


@router.post("/publicar", status_code=status.HTTP_201_CREATED)
async def publicar_com_token(
    versao: str = Form(...),
    arquivo: UploadFile = File(...),
    token: Optional[str] = Security(publicacao_header),
    db: Session = Depends(get_db),
):
    """Publicação automática de uma versão nova, com o token de publicação (só serve para isto)."""
    registro = None
    if token and len(token) >= 20:
        registro = db.query(AppPublicacaoToken).filter(
            AppPublicacaoToken.token_hash == _hash(token.strip()),
            AppPublicacaoToken.revogado_em.is_(None),
        ).first()
    if registro is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de publicação inválido ou revogado.")
    return await _guardar_versao(db, versao, arquivo, registro.criado_por_id)


@router.get("/token-publicacao")
def ver_token_publicacao(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    ativo = db.query(AppPublicacaoToken).filter(AppPublicacaoToken.revogado_em.is_(None)).order_by(AppPublicacaoToken.id.desc()).first()
    return {"ativo": ativo is not None, "criado_em": ativo.created_at.isoformat() if ativo and ativo.created_at else None}


@router.post("/token-publicacao")
def gerar_token_publicacao(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    """Gera um token novo (o anterior deixa de valer). O valor só aparece nesta resposta."""
    agora = datetime.now(timezone.utc)
    for antigo in db.query(AppPublicacaoToken).filter(AppPublicacaoToken.revogado_em.is_(None)):
        antigo.revogado_em = agora
    token = secrets.token_urlsafe(32)
    db.add(AppPublicacaoToken(token_hash=_hash(token), criado_por_id=admin.id, created_at=agora))
    db.commit()
    return {"token": token}


@router.delete("/token-publicacao", status_code=status.HTTP_204_NO_CONTENT)
def revogar_token_publicacao(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    agora = datetime.now(timezone.utc)
    for antigo in db.query(AppPublicacaoToken).filter(AppPublicacaoToken.revogado_em.is_(None)):
        antigo.revogado_em = agora
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- celular do adulto

class RegistrarAdultoIn(BaseModel):
    device_label: Optional[str] = Field(default=None, max_length=80)
    app_versao: Optional[int] = Field(default=None, ge=0)


class AvisosAdultoIn(BaseModel):
    app_versao: Optional[int] = Field(default=None, ge=0)
    notificacoes: Optional[bool] = None
    avisos_recebidos: list[int] = Field(default_factory=list, max_length=50)


dispositivo_header = APIKeyHeader(name="X-Device-Token", auto_error=False)


def _adulto_atual(token: Optional[str] = Security(dispositivo_header), db: Session = Depends(get_db)) -> AppDispositivoAdulto:
    aparelho = None
    if token and len(token.strip()) >= 20:
        aparelho = db.query(AppDispositivoAdulto).filter(
            AppDispositivoAdulto.token_hash == _hash(token.strip()),
            AppDispositivoAdulto.revoked_at.is_(None),
        ).first()
    if aparelho is not None:
        usuario = db.query(User).filter(User.id == aparelho.user_id).first()
        if usuario is None or not usuario.is_active or usuario.is_child or usuario.family_id != aparelho.family_id:
            aparelho.revoked_at = datetime.now(timezone.utc)
            db.commit()
            aparelho = None
    if aparelho is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Celular não registrado ou acesso revogado.")
    return aparelho


@router.post("/dispositivos/registrar")
def registrar_celular_adulto(
    dados: RegistrarAdultoIn,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
):
    """O app de um adulto, já logado, se registra para receber alertas e lembretes como notificação."""
    if usuario.is_child or not usuario.family_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Só adultos da família registram o celular para alertas.")
    token = secrets.token_urlsafe(32)
    agora = datetime.now(timezone.utc)
    aparelho = AppDispositivoAdulto(
        family_id=usuario.family_id,
        user_id=usuario.id,
        token_hash=_hash(token),
        label=((dados.device_label or "").strip() or "Celular")[:80],
        app_versao=dados.app_versao,
        last_seen_at=agora,
        created_at=agora,
    )
    db.add(aparelho)
    db.commit()
    db.refresh(aparelho)
    return {"device_token": token, "device_id": aparelho.id}


@router.post("/dispositivos/avisos")
def avisos_do_adulto(
    dados: AvisosAdultoIn,
    db: Session = Depends(get_db),
    aparelho: AppDispositivoAdulto = Depends(_adulto_atual),
):
    """O app do adulto busca periodicamente os alertas pendentes e confirma os que já mostrou."""
    aparelho.last_seen_at = datetime.now(timezone.utc)
    return {"avisos": avisos_app.atualizar_e_entregar(db, aparelho, dados.app_versao, dados.notificacoes, dados.avisos_recebidos)}


@router.post("/dispositivos/revogar-me", status_code=status.HTTP_204_NO_CONTENT)
def revogar_celular_adulto(db: Session = Depends(get_db), aparelho: AppDispositivoAdulto = Depends(_adulto_atual)):
    aparelho.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _conferir_assinatura(conteudo: bytes) -> None:
    """Só aceita APK assinado com a chave da família (quem já tem o app não atualiza com outra chave)."""
    esperados = {c.strip().lower().replace(":", "") for c in settings.APP_ASSINATURA_SHA256.split(",") if c.strip()}
    if not esperados:
        return
    try:
        encontrados = apk_assinatura.certificados(conteudo)
    except apk_assinatura.ApkInvalido:
        encontrados = set()
    # Todos os certificados precisam ser da família: um bloco v2 com o certificado copiado e um v3 de
    # outra chave seria instalado pelo Android com a outra chave.
    if not encontrados or not encontrados <= esperados:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="O APK não está assinado com a chave do app da família.",
        )


async def _guardar_versao(db: Session, versao: str, arquivo: UploadFile, enviado_por_id: Optional[int]) -> dict:
    versao = versao.strip()
    if not VERSAO_VALIDA.match(versao):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Versão inválida. Use o formato 1.0.2.")
    if not (arquivo.filename or "").lower().endswith(".apk"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envie o arquivo .apk do app.")
    conteudo = await arquivo.read(TAMANHO_MAXIMO + 1)
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="O arquivo passa de 50 MB.")
    # Todo APK é um arquivo ZIP: começa com "PK\x03\x04".
    if not conteudo.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O arquivo não parece ser um APK.")
    _conferir_assinatura(conteudo)
    atual = _ultima(db)
    if atual is not None and VERSAO_VALIDA.match(atual.versao) and apk_assinatura.comparar_versoes(versao, atual.versao) < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"A versão {versao} é mais antiga que a publicada ({atual.versao}).",
        )
    novo = AppAndroid(
        versao=versao,
        tamanho_bytes=len(conteudo),
        sha256=hashlib.sha256(conteudo).hexdigest(),
        conteudo=conteudo,
        enviado_por_id=enviado_por_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(novo)
    db.flush()
    antigos = db.query(AppAndroid.id).order_by(AppAndroid.id.desc()).offset(VERSOES_GUARDADAS).all()
    if antigos:
        db.query(AppAndroid).filter(AppAndroid.id.in_([a.id for a in antigos])).delete(synchronize_session=False)
    db.commit()
    db.refresh(novo)
    return _info(novo)
