"""Alertas de localização para os adultos da família, entregues como notificação no app deles.

- Chegou / saiu de um lugar cadastrado.
- Bateria do celular da criança em 15% ou menos (um aviso por descarga).
- Celular da criança sem enviar localização há 30 minutos (um aviso por ausência).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.app_android import AppDispositivoAdulto
from app.models.location import LocationDevice
from app.models.user import User
from app.services import avisos_app

logger = logging.getLogger(__name__)

FUSO = ZoneInfo("America/Sao_Paulo")
BATERIA_BAIXA = 15
SEM_SINAL = timedelta(minutes=30)
# Ausência mais antiga que isso não gera alerta novo (ex.: celular desligado há dias).
SEM_SINAL_LIMITE = timedelta(hours=24)
EVENTO_RECENTE = timedelta(hours=1)
VALIDADE_ALERTA = timedelta(hours=3)
URL_LOCALIZACAO = "/localizacao"


def _como_utc(momento: datetime) -> datetime:
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def _hora(momento: datetime) -> str:
    return _como_utc(momento).astimezone(FUSO).strftime("%H:%M")


def _pode_ver_localizacao(usuario: User) -> bool:
    if usuario.is_child or not usuario.is_active:
        return False
    if usuario.is_superuser or usuario.allowed_menus is None:
        return True
    return "localizacao" in (usuario.allowed_menus or [])


def destinatarios(db: Session, family_id: int) -> list[User]:
    """Adultos da família com o app instalado e acesso à Localização."""
    ids = {
        d.user_id
        for d in db.query(AppDispositivoAdulto).filter(
            AppDispositivoAdulto.family_id == family_id,
            AppDispositivoAdulto.revoked_at.is_(None),
        )
    }
    if not ids:
        return []
    usuarios = db.query(User).filter(User.id.in_(ids), User.family_id == family_id).all()
    return [u for u in usuarios if _pode_ver_localizacao(u)]


def avisar(db: Session, family_id: int, tipo: str, titulo: str, texto: str) -> int:
    enviados = 0
    for adulto in destinatarios(db, family_id):
        avisos_app.enfileirar(db, adulto, titulo, texto, URL_LOCALIZACAO, tipo=tipo, validade=VALIDADE_ALERTA)
        enviados += 1
    return enviados


def chegada_saida(db: Session, crianca_nome: str, family_id: int, evento_id: int, frase: str, quando: datetime) -> int:
    """Ex.: "Guilherme chegou na Escola às 07:12". Pontos antigos da fila offline não geram alerta."""
    if datetime.now(timezone.utc) - _como_utc(quando) > EVENTO_RECENTE:
        return 0
    texto = f"{crianca_nome} {frase[0].lower()}{frase[1:]} às {_hora(quando)}"
    return avisar(db, family_id, f"alerta-lugar-{evento_id}", "Localização", texto)


def bateria(db: Session, crianca_nome: str, aparelho: LocationDevice, nivel: Optional[int], anterior: Optional[int]) -> int:
    """Só avisa quando a bateria cruza o limite (estava acima, ou sem dado, e ficou em 15% ou menos)."""
    if nivel is None or nivel > BATERIA_BAIXA:
        return 0
    if anterior is not None and anterior <= BATERIA_BAIXA:
        return 0
    texto = f"Bateria do celular de {crianca_nome} em {nivel}%."
    return avisar(db, aparelho.family_id, f"alerta-bateria-{aparelho.id}", "Bateria baixa", texto)


def verificar_sem_sinal(db: Session, agora: Optional[datetime] = None) -> int:
    """Roda periodicamente: celulares ativos que pararam de enviar há 30 min recebem um alerta só."""
    agora = agora or datetime.now(timezone.utc)
    aparelhos = db.query(LocationDevice).filter(
        LocationDevice.revoked_at.is_(None),
        LocationDevice.last_seen_at.isnot(None),
        LocationDevice.alerta_sem_sinal_em.is_(None),
        LocationDevice.last_seen_at < agora - SEM_SINAL,
        LocationDevice.last_seen_at > agora - SEM_SINAL_LIMITE,
    ).all()
    total = 0
    for aparelho in aparelhos:
        crianca = db.query(User).filter(User.id == aparelho.child_user_id).first()
        aparelho.alerta_sem_sinal_em = agora
        if crianca is None or not crianca.is_active:
            continue
        nome = (crianca.first_name or "").strip() or crianca.username
        texto = f"O celular de {nome} não envia localização desde {_hora(aparelho.last_seen_at)}."
        total += avisar(db, aparelho.family_id, f"alerta-sinal-{aparelho.id}", "Sem localização", texto)
    if aparelhos:
        db.commit()
    return total
