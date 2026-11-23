"""Envio de erros para o GlitchTip (logs.kbosolucoes.com.br), sem dados pessoais.

O sistema guarda dados de crianças (nome, saúde, localização). Por isso o filtro não tenta adivinhar
o que é sensível: ele REMONTA o evento só com o que está na lista permitida. Campo novo do SDK, texto
do erro, URL, cabeçalho, corpo, usuário, variável local ou log não sai, porque não está na lista.

Desligado quando GF_SENTRY_DSN_BACKEND está vazia: o SDK nem é importado.
"""
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

SEM_TEXTO = "[texto removido]"

_NIVEIS = {"fatal", "error", "warning", "info", "debug"}
# Identificadores de código (tipos, funções, módulos): nunca texto livre.
_CODIGO = re.compile(r"^[A-Za-z_<][\w.<>]{0,119}$")
_ARQUIVO = re.compile(r"^[\w./\-]{1,200}$")
_VERSAO = re.compile(r"^[\w.@+\-]{1,80}$")
_ID = re.compile(r"^[0-9a-f]{32}$")
_MECANISMO = re.compile(r"^[a-z_]{1,40}$")
_METODOS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}


def _texto(valor: Any, formato: re.Pattern) -> Optional[str]:
    return valor if isinstance(valor, str) and formato.fullmatch(valor) else None


def _inteiro(valor: Any) -> Optional[int]:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) and 0 <= valor < 10_000_000 else None


def _limpo(dados: dict) -> dict:
    return {chave: valor for chave, valor in dados.items() if valor is not None}


def _quadro(quadro: Any) -> Optional[dict]:
    """Onde o erro passou: arquivo, função e linha. Sem variáveis locais e sem o texto do código."""
    if not isinstance(quadro, dict):
        return None
    return _limpo({
        "filename": _texto(quadro.get("filename"), _ARQUIVO),
        "module": _texto(quadro.get("module"), _CODIGO),
        "function": _texto(quadro.get("function"), _CODIGO),
        "lineno": _inteiro(quadro.get("lineno")),
        "in_app": quadro.get("in_app") if isinstance(quadro.get("in_app"), bool) else None,
    })


def _excecao(valor: Any) -> Optional[dict]:
    if not isinstance(valor, dict):
        return None
    pilha = valor.get("stacktrace")
    quadros = pilha.get("frames") if isinstance(pilha, dict) else None
    mecanismo = valor.get("mechanism") if isinstance(valor.get("mechanism"), dict) else {}
    saida = _limpo({
        "type": _texto(valor.get("type"), _CODIGO) or "Erro",
        "module": _texto(valor.get("module"), _CODIGO),
    })
    # A mensagem pode trazer nome, coordenada ou os valores de um INSERT: nunca vai.
    saida["value"] = SEM_TEXTO
    saida["mechanism"] = _limpo({
        "type": _texto(mecanismo.get("type"), _MECANISMO) or "generic",
        "handled": mecanismo.get("handled") if isinstance(mecanismo.get("handled"), bool) else None,
    })
    if isinstance(quadros, list):
        saida["stacktrace"] = {"frames": [q for q in (_quadro(item) for item in quadros[-80:]) if q]}
    return saida


def _lista_de_excecoes(evento: dict) -> list:
    bruto = evento.get("exception")
    valores = bruto.get("values") if isinstance(bruto, dict) else bruto
    if not isinstance(valores, list):
        return []
    return [e for e in (_excecao(item) for item in valores[:10]) if e]


def _rota(evento: dict) -> Optional[str]:
    """Nome da função da rota (ex.: app.api...listar_sos). URL com valores (source "url") nunca vai."""
    info = evento.get("transaction_info")
    if not isinstance(info, dict) or info.get("source") != "component":
        return None
    return _texto(evento.get("transaction"), _CODIGO)


def _origem_do_log(dica: Any) -> Optional[str]:
    """Onde o logger.error foi chamado (função e linha). O texto do log não é lido."""
    registro = dica.get("log_record") if isinstance(dica, dict) else None
    nome = _texto(getattr(registro, "name", None), _CODIGO)
    if nome is None:
        return None
    funcao = _texto(getattr(registro, "funcName", None), _CODIGO) or "?"
    linha = _inteiro(getattr(registro, "lineno", None))
    return f"log de erro em {nome}.{funcao}:{linha if linha is not None else '?'}"


def filtrar_evento(evento: Any, dica: Any = None) -> Optional[dict]:
    """before_send: devolve um evento NOVO só com o permitido. Qualquer falha aqui descarta o evento."""
    try:
        return _filtrar(evento, dica)
    except Exception:
        return None


def _filtrar(evento: Any, dica: Any) -> Optional[dict]:
    if not isinstance(evento, dict):
        return None
    # Transações, check-ins e afins têm "type"; aqui só passa erro.
    if evento.get("type"):
        return None
    excecoes = _lista_de_excecoes(evento)
    momento = evento.get("timestamp")
    pedido = evento.get("request") if isinstance(evento.get("request"), dict) else {}
    metodo = pedido.get("method") if pedido.get("method") in _METODOS else None
    saida = _limpo({
        "event_id": _texto(evento.get("event_id"), _ID),
        "timestamp": momento if _e_momento(momento) else None,
        "platform": "python",
        "level": evento.get("level") if evento.get("level") in _NIVEIS else "error",
        "environment": _texto(evento.get("environment"), _VERSAO),
        "release": _texto(evento.get("release"), _VERSAO),
        "logger": _texto(evento.get("logger"), _CODIGO),
        "transaction": _rota(evento),
    })
    saida["tags"] = _limpo({"servico": "gf-backend", "metodo": metodo})
    if excecoes:
        saida["exception"] = {"values": excecoes}
    else:
        saida["message"] = _origem_do_log(dica) or SEM_TEXTO
    return saida


def _e_momento(valor: Any) -> bool:
    from datetime import datetime

    if isinstance(valor, (datetime, float)):
        return True
    return isinstance(valor, str) and re.fullmatch(r"[\dTZ:.+\-]{10,40}", valor) is not None


def _nada(*_args, **_kwargs):
    """Transações, logs e métricas: desligados; se algum escapar, é descartado."""
    return None


def _transporte_sem_rastro():
    from sentry_sdk.transport import HttpTransport

    class TransporteSoErros(HttpTransport):
        """Última barreira: só deixa sair envelope de erro, sem o cabeçalho de rastreio
        (que pode carregar dados vindos do cabeçalho "baggage" de quem chamou a API)."""

        def capture_envelope(self, envelope):
            if any(item.headers.get("type") != "event" for item in envelope.items):
                return
            envelope.headers.pop("trace", None)
            super().capture_envelope(envelope)

    return TransporteSoErros


def iniciar_monitoramento(dsn: Optional[str], ambiente: str, commit: str, **opcoes_de_teste) -> bool:
    """Liga o envio de erros. Sem DSN, com DSN inválido ou com falha do SDK, o app segue sem ele."""
    dsn = (dsn or "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.atexit import AtexitIntegration
        from sentry_sdk.integrations.dedupe import DedupeIntegration
        from sentry_sdk.integrations.excepthook import ExcepthookIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
        from sentry_sdk.integrations.threading import ThreadingIntegration

        sentry_sdk.init(**{
            "dsn": dsn,
            "environment": _texto(ambiente, _VERSAO) or "production",
            "release": f"gf-backend@{_texto(commit, _VERSAO) or 'desconhecido'}",
            "server_name": "gf-backend",
            # Só as integrações desta lista: nada de SQL, HTTP de saída, argumentos ou módulos instalados.
            "default_integrations": False,
            "auto_enabling_integrations": False,
            "integrations": [
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=None, event_level=logging.ERROR),
                ExcepthookIntegration(),
                ThreadingIntegration(propagate_scope=False),
                DedupeIntegration(),
                AtexitIntegration(callback=_nada),
            ],
            "send_default_pii": False,
            "include_local_variables": False,
            "include_source_context": False,
            "max_request_body_size": "never",
            "max_breadcrumbs": 0,
            "attach_stacktrace": False,
            "traces_sample_rate": None,
            "trace_propagation_targets": [],
            "auto_session_tracking": False,
            "send_client_reports": False,
            "enable_logs": False,
            "enable_metrics": False,
            "spotlight": False,
            "debug": False,
            "before_send": filtrar_evento,
            "before_send_transaction": _nada,
            "before_breadcrumb": _nada,
            "before_send_log": _nada,
            "before_send_metric": _nada,
            "transport": _transporte_sem_rastro(),
            **opcoes_de_teste,
        })
    except Exception as erro:
        # Só o tipo do erro: a mensagem pode trazer o próprio DSN.
        logger.warning("Monitoramento de erros desligado: falha ao iniciar (%s)", type(erro).__name__)
        return False
    logger.info("Monitoramento de erros ligado (ambiente=%s)", ambiente)
    return True
