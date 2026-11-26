"""Avisos para o app Android da criança.

O app não tem canal próprio de push: a cada ~5 minutos ele envia a localização,
e a resposta desse envio traz os avisos pendentes. Assim não há Firebase nem conta extra.

Entrega com confirmação: o aviso volta em toda resposta até o app confirmar
(campo avisos_recebidos do envio seguinte) ou até vencer. Resposta perdida não apaga o aviso.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.models.lembrete import AvisoApp
from app.models.location import LocationDevice
from app.models.user import User

VALIDADE_PADRAO = timedelta(hours=6)
MAX_POR_ENTREGA = 5
# O app conta como ativo só se mandou posição há pouco; senão o lembrete vai pelo navegador.
APP_ATIVO_JANELA = timedelta(minutes=30)
# Primeira versão do app que mostra e confirma avisos (versionCode da 1.0.2).
VERSAO_MINIMA_AVISOS = 3


def _como_utc(momento: datetime) -> datetime:
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def aparelho_pode_receber(aparelho: LocationDevice, agora: Optional[datetime] = None) -> bool:
    agora = agora or datetime.now(timezone.utc)
    return (
        aparelho.revoked_at is None
        and (aparelho.app_versao or 0) >= VERSAO_MINIMA_AVISOS
        and aparelho.notificacoes_ativas is True
        and aparelho.last_seen_at is not None
        and agora - _como_utc(aparelho.last_seen_at) <= APP_ATIVO_JANELA
    )


def tem_app(db: Session, crianca: User) -> bool:
    """A criança tem um celular pareado, com app novo, notificações liberadas e enviando agora há pouco."""
    agora = datetime.now(timezone.utc)
    aparelhos = db.query(LocationDevice).filter(
        LocationDevice.child_user_id == crianca.id,
        LocationDevice.family_id == crianca.family_id,
        LocationDevice.revoked_at.is_(None),
    ).all()
    return any(aparelho_pode_receber(a, agora) for a in aparelhos)


def enfileirar(
    db: Session,
    crianca: User,
    titulo: str,
    texto: str,
    url: Optional[str] = None,
    tipo: str = "lembrete",
    validade: timedelta = VALIDADE_PADRAO,
    expira_em: Optional[datetime] = None,
    som: Optional[str] = None,
    volume: Optional[str] = None,
) -> AvisoApp:
    """Guarda o aviso. Um aviso novo do mesmo tipo substitui o anterior ainda não confirmado."""
    agora = datetime.now(timezone.utc)
    db.query(AvisoApp).filter(
        AvisoApp.child_user_id == crianca.id,
        AvisoApp.tipo == tipo,
        AvisoApp.entregue_em.is_(None),
    # "fetch" tira o aviso antigo da sessão: no SQLite o id pode ser reaproveitado pelo novo.
    ).delete(synchronize_session="fetch")
    aviso = AvisoApp(
        family_id=crianca.family_id,
        child_user_id=crianca.id,
        tipo=tipo,
        titulo=titulo[:120],
        texto=texto[:500],
        url=(url or None) and url[:300],
        som=None if som in (None, "desligado") else som,
        volume=volume if som not in (None, "desligado") else None,
        created_at=agora,
        expira_em=expira_em or (agora + validade),
    )
    db.add(aviso)
    db.flush()
    return aviso


def _dono(aparelho) -> int:
    """Dono dos avisos: a criança do celular (LocationDevice) ou o adulto (AppDispositivoAdulto)."""
    return aparelho.child_user_id if hasattr(aparelho, "child_user_id") else aparelho.user_id


def confirmar(db: Session, aparelho, ids: Iterable[int]) -> int:
    """Marca como entregues os avisos que o app confirmou ter mostrado."""
    ids = [i for i in ids if isinstance(i, int)]
    if not ids:
        return 0
    agora = datetime.now(timezone.utc)
    avisos = db.query(AvisoApp).filter(
        AvisoApp.id.in_(ids),
        AvisoApp.child_user_id == _dono(aparelho),
        AvisoApp.family_id == aparelho.family_id,
        AvisoApp.entregue_em.is_(None),
    ).all()
    for aviso in avisos:
        aviso.entregue_em = agora
    # A sessão da API não faz autoflush: sem isso, a busca dos pendentes ainda veria o aviso.
    db.flush()
    return len(avisos)


def pendentes(db: Session, aparelho) -> list[dict]:
    """Avisos ainda não confirmados do dono deste celular. Voltam até serem confirmados ou vencerem."""
    if (aparelho.app_versao or 0) < VERSAO_MINIMA_AVISOS:
        return []
    agora = datetime.now(timezone.utc)
    lista = (
        db.query(AvisoApp)
        .filter(
            AvisoApp.child_user_id == _dono(aparelho),
            AvisoApp.family_id == aparelho.family_id,
            AvisoApp.entregue_em.is_(None),
        )
        .order_by(AvisoApp.id.asc())
        .all()
    )
    saida = []
    for aviso in lista:
        if _como_utc(aviso.expira_em) < agora:
            db.delete(aviso)
            continue
        if len(saida) < MAX_POR_ENTREGA:
            item = {
                "id": aviso.id,
                "tipo": aviso.tipo,
                "titulo": aviso.titulo,
                "texto": aviso.texto,
                "url": aviso.url,
            }
            # App 2.0.9+: toca como alarme. Versões antigas ignoram os campos e só notificam.
            if aviso.som:
                item["som"] = aviso.som
                item["volume"] = aviso.volume or "medio"
            saida.append(item)
    return saida


def atualizar_e_entregar(db: Session, aparelho, versao: Optional[int], notificacoes: Optional[bool], recebidos: Iterable[int]) -> list[dict]:
    """Registra o que o app informou, confirma o que ele já mostrou e devolve o que falta."""
    if versao is not None:
        aparelho.app_versao = versao
    if notificacoes is not None:
        aparelho.notificacoes_ativas = notificacoes
    confirmar(db, aparelho, recebidos)
    saida = pendentes(db, aparelho)
    db.commit()
    return saida


def limpar_antigos(db: Session, dias: int = 7) -> int:
    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    return db.query(AvisoApp).filter(AvisoApp.created_at < corte).delete(synchronize_session=False)


# Primeira versão do app que toca o alarme (versionCode da 2.0.9).
VERSAO_MINIMA_ALARME = 13


class SemCelularDeAdulto(Exception):
    """O adulto logado não tem celular com o app conectado como adulto."""


def testar_alarme_no_adulto(db: Session, adulto: User, som: str, volume: str) -> dict:
    """Teste do alarme SÓ no celular do próprio adulto logado.

    Não consulta filhos nem celulares de criança: o destinatário é sempre `adulto`,
    e o aviso só é entregue a celulares cujo dono é esse usuário (ver `pendentes`).
    """
    from app.models.app_android import AppDispositivoAdulto

    if adulto.is_child:
        raise SemCelularDeAdulto("Só um adulto pode testar o alarme.")
    aparelhos = db.query(AppDispositivoAdulto).filter(
        AppDispositivoAdulto.user_id == adulto.id,
        AppDispositivoAdulto.family_id == adulto.family_id,
        AppDispositivoAdulto.revoked_at.is_(None),
    ).all()
    if not aparelhos:
        raise SemCelularDeAdulto(
            "Nenhum celular seu está conectado ao app como adulto. Entre no app Gestão Familiar com a sua conta e tente de novo."
        )
    aviso = enfileirar(
        db, adulto, "Teste do alarme", "Se você ouviu o som, o alarme do lembrete está funcionando.",
        url=None, tipo="teste_alarme", validade=timedelta(hours=1), som=som, volume=volume,
    )
    db.commit()
    return {
        "aviso_id": aviso.id,
        "aparelhos": len(aparelhos),
        "precisa_atualizar": not any((a.app_versao or 0) >= VERSAO_MINIMA_ALARME for a in aparelhos),
    }
