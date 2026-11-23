"""GlitchTip sem dados pessoais. O servidor falso recebe os bytes que o SDK manda de verdade."""
import gzip
import json
import logging
import os
import subprocess
import sys
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import create_engine, text

from app.core import monitoramento as m

BACKEND = Path(__file__).resolve().parents[1]

# Tudo isto é plantado em todo lugar e não pode aparecer em nenhum byte enviado.
SEGREDOS = {
    "nome": "Guilhermina-Segredo",
    "sobrenome": "Zacarias",
    "email": "crianca.segredo@example.com",
    "latitude": "-23.987654",
    "longitude": "-46.123987",
    "token": "eyJhbGciOiJIUzI1NiJ9.segredo-jwt",
    "token_celular": "device-token-segredo-123",
    "api_token": "api-token-segredo-456",
    "cookie": "sessao-segredo-789",
    "telefone": "13999887766",
    "remedio": "Ritalinassegredo",
    "ip": "203.0.113.77",
    "bagagem": "bagagem-segredo",
}


class GlitchTipFalso:
    def __init__(self):
        self.corpos: list[bytes] = []
        self.cabecalhos: list[str] = []
        dono = self

        class Receptor(BaseHTTPRequestHandler):
            def do_POST(self):
                bruto = self.rfile.read(int(self.headers.get("Content-Length") or 0))
                codificacao = self.headers.get("Content-Encoding")
                if codificacao == "gzip":
                    bruto = gzip.decompress(bruto)
                elif codificacao == "br":
                    import brotli
                    bruto = brotli.decompress(bruto)
                elif codificacao == "deflate":
                    bruto = zlib.decompress(bruto)
                dono.corpos.append(bruto)
                dono.cabecalhos.append(str(self.headers))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *args):
                pass

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), Receptor)
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    @property
    def dsn(self):
        return f"http://chavepublica@127.0.0.1:{self.servidor.server_address[1]}/1"

    def eventos(self):
        import sentry_sdk

        sentry_sdk.flush(timeout=5)
        saida = []
        for corpo in self.corpos:
            linhas = [linha for linha in corpo.split(b"\n") if linha]
            for i in range(1, len(linhas) - 1, 2):
                saida.append((json.loads(linhas[i]).get("type"), json.loads(linhas[i + 1]), json.loads(linhas[0])))
        return saida

    def tudo(self):
        return b"\n".join(self.corpos).decode("utf-8") + "\n".join(self.cabecalhos)


@pytest.fixture
def glitchtip():
    import sentry_sdk

    falso = GlitchTipFalso()
    assert m.iniciar_monitoramento(falso.dsn, "teste", "abc1234") is True
    yield falso
    sentry_sdk.get_client().close(timeout=1)
    sentry_sdk.get_global_scope().set_client(None)
    falso.servidor.shutdown()
    falso.servidor.server_close()


def _sem_segredos(texto):
    for rotulo, valor in SEGREDOS.items():
        assert valor not in texto, f"vazou: {rotulo}"


# ---------------------------------------------------------------- desligado

@pytest.mark.parametrize("dsn", ["", None, "   "])
def test_sem_dsn_nao_inicializa(dsn, monkeypatch):
    import sentry_sdk

    monkeypatch.setattr(sentry_sdk, "init", lambda *a, **k: pytest.fail("não podia inicializar"))
    assert m.iniciar_monitoramento(dsn, "production", "abc") is False


def test_dsn_invalido_nao_quebra_o_app_nem_vai_para_o_log(caplog):
    caplog.set_level(logging.DEBUG)
    assert m.iniciar_monitoramento("isto-nao-e-dsn-segredo", "production", "abc") is False
    assert "segredo" not in caplog.text


def test_app_de_verdade_sobe_sem_dsn_e_sem_importar_o_sdk(tmp_path):
    codigo = "import app.main, sys; print('SDK' if 'sentry_sdk' in sys.modules else 'sem SDK', len(app.main.app.routes) > 50)"
    ambiente = {k: v for k, v in os.environ.items() if "SENTRY" not in k}
    ambiente.update(DATABASE_URL="postgresql://u:p@localhost/db", SECRET_KEY="x", PYTHONPATH=str(BACKEND))
    r = subprocess.run([sys.executable, "-c", codigo], cwd=tmp_path, env=ambiente, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-800:]
    assert r.stdout.strip().endswith("sem SDK True")


# ---------------------------------------------------------------- o que sai pela rede

class Crianca(BaseModel):
    nome: str
    remedio: str


def _app():
    app = FastAPI()

    @app.middleware("http")
    async def registrar(request, call_next):  # igual ao main.py: escreve a URL inteira no log
        logging.getLogger("app.main").info("[REQUEST] %s", request.url)
        return await call_next(request)

    @app.post("/api/v1/criancas/{nome}")
    def estourar(nome: str, corpo: Crianca, request: Request, lat: str = ""):
        local = {"nome": nome, "lat": lat, "jwt": request.headers.get("authorization")}
        raise ValueError(f"falha com {local} {corpo}")

    @app.post("/api/v1/banco/{nome}")
    def banco(nome: str, corpo: Crianca):
        motor = create_engine("sqlite://")
        with motor.begin() as c:
            c.execute(text("INSERT INTO nao_existe VALUES (:a, :b)"), {"a": nome, "b": corpo.remedio})

    @app.post("/api/v1/http500/{nome}")
    def http500(nome: str, corpo: Crianca):
        raise HTTPException(status_code=500, detail=f"{nome} {corpo.remedio}")

    @app.post("/api/v1/log/{nome}")
    def registra(nome: str, corpo: Crianca):
        logging.getLogger("app.services.teste").error(f"erro de {nome}: %s", corpo.remedio, extra={"paciente": nome})
        return {"ok": True}

    @app.post("/api/v1/encadeado/{nome}")
    def encadeado(nome: str, corpo: Crianca):
        try:
            raise KeyError(nome)
        except KeyError as erro:
            raise RuntimeError(corpo.remedio) from erro

    return app


def _chamar(caminho):
    s = SEGREDOS
    cliente = TestClient(_app(), raise_server_exceptions=False)
    return cliente.post(
        f"{caminho}/{s['nome']}?lat={s['latitude']}&lng={s['longitude']}&email={s['email']}",
        json={"nome": f"{s['nome']} {s['sobrenome']} {s['telefone']}", "remedio": s["remedio"]},
        headers={
            "Authorization": f"Bearer {s['token']}", "X-Device-Token": s["token_celular"],
            "X-API-Token": s["api_token"], "Cookie": f"s={s['cookie']}", "X-Forwarded-For": s["ip"],
            "User-Agent": f"App {s['nome']}", "Referer": f"https://site/{s['nome']}",
            "sentry-trace": "771a43a4192642f0b136d5159a501700-1234567890abcdef-1",
            "baggage": f"sentry-trace_id=771a43a4192642f0b136d5159a501700,sentry-transaction={s['bagagem']},"
                       f"sentry-user_id={s['nome']},outro={s['bagagem']}",
        },
    )


@pytest.mark.parametrize("caminho,tipo", [
    ("/api/v1/criancas", "ValueError"),
    ("/api/v1/banco", "OperationalError"),
    ("/api/v1/http500", "HTTPException"),
    ("/api/v1/encadeado", "RuntimeError"),
])
def test_erro_em_rota_chega_sem_dado_pessoal(glitchtip, caminho, tipo):
    import sentry_sdk

    sentry_sdk.set_user({"id": 16, "username": SEGREDOS["nome"], "email": SEGREDOS["email"], "ip_address": SEGREDOS["ip"]})
    sentry_sdk.set_tag("paciente", SEGREDOS["nome"])
    sentry_sdk.set_extra("posicao", SEGREDOS["latitude"])
    sentry_sdk.set_context("saude", {"remedio": SEGREDOS["remedio"]})
    sentry_sdk.add_breadcrumb(message=SEGREDOS["nome"])
    assert _chamar(caminho).status_code == 500
    eventos = glitchtip.eventos()
    assert len(eventos) == 1, [e[0] for e in eventos]
    tipo_item, evento, envelope = eventos[0]
    assert tipo_item == "event"
    # Útil para achar o erro: tipo, arquivo, função, linha, rota, versão e ambiente.
    excecoes = evento["exception"]["values"]
    assert excecoes[-1]["type"] == tipo
    assert {e["value"] for e in excecoes} == {m.SEM_TEXTO}
    quadros = excecoes[-1]["stacktrace"]["frames"]
    assert any(q["filename"].endswith("test_monitoramento.py") and q["lineno"] > 0 for q in quadros)
    assert evento["release"] == "gf-backend@abc1234" and evento["environment"] == "teste"
    assert evento["tags"] == {"servico": "gf-backend", "metodo": "POST"}
    assert evento["transaction"].startswith("tests.test_monitoramento._app") or "test_monitoramento" in evento["transaction"]
    # Só as chaves permitidas, em todos os níveis.
    assert set(evento) <= {"event_id", "timestamp", "platform", "level", "environment", "release",
                           "logger", "transaction", "tags", "exception"}
    for e in excecoes:
        assert set(e) <= {"type", "module", "value", "mechanism", "stacktrace"}
    for q in quadros:
        assert set(q) <= {"filename", "module", "function", "lineno", "in_app"}
    assert "trace" not in envelope
    _sem_segredos(glitchtip.tudo())


def test_logger_error_leva_so_o_lugar_e_nao_o_texto(glitchtip):
    assert _chamar("/api/v1/log").status_code == 200
    eventos = glitchtip.eventos()
    assert len(eventos) == 1
    evento = eventos[0][1]
    assert evento["logger"] == "app.services.teste"
    assert evento["message"].startswith("log de erro em app.services.teste.registra:")
    _sem_segredos(glitchtip.tudo())


def test_transacao_check_in_log_metrica_e_sessao_nao_saem(glitchtip):
    import sentry_sdk
    from sentry_sdk.envelope import Envelope, Item, PayloadRef

    with sentry_sdk.start_transaction(name=SEGREDOS["nome"], sampled=True):
        pass
    for tipo in ("transaction", "check_in", "log", "attachment", "statsd", "session", "feedback"):
        envelope = Envelope(headers={"event_id": "a" * 32})
        envelope.add_item(Item(payload=PayloadRef(json={"x": SEGREDOS["nome"]}), type=tipo))
        sentry_sdk.get_client().transport.capture_envelope(envelope)
    sentry_sdk.logger.error(SEGREDOS["nome"])
    assert glitchtip.eventos() == []
    assert glitchtip.corpos == []


def test_transporte_tira_o_cabecalho_de_rastreio_do_envelope(glitchtip):
    import sentry_sdk
    from sentry_sdk.envelope import Envelope

    envelope = Envelope(headers={"event_id": "a" * 32, "trace": {"transaction": SEGREDOS["bagagem"], "user_id": SEGREDOS["nome"]}})
    envelope.add_event({"event_id": "a" * 32})
    sentry_sdk.get_client().transport.capture_envelope(envelope)
    eventos = glitchtip.eventos()
    assert len(eventos) == 1 and "trace" not in eventos[0][2]
    _sem_segredos(glitchtip.tudo())


def test_anexo_junto_do_erro_faz_o_envelope_inteiro_ser_descartado(glitchtip):
    import sentry_sdk

    with sentry_sdk.new_scope() as escopo:
        escopo.add_attachment(bytes=SEGREDOS["nome"].encode(), filename="ficha.txt")
        sentry_sdk.capture_exception(ValueError("x"))
    glitchtip.eventos()
    _sem_segredos(glitchtip.tudo())


# ---------------------------------------------------------------- filtro, com evento montado à mão

def _evento_cheio():
    s = SEGREDOS
    sujo = " ".join(s.values())
    return {
        "event_id": "a" * 32, "timestamp": "2026-11-23T12:00:00.000000Z", "platform": sujo, "level": sujo,
        "environment": sujo, "release": sujo, "logger": sujo, "server_name": sujo, "dist": sujo,
        "transaction": f"/api/v1/criancas/{s['nome']}", "transaction_info": {"source": "url"},
        "user": {"id": 1, "email": s["email"], "ip_address": s["ip"]},
        "request": {"url": sujo, "method": sujo, "query_string": sujo, "headers": {"Authorization": s["token"]},
                    "cookies": s["cookie"], "data": {"nome": s["nome"]}, "env": {"REMOTE_ADDR": s["ip"]}},
        "breadcrumbs": {"values": [{"message": sujo}]}, "extra": {"a": sujo}, "tags": {"a": sujo},
        "contexts": {"device": {"name": sujo}, "trace": {"data": sujo}}, "modules": {"a": sujo},
        "logentry": {"message": sujo, "params": [sujo], "formatted": sujo}, "message": sujo,
        "fingerprint": [sujo], "threads": {"values": [{"name": sujo}]}, "debug_meta": {"a": sujo},
        "campo_que_o_sdk_inventar_amanha": sujo,
        "exception": {"values": [{
            "type": sujo, "module": sujo, "value": sujo, "thread_id": sujo,
            "mechanism": {"type": sujo, "handled": False, "data": {"a": sujo}, "meta": sujo},
            "stacktrace": {"frames": [{
                "filename": f"app/{s['nome']} x.py", "abs_path": sujo, "function": sujo, "module": sujo, "lineno": sujo,
                "vars": {"senha": sujo}, "context_line": sujo, "pre_context": [sujo], "post_context": [sujo],
                "in_app": sujo, "campo_novo": sujo}]},
        }]},
    }


def test_filtro_remove_tudo_o_que_nao_esta_na_lista():
    saida = m.filtrar_evento(_evento_cheio(), {"log_record": None})
    _sem_segredos(json.dumps(saida, ensure_ascii=False))
    assert saida["level"] == "error" and saida["tags"] == {"servico": "gf-backend"}
    assert "transaction" not in saida


@pytest.mark.parametrize("evento", [None, "texto", 1, [], {"type": "transaction"}, {"type": "check_in"}])
def test_filtro_descarta_o_que_nao_e_erro(evento):
    assert m.filtrar_evento(evento, None) is None


@pytest.mark.parametrize("ruim", [
    {"exception": "Guilhermina-Segredo"}, {"exception": {"values": "Guilhermina-Segredo"}},
    {"exception": {"values": [None, 1, {"stacktrace": {"frames": "Guilhermina-Segredo"}, "mechanism": 3}]}},
    {"request": "Guilhermina-Segredo", "transaction_info": "Guilhermina-Segredo", "timestamp": {"a": "Guilhermina-Segredo"}},
])
def test_filtro_aguenta_formato_estranho(ruim):
    _sem_segredos(json.dumps(m.filtrar_evento(ruim, None)))


def test_se_o_filtro_falhar_o_evento_e_descartado(monkeypatch):
    monkeypatch.setattr(m, "_filtrar", lambda *a: 1 / 0)
    assert m.filtrar_evento({"exception": {}}, None) is None
