"""Avisos para o app Android da criança.

O app não tem canal próprio de push: a cada ~5 minutos ele envia a localização,
e a resposta desse envio traz os avisos pendentes. Assim não há Firebase nem conta extra.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.lembrete import AvisoApp
from app.models.location import LocationDevice
from app.models.user import User

VALIDADE_PADRAO = timedelta(hours=6)
MAX_POR_ENTREGA = 5


def tem_app(db: Session, crianca: User) -> bool:
    """A criança tem um celular pareado e ativo, da família atual."""
    return db.query(LocationDevice).filter(
        LocationDevice.child_user_id == crianca.id,
        LocationDevice.family_id == crianca.family_id,
        LocationDevice.revoked_at.is_(None),
    ).first() is not None


def enfileirar(
    db: Session,
    crianca: User,
    titulo: str,
    texto: str,
    url: Optional[str] = None,
    tipo: str = "lembrete",
    validade: timedelta = VALIDADE_PADRAO,
) -> AvisoApp:
    """Guarda o aviso. Um aviso novo do mesmo tipo substitui o anterior ainda não entregue."""
    agora = datetime.now(timezone.utc)
    db.query(AvisoApp).filter(
        AvisoApp.child_user_id == crianca.id,
        AvisoApp.tipo == tipo,
        AvisoApp.entregue_em.is_(None),
    ).delete(synchronize_session=False)
    aviso = AvisoApp(
        family_id=crianca.family_id,
        child_user_id=crianca.id,
        tipo=tipo,
        titulo=titulo[:120],
        texto=texto[:500],
        url=(url or None) and url[:300],
        created_at=agora,
        expira_em=agora + validade,
    )
    db.add(aviso)
    db.flush()
    return aviso


def _como_utc(momento: datetime) -> datetime:
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def entregar(db: Session, aparelho: LocationDevice) -> list[dict]:
    """Avisos pendentes da criança deste celular. Ficam marcados como entregues."""
    agora = datetime.now(timezone.utc)
    pendentes = (
        db.query(AvisoApp)
        .filter(
            AvisoApp.child_user_id == aparelho.child_user_id,
            AvisoApp.family_id == aparelho.family_id,
            AvisoApp.entregue_em.is_(None),
        )
        .order_by(AvisoApp.id.asc())
        .all()
    )
    saida = []
    for aviso in pendentes:
        if _como_utc(aviso.expira_em) < agora:
            db.delete(aviso)
            continue
        if len(saida) >= MAX_POR_ENTREGA:
            break
        aviso.entregue_em = agora
        saida.append({
            "id": aviso.id,
            "tipo": aviso.tipo,
            "titulo": aviso.titulo,
            "texto": aviso.texto,
            "url": aviso.url,
        })
    if pendentes:
        db.commit()
    return saida


def limpar_antigos(db: Session, dias: int = 7) -> int:
    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    return db.query(AvisoApp).filter(AvisoApp.created_at < corte).delete(synchronize_session=False)
