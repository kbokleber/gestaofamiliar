"""Envio de erros para o GlitchTip (logs.kbosolucoes.com.br), sem dados pessoais.

O sistema guarda dados de crianças (nome, saúde, localização). Por isso o filtro não tenta adivinhar
o que é sensível: ele REMONTA o evento só com o que está na lista permitida. Campo novo do SDK, texto
do erro, URL, cabeçalho, corpo, usuário, variável local ou log não sai, porque não está na lista.

Desligado quando GF_SENTRY_DSN_BACKEND está vazia: o SDK nem é importado.
"""
import builtins
import logging
import re
import sys
from functools import lru_cache
from types import ModuleType
from typing import Any, Optional

logger = logging.getLogger(__name__)

SEM_TEXTO = "[texto removido]"
MAX_CAUSAS = 10
# Teste de ponta a ponta (GF_SENTRY_TESTE=1): o único texto de erro que sai, e só igual a este, letra por letra.
MENSAGEM_DE_TESTE = "TESTE-GLITCHTIP (pode ignorar)"


class ErroDeTesteGlitchTip(Exception):
    """Erro provocado de propósito, com mensagem fixa. Não aceita texto de fora."""

    def __init__(self) -> None:
        super().__init__(MENSAGEM_DE_TESTE)


_NIVEIS = {"fatal", "error", "warning", "info", "debug"}
_METODOS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
_MECANISMOS = {"generic", "chained", "starlette", "fastapi", "logging", "excepthook", "threading"}
_FUNCOES_DO_PYTHON = {"<module>", "<lambda>", "<listcomp>", "<dictcomp>", "<setcomp>", "<genexpr>"}
# Loggers conhecidos que não têm o nome de um módulo.
_LOGGERS_CONHECIDOS = {"uvicorn.error"}

# Primeira triagem, só pelo formato. Uma palavra qualquer ("Guilhermina") também tem formato de nome,
# por isso cada campo ainda precisa EXISTIR no código carregado (funções _modulo, _tipo, _funcao...).
_CODIGO = re.compile(r"[A-Za-z_<][\w.<>]{0,119}", re.ASCII)
_ARQUIVO = re.compile(r"(?:[A-Za-z_]\w{0,59}/){0,12}[A-Za-z_]\w{0,59}\.py", re.ASCII)
_VERSAO = re.compile(r"[\w.@+\-]{1,80}", re.ASCII)
_ID = re.compile(r"[0-9a-f]{32}")
_MOMENTO = re.compile(r"20[0-9]{2}-[01][0-9]-[0-3][0-9]T[0-2][0-9]:[0-5][0-9]:[0-6][0-9](?:\.[0-9]{1,6})?(?:Z|\+00:00)")
_DEFINICAO = re.compile(r"\b(?:def|class)\s+([A-Za-z_]\w*)", re.ASCII)

# Ambiente e versão configurados ao ligar: só estes valores saem.
_identidade: dict = {}


def _texto(valor: Any, formato: re.Pattern) -> Optional[str]:
    return valor if isinstance(valor, str) and formato.fullmatch(valor) else None


def _inteiro(valor: Any) -> Optional[int]:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) and 0 <= valor < 1_000_000 else None


def _limpo(dados: dict) -> dict:
    return {chave: valor for chave, valor in dados.items() if valor is not None}


# ---------------------------------------------------------------- só o que existe no código carregado

def _modulo(nome: Any) -> Optional[str]:
    nome = _texto(nome, _CODIGO)
    return nome if nome and isinstance(sys.modules.get(nome), ModuleType) else None


def _arquivo_do_modulo(modulo: str) -> str:
    arquivo = vars(sys.modules[modulo]).get("__file__")
    return arquivo if isinstance(arquivo, str) else ""


@lru_cache(maxsize=1024)
def _definicoes(modulo: str) -> frozenset:
    """Nomes de funções e classes escritos no arquivo do módulo."""
    arquivo = _arquivo_do_modulo(modulo)
    if not arquivo.endswith(".py"):
        return frozenset()
    try:
        with open(arquivo, encoding="utf-8") as f:
            return frozenset(_DEFINICAO.findall(f.read()))
    except (OSError, UnicodeDecodeError):
        return frozenset()


def _arquivo(modulo: Optional[str], nome: Any) -> Optional[str]:
    nome = _texto(nome, _ARQUIVO)
    if not nome or not modulo:
        return None
    return nome if f"/{_arquivo_do_modulo(modulo)}".replace("\\", "/").endswith(f"/{nome}") else None


def _funcao(modulo: Optional[str], nome: Any) -> Optional[str]:
    nome = _texto(nome, _CODIGO)
    if not nome or not modulo:
        return None
    return nome if nome in _FUNCOES_DO_PYTHON or nome in _definicoes(modulo) else None


def _tipo(modulo: Any, nome: Any) -> str:
    """Nome da classe da exceção, se ela existir no módulo informado. Classe criada na hora vira "Erro"."""
    nome = _texto(nome, _CODIGO)
    if not nome:
        return "Erro"
    if modulo is None or modulo == "builtins":
        alvo: Any = builtins
    else:
        existente = _modulo(modulo)
        if not existente:
            return "Erro"
        alvo = sys.modules[existente]
    for parte in nome.split("."):
        if not isinstance(alvo, (ModuleType, type)):
            return "Erro"
        # vars() não dispara __getattr__ de ninguém.
        alvo = vars(alvo).get(parte)
    return nome if isinstance(alvo, type) and issubclass(alvo, BaseException) else "Erro"


def _quadro(quadro: Any) -> Optional[dict]:
    """Onde o erro passou: arquivo, função e linha. Sem variáveis locais e sem o texto do código."""
    if not isinstance(quadro, dict):
        return None
    modulo = _modulo(quadro.get("module"))
    return _limpo({
        "filename": _arquivo(modulo, quadro.get("filename")),
        "module": modulo,
        "function": _funcao(modulo, quadro.get("function")),
        "lineno": _inteiro(quadro.get("lineno")),
        "in_app": quadro.get("in_app") if isinstance(quadro.get("in_app"), bool) else None,
    })


def _excecao(valor: Any) -> Optional[dict]:
    if not isinstance(valor, dict):
        return None
    pilha = valor.get("stacktrace")
    quadros = pilha.get("frames") if isinstance(pilha, dict) else None
    mecanismo = valor.get("mechanism") if isinstance(valor.get("mechanism"), dict) else {}
    origem = mecanismo.get("type")
    saida = _limpo({
        "type": _tipo(valor.get("module"), valor.get("type")),
        "module": _modulo(valor.get("module")),
    })
    # A mensagem pode trazer nome, coordenada ou os valores de um INSERT: nunca vai.
    # A única exceção é a mensagem fixa do erro de teste, comparada por inteiro.
    de_teste = (
        saida["type"] == ErroDeTesteGlitchTip.__name__ and saida.get("module") == __name__
        and valor.get("value") == MENSAGEM_DE_TESTE
    )
    saida["value"] = MENSAGEM_DE_TESTE if de_teste else SEM_TEXTO
    saida["mechanism"] = _limpo({
        "type": origem if isinstance(origem, str) and origem in _MECANISMOS else "generic",
        "handled": mecanismo.get("handled") if isinstance(mecanismo.get("handled"), bool) else None,
    })
    if isinstance(quadros, list):
        saida["stacktrace"] = {"frames": [q for q in (_quadro(item) for item in quadros[-80:]) if q]}
    return saida


def _lista_de_excecoes(evento: dict) -> tuple[list, int]:
    """As últimas exceções da cadeia (a última é a que chegou ao fim) e quantas foram cortadas."""
    bruto = evento.get("exception")
    valores = bruto.get("values") if isinstance(bruto, dict) else bruto
    if not isinstance(valores, list):
        return [], 0
    cortadas = max(0, len(valores) - MAX_CAUSAS)
    return [e for e in (_excecao(item) for item in valores[-MAX_CAUSAS:]) if e], cortadas


def _rota(evento: dict) -> Optional[str]:
    """Nome da função da rota (ex.: app.api...listar_sos). URL com valores (source "url") nunca vai."""
    info = evento.get("transaction_info")
    if not isinstance(info, dict) or info.get("source") != "component":
        return None
    nome = _texto(evento.get("transaction"), _CODIGO)
    if not nome:
        return None
    partes = nome.split(".")
    for corte in range(len(partes) - 1, 0, -1):
        modulo = _modulo(".".join(partes[:corte]))
        if modulo:
            resto = [parte for parte in partes[corte:] if parte != "<locals>"]
            return nome if all(parte in _definicoes(modulo) for parte in resto) else None
    return None


def _logger(nome: Any) -> Optional[str]:
    if isinstance(nome, str) and nome in _LOGGERS_CONHECIDOS:
        return nome
    return _modulo(nome)


def _origem_do_log(dica: Any) -> Optional[str]:
    """Onde o logger.error foi chamado (função e linha). O texto do log não é lido."""
    registro = dica.get("log_record") if isinstance(dica, dict) else None
    nome = _logger(getattr(registro, "name", None))
    if nome is None:
        return None
    funcao = _funcao(_modulo(nome), getattr(registro, "funcName", None)) or "?"
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
    excecoes, cortadas = _lista_de_excecoes(evento)
    pedido = evento.get("request") if isinstance(evento.get("request"), dict) else {}
    metodo = pedido.get("method") if pedido.get("method") in _METODOS else None
    saida = _limpo({
        "event_id": _texto(evento.get("event_id"), _ID),
        "timestamp": _texto(evento.get("timestamp"), _MOMENTO),
        "platform": "python",
        "level": evento.get("level") if evento.get("level") in _NIVEIS else "error",
        "environment": _identidade.get("environment"),
        "release": _identidade.get("release"),
        "logger": _logger(evento.get("logger")),
        "transaction": _rota(evento),
    })
    saida["tags"] = _limpo({
        "servico": "gf-backend", "metodo": metodo,
        # Aviso de que a cadeia de causas foi cortada: só a quantidade.
        "causas_cortadas": str(cortadas) if cortadas else None,
    })
    if cortadas:
        logger.warning("Monitoramento: %s causas encadeadas cortadas do evento", cortadas)
    if excecoes:
        saida["exception"] = {"values": excecoes}
    else:
        saida["message"] = _origem_do_log(dica) or SEM_TEXTO
    return saida


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
        _identidade.update(
            environment=_texto(ambiente, _VERSAO) or "production",
            release=f"gf-backend@{_texto(commit, _VERSAO) or 'desconhecido'}",
        )
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
            **_identidade,
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
