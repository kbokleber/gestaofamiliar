"""Escolhe as atividades e envia o alerta para o navegador do filho."""
import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.estudo import Atividade
from app.models.lembrete import FamilyLembreteConfig, PushInscricao
from app.models.user import User

logger = logging.getLogger(__name__)

FUSO = timezone(timedelta(hours=-3))
HORA_INICIO = 13
HORA_FIM = 21


def agora_local() -> datetime:
    return datetime.now(FUSO)


def dentro_da_janela(momento: datetime | None = None) -> bool:
    momento = momento or agora_local()
    minutos = momento.hour * 60 + momento.minute
    return HORA_INICIO * 60 <= minutos <= HORA_FIM * 60


def intervalo_em_segundos(config: FamilyLembreteConfig) -> int:
    fator = 60 if config.unidade == "minutos" else 3600
    return max(1, config.intervalo) * fator


def _dia_local(prazo: datetime) -> datetime.date:
    if prazo.tzinfo is None:
        prazo = prazo.replace(tzinfo=timezone.utc)
    return prazo.astimezone(FUSO).date()


def tarefas_para_lembrar(db: Session, aluno_id: int, hoje=None) -> list[Atividade]:
    """Pendências que vencem amanhã ou que já venceram. O prazo de hoje fica de fora."""
    hoje = hoje or agora_local().date()
    amanha = hoje + timedelta(days=1)
    atividades = db.query(Atividade).filter(
        Atividade.aluno_id == aluno_id,
        Atividade.tipo != "comunicado",
        Atividade.prazo_entrega.isnot(None),
        or_(Atividade.status.is_(None), Atividade.status != "concluida"),
    ).all()
    escolhidas = []
    for atividade in atividades:
        dia = _dia_local(atividade.prazo_entrega)
        if dia == amanha or dia < hoje:
            escolhidas.append(atividade)
    escolhidas.sort(key=lambda item: item.prazo_entrega)
    return escolhidas


def _texto(atividades: list[Atividade]) -> str:
    titulos = [" ".join((item.titulo or "atividade").split()) for item in atividades[:8]]
    resto = len(atividades) - len(titulos)
    texto = "Amanhã ou atrasadas: " + "; ".join(titulos)
    if resto > 0:
        texto += f" e mais {resto}"
    return texto[:240]


def _chave_privada() -> str:
    from pathlib import Path
    valor = (settings.VAPID_PRIVATE_KEY or "").strip()
    if not valor:
        return ""
    caminho = Path(valor)
    if not caminho.is_file():
        caminho = Path(__file__).resolve().parents[2] / valor
    return str(caminho) if caminho.is_file() else valor


def chave_publica_vapid() -> str:
    if settings.VAPID_PUBLIC_KEY:
        return settings.VAPID_PUBLIC_KEY
    privada = _chave_privada()
    if not privada:
        return ""
    from pathlib import Path
    from base64 import urlsafe_b64encode
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from py_vapid import Vapid
    if Path(privada).is_file():
        vapid = Vapid.from_file(private_key_file=privada)
    else:
        vapid = Vapid.from_string(private_key=privada)
    bruto = vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    return urlsafe_b64encode(bruto).decode().rstrip("=")


def enviar_para_usuario(db: Session, usuario: User, atividades: list[Atividade]) -> int:
    inscricoes = db.query(PushInscricao).filter(PushInscricao.user_id == usuario.id).all()
    if not inscricoes or not atividades:
        return 0
    privada = _chave_privada()
    if not privada or not chave_publica_vapid():
        logger.warning("Chaves VAPID ausentes; lembrete não enviado.")
        return 0
    from pywebpush import WebPushException, webpush

    corpo = json.dumps({
        "title": "Atividades para concluir",
        "body": _texto(atividades),
        "url": "/estudos/atividades?recorte=pendentes",
    })
    enviados = 0
    for inscricao in inscricoes:
        try:
            webpush(
                subscription_info={
                    "endpoint": inscricao.endpoint,
                    "keys": {"p256dh": inscricao.p256dh, "auth": inscricao.auth},
                },
                data=corpo,
                vapid_private_key=privada,
                vapid_claims={"sub": settings.VAPID_SUBJECT},
            )
            enviados += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in {404, 410}:
                db.delete(inscricao)
            logger.warning("Falha ao avisar %s: %s", usuario.id, exc)
        except Exception:
            logger.warning("Falha ao avisar %s", usuario.id, exc_info=True)
    return enviados


def disparar_familia(db: Session, family_id: int) -> dict:
    """Envia agora, sem olhar o relógio nem o intervalo."""
    filhos = db.query(User).filter(
        User.family_id == family_id,
        User.is_child.is_(True),
        User.is_active.is_(True),
    ).all()
    enviados = []
    sem_tarefa = []
    sem_inscricao = []
    for filho in filhos:
        nome = (filho.first_name or "").strip() or filho.username
        atividades = tarefas_para_lembrar(db, filho.id)
        if not atividades:
            sem_tarefa.append(nome)
            continue
        quantidade = db.query(PushInscricao).filter(PushInscricao.user_id == filho.id).count()
        if quantidade == 0:
            sem_inscricao.append(nome)
            continue
        enviar_para_usuario(db, filho, atividades)
        enviados.append({
            "filho": nome,
            "tarefas": [item.titulo for item in atividades],
        })
    db.commit()
    return {"enviados": enviados, "sem_tarefa": sem_tarefa, "sem_inscricao": sem_inscricao}


def processar_lembretes_pendentes(db: Session) -> int:
    """Respeita a janela das 13h às 21h e o intervalo configurado."""
    if not dentro_da_janela():
        return 0
    agora = datetime.now(timezone.utc)
    configs = db.query(FamilyLembreteConfig).filter(FamilyLembreteConfig.enabled.is_(True)).all()
    disparos = 0
    for config in configs:
        if config.ultimo_envio is not None:
            decorrido = (agora - config.ultimo_envio).total_seconds()
            if decorrido < intervalo_em_segundos(config):
                continue
        config.ultimo_envio = agora
        family_id = config.family_id
        db.commit()
        disparar_familia(db, family_id)
        disparos += 1
    return disparos
