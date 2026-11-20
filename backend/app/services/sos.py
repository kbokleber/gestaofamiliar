"""Botão SOS do app: registra o pedido e avisa só os familiares escolhidos.

Canal: o mesmo dos alertas (fila de avisos buscada pelo app do adulto) e, para quem ativou
as notificações do navegador, o Web Push dos lembretes, que chega na hora. Sem central e
sem ligação automática.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.lembrete import PushInscricao
from app.models.location import LocationDevice, LocationSos, LocationSosDestinatario
from app.models.user import User
from app.schemas.location import SosIn
from app.services import avisos_app
from app.services.localizacao import (
    FUSO,
    adulto_com_localizacao,
    como_utc,
    familia_do_cadastro,
    familias_do_adulto,
    nome_de,
    ultimo_ponto,
)

logger = logging.getLogger(__name__)

# Um SOS por celular a cada 2 minutos: o segundo toque por engano não manda outro aviso.
INTERVALO_SOS = timedelta(minutes=2)
VALIDADE_AVISO_SOS = timedelta(hours=24)
RECENTES = timedelta(hours=24)


def _hora(momento: Optional[datetime]) -> str:
    return como_utc(momento).astimezone(FUSO).strftime("%H:%M") if momento else "--:--"


def opcoes_de_destinatario(db: Session, family_id: int) -> list[User]:
    """Quem pode receber o SOS: adultos ativos da família que VEEM o mapa (nunca quem só é visto)."""
    candidatos = (
        db.query(User)
        .filter(User.family_id == family_id, User.is_child.is_(False), User.is_active.is_(True))
        .order_by(User.first_name, User.last_name, User.username)
        .all()
    )
    return [usuario for usuario in candidatos if adulto_com_localizacao(usuario)]


def destinatarios(db: Session, family_id: int, quem_pediu_id: int) -> list[User]:
    """Os escolhidos pela família. Se ninguém foi escolhido ainda, todos os adultos que veem o mapa,
    para um SOS nunca se perder. Quem pediu não recebe o próprio aviso."""
    opcoes = opcoes_de_destinatario(db, family_id)
    escolhidos = {
        d.user_id for d in db.query(LocationSosDestinatario).filter(LocationSosDestinatario.family_id == family_id)
    }
    lista = [u for u in opcoes if u.id in escolhidos] if escolhidos else opcoes
    return [u for u in lista if u.id != quem_pediu_id]


def _push_navegador(db: Session, usuario: User, titulo: str, texto: str, url: str) -> int:
    inscricoes = db.query(PushInscricao).filter(PushInscricao.user_id == usuario.id).all()
    if not inscricoes:
        return 0
    from app.services.lembrete import _chave_privada, chave_publica_vapid

    privada = _chave_privada()
    if not privada or not chave_publica_vapid():
        return 0
    from pywebpush import WebPushException, webpush

    corpo = json.dumps({"title": titulo, "body": texto, "url": url})
    enviados = 0
    for inscricao in inscricoes:
        try:
            webpush(
                subscription_info={"endpoint": inscricao.endpoint, "keys": {"p256dh": inscricao.p256dh, "auth": inscricao.auth}},
                data=corpo,
                vapid_private_key=privada,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
            )
            enviados += 1
        except WebPushException as exc:
            if getattr(getattr(exc, "response", None), "status_code", None) in {404, 410}:
                db.delete(inscricao)
            logger.warning("SOS: falha no push para user_id=%s", usuario.id)
        except Exception:
            logger.warning("SOS: falha no push para user_id=%s", usuario.id, exc_info=True)
    return enviados


def texto_do_aviso(nome: str, criado_em: datetime, posicao_em: Optional[datetime], bateria: Optional[int]) -> str:
    partes = [f"{nome} pediu socorro às {_hora(criado_em)}."]
    partes.append(f"Última posição às {_hora(posicao_em)}." if posicao_em else "Sem posição conhecida.")
    if bateria is not None:
        partes.append(f"Bateria {bateria}%.")
    return " ".join(partes)


def registrar_sos(db: Session, aparelho: LocationDevice, dados: SosIn) -> dict:
    agora = datetime.now(timezone.utc)
    recente = (
        db.query(LocationSos)
        .filter(LocationSos.device_id == aparelho.id, LocationSos.created_at >= agora - INTERVALO_SOS)
        .order_by(LocationSos.id.desc())
        .first()
    )
    if recente is not None:
        return {"id": recente.id, "repetido": True, "avisados": recente.avisados}

    dono = db.query(User).filter(User.id == aparelho.child_user_id).first()
    if dono is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Aparelho não pareado ou token revogado.")
    ultimo = ultimo_ponto(db, dono.id)
    if dados.latitude is not None and dados.longitude is not None:
        latitude, longitude, precisao = dados.latitude, dados.longitude, dados.accuracy_m
        posicao_em = como_utc(dados.recorded_at) if dados.recorded_at else agora
    elif ultimo is not None:
        latitude, longitude, precisao = ultimo.latitude, ultimo.longitude, ultimo.accuracy_m
        posicao_em = como_utc(ultimo.recorded_at)
    else:
        latitude = longitude = precisao = posicao_em = None
    bateria = dados.battery_level if dados.battery_level is not None else (ultimo.battery_level if ultimo else None)

    sos = LocationSos(
        family_id=aparelho.family_id,
        user_id=dono.id,
        device_id=aparelho.id,
        latitude=latitude,
        longitude=longitude,
        accuracy_m=precisao,
        battery_level=bateria,
        posicao_em=posicao_em,
        created_at=agora,
    )
    db.add(sos)
    db.flush()
    nome = nome_de(dono)
    titulo = f"SOS de {nome}"
    texto = texto_do_aviso(nome, agora, posicao_em, bateria)
    url = f"/localizacao?sos={sos.id}"
    avisados = 0
    for adulto in destinatarios(db, aparelho.family_id, dono.id):
        avisos_app.enfileirar(db, adulto, titulo, texto, url, tipo=f"sos-{sos.id}", validade=VALIDADE_AVISO_SOS)
        _push_navegador(db, adulto, titulo, texto, url)
        avisados += 1
    sos.avisados = avisados
    db.commit()
    logger.info("SOS registrado sos_id=%s device_id=%s avisados=%s", sos.id, aparelho.id, avisados)
    return {"id": sos.id, "repetido": False, "avisados": avisados}


def _serializar(db: Session, sos: LocationSos) -> dict:
    pessoa = db.query(User).filter(User.id == sos.user_id).first()
    visto_por = db.query(User).filter(User.id == sos.visto_por_id).first() if sos.visto_por_id else None
    return {
        "id": sos.id,
        "pessoa_id": sos.user_id,
        "nome": nome_de(pessoa) if pessoa else "?",
        "adulto": bool(pessoa and not pessoa.is_child),
        "criado_em": como_utc(sos.created_at),
        "latitude": sos.latitude,
        "longitude": sos.longitude,
        "accuracy_m": sos.accuracy_m,
        "bateria": sos.battery_level,
        "posicao_em": como_utc(sos.posicao_em) if sos.posicao_em else None,
        "visto_em": como_utc(sos.visto_em) if sos.visto_em else None,
        "visto_por": nome_de(visto_por) if visto_por else None,
    }


def listar_sos(db: Session, adulto: User) -> list[dict]:
    """SOS ainda não vistos e os das últimas 24 h, só das famílias do adulto."""
    familias = familias_do_adulto(adulto, db)
    corte = datetime.now(timezone.utc) - RECENTES
    lista = (
        db.query(LocationSos)
        .filter(LocationSos.family_id.in_(familias))
        .filter((LocationSos.visto_em.is_(None)) | (LocationSos.created_at >= corte))
        .order_by(LocationSos.id.desc())
        .limit(50)
        .all()
    )
    return [_serializar(db, sos) for sos in lista]


def marcar_visto(db: Session, adulto: User, sos_id: int) -> dict:
    familias = familias_do_adulto(adulto, db)
    sos = db.query(LocationSos).filter(LocationSos.id == sos_id, LocationSos.family_id.in_(familias)).first()
    if sos is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SOS não encontrado nesta família.")
    if sos.visto_em is None:
        sos.visto_em = datetime.now(timezone.utc)
        sos.visto_por_id = adulto.id
        db.commit()
    return _serializar(db, sos)


def ler_destinatarios(db: Session, adulto: User, family_id: Optional[int]) -> dict:
    familia = familia_do_cadastro(adulto, db, family_id)
    opcoes = opcoes_de_destinatario(db, familia)
    escolhidos = [
        d.user_id for d in db.query(LocationSosDestinatario).filter(LocationSosDestinatario.family_id == familia)
    ]
    validos = {u.id for u in opcoes}
    return {
        "family_id": familia,
        "opcoes": [{"id": u.id, "nome": nome_de(u)} for u in opcoes],
        "escolhidos": [i for i in escolhidos if i in validos],
    }


def salvar_destinatarios(db: Session, adulto: User, family_id: Optional[int], user_ids: list[int]) -> dict:
    familia = familia_do_cadastro(adulto, db, family_id)
    validos = {u.id for u in opcoes_de_destinatario(db, familia)}
    invalidos = [i for i in user_ids if i not in validos]
    if invalidos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Só adultos desta família que veem o mapa podem receber o SOS.",
        )
    db.query(LocationSosDestinatario).filter(LocationSosDestinatario.family_id == familia).delete(synchronize_session=False)
    for user_id in dict.fromkeys(user_ids):
        db.add(LocationSosDestinatario(family_id=familia, user_id=user_id))
    db.commit()
    return ler_destinatarios(db, adulto, familia)
