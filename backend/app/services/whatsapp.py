"""Envia o aviso de atividade concluída para a URL configurada na família."""
import logging
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.models.estudo import Atividade
from app.models.whatsapp import FamilyWhatsAppConfig

logger = logging.getLogger(__name__)


def texto_conclusao(atividade: Atividade) -> str:
    aluno = atividade.aluno
    nome = (getattr(aluno, "first_name", None) or "").strip() or getattr(aluno, "username", None) or "O filho"
    titulo = " ".join((atividade.titulo or "atividade").split())
    return f"{nome} marcou a tarefa {titulo} como concluída"


async def avisar_atividade_concluida(db: Session, atividade: Atividade) -> None:
    """Avisa o grupo. Uma falha aqui não desfaz a conclusão da atividade."""
    config = (
        db.query(FamilyWhatsAppConfig)
        .filter(FamilyWhatsAppConfig.family_id == atividade.family_id)
        .first()
    )
    if config is None or not config.enabled:
        return
    url = (config.url or "").strip()
    numero = (config.destino or "").strip()
    if not url or not numero:
        return
    partes = urlparse(url)
    if partes.scheme not in {"http", "https"} or not partes.netloc:
        logger.warning("WhatsApp da família %s ignorado: URL inválida", atividade.family_id)
        return
    corpo = {
        "mensagem": texto_conclusao(atividade),
        "numero": numero,
    }
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=False) as cliente:
            resposta = await cliente.post(url, json=corpo)
        if resposta.status_code >= 400:
            logger.warning("WhatsApp da família %s respondeu %s", atividade.family_id, resposta.status_code)
    except httpx.HTTPError:
        logger.warning("WhatsApp da família %s não respondeu", atividade.family_id)
