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
    TesteAlarmeIn,
)
from app.services import avisos_app
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
        som=config.som or "desligado",
        volume=config.volume or "medio",
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
    if payload.som is not None:
        config.som = payload.som
    if payload.volume is not None:
        config.volume = payload.volume
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


@router.post("/notificacoes/lembretes/testar-alarme")
async def testar_alarme(
    payload: TesteAlarmeIn | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """TEMPORÁRIO: toca o alarme só no celular do adulto logado (nunca nos filhos)."""
    dados = payload or TesteAlarmeIn()
    try:
        return avisos_app.testar_alarme_no_adulto(db, current_user, dados.som, dados.volume)
    except avisos_app.SemCelularDeAdulto as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


async def ciclo_de_lembretes() -> None:
    from app.services.alertas_adultos import verificar_sem_sinal

    voltas = 0
    while True:
        await asyncio.sleep(20)
        voltas += 1
        db = SessionLocal()
        try:
            processar_lembretes_pendentes(db)
            # A cada ~1 minuto: celulares de crianças que pararam de enviar localização.
            if voltas % 3 == 0:
                verificar_sem_sinal(db)
        except Exception:
            logger.warning("Falha no ciclo de lembretes", exc_info=True)
            db.rollback()
        finally:
            db.close()
