import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user
from app.db.base import SessionLocal, get_db
from app.models.lembrete import FamilyLembreteConfig, PushInscricao
from app.models.user import User
from app.schemas.lembrete import (
    FamilyLembreteConfigResponse,
    FamilyLembreteConfigUpdate,
    PushInscricaoCreate,
)
from app.services.lembrete import chave_publica_vapid, disparar_familia, processar_lembretes_pendentes
from app.api.v1.endpoints.families import _familia_do_admin

router = APIRouter()
logger = logging.getLogger(__name__)


def _resposta(config: FamilyLembreteConfig | None) -> FamilyLembreteConfigResponse:
    if config is None:
        return FamilyLembreteConfigResponse(enabled=False, intervalo=2, unidade="horas")
    return FamilyLembreteConfigResponse(
        enabled=config.enabled,
        intervalo=config.intervalo,
        unidade=config.unidade,
    )


@router.get("/lembretes/{family_id}", response_model=FamilyLembreteConfigResponse)
async def ler_lembrete(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    _familia_do_admin(db, current_user, family_id)
    config = db.query(FamilyLembreteConfig).filter(FamilyLembreteConfig.family_id == family_id).first()
    return _resposta(config)


@router.put("/lembretes/{family_id}", response_model=FamilyLembreteConfigResponse)
async def salvar_lembrete(
    family_id: int,
    payload: FamilyLembreteConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    _familia_do_admin(db, current_user, family_id)
    try:
        payload.validar()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    config = db.query(FamilyLembreteConfig).filter(FamilyLembreteConfig.family_id == family_id).first()
    if config is None:
        config = FamilyLembreteConfig(family_id=family_id)
        db.add(config)
    config.enabled = payload.enabled
    config.intervalo = payload.intervalo
    config.unidade = payload.unidade
    db.commit()
    db.refresh(config)
    return _resposta(config)


@router.get("/notificacoes/chave-publica")
async def chave_publica(current_user: User = Depends(get_current_user)):
    publica = chave_publica_vapid()
    if not publica:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alertas ainda não estão configurados neste servidor.")
    return {"publicKey": publica}


@router.post("/notificacoes/inscricao", status_code=status.HTTP_204_NO_CONTENT)
async def salvar_inscricao(
    payload: PushInscricaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.endpoint or not payload.p256dh() or not payload.auth_key():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Inscrição de notificação incompleta.")
    inscricao = db.query(PushInscricao).filter(PushInscricao.endpoint == payload.endpoint).first()
    if inscricao is None:
        inscricao = PushInscricao(endpoint=payload.endpoint, user_id=current_user.id, p256dh="", auth="")
        db.add(inscricao)
    inscricao.user_id = current_user.id
    inscricao.p256dh = payload.p256dh()
    inscricao.auth = payload.auth_key()
    db.commit()


@router.post("/notificacoes/lembretes/disparar")
async def disparar_agora(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Dispara o mesmo alerta na hora, para testar sem esperar o intervalo."""
    if current_user.family_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Família não encontrada.")
    return disparar_familia(db, current_user.family_id)


async def ciclo_de_lembretes() -> None:
    while True:
        await asyncio.sleep(20)
        db = SessionLocal()
        try:
            processar_lembretes_pendentes(db)
        except Exception:
            logger.warning("Falha no ciclo de lembretes", exc_info=True)
            db.rollback()
        finally:
            db.close()
