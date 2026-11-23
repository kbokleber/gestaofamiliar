"""Rota de teste do GlitchTip: o app de verdade, com login de verdade e um GlitchTip falso recebendo os bytes."""
import json
import os
import subprocess
import sys

import pytest

from app.core import monitoramento as m
from tests.test_monitoramento import BACKEND, SEGREDOS, GlitchTipFalso, _sem_segredos

ROTA = "/api/v1/system/teste-glitchtip"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
NAVEGADOR = "Mozilla/5.0 (segredo-do-navegador)"

# Banco em memória com um usuário de cada tipo; a autenticação não é trocada.
PROGRAMA = r"""
import json, sys
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import app.main
from app.db.base import Base, get_db
from app.models.user import User

pedidos, segredos = json.loads(sys.argv[1]), json.loads(sys.argv[2])
engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(bind=engine)
db = sessionmaker(bind=engine)()
agora = datetime.now(timezone.utc)
def usuario(i, nome, **extra):
    return User(id=i, username=nome, password="x", email=segredos["email"], first_name=segredos["nome"], last_name=segredos["sobrenome"],
                **{"is_active": True, "is_staff": False, "is_superuser": False, "is_child": False, "date_joined": agora, "api_token": "tok-" + nome, **extra})
db.add_all([usuario(1, "admin", is_superuser=True), usuario(2, "equipe", is_staff=True), usuario(3, "adulto"),
            usuario(4, "crianca", is_child=True), usuario(5, "inativo", is_superuser=True, is_active=False)])
db.commit()
def _db():
    yield db
app.main.app.dependency_overrides[get_db] = _db
cliente = TestClient(app.main.app, raise_server_exceptions=False)
saida = []
for metodo, quem in pedidos:
    cab = {"User-Agent": segredos["ua"], "X-Forwarded-For": segredos["ip"], "X-Real-IP": segredos["ip"], "Cookie": "s=" + segredos["cookie"],
           "Referer": "https://x/?nome=" + segredos["nome"], "baggage": "sentry-release=" + segredos["bagagem"]}
    if quem == "lixo":
        cab["Authorization"] = "Bearer " + segredos["token"]
    elif quem:
        cab["X-API-Token"] = "tok-" + quem
    r = cliente.request(metodo, "/api/v1/system/teste-glitchtip?nome=" + segredos["nome"], headers=cab,
                        **({"json": {"mensagem": segredos["nome"]}} if metodo == "POST" else {}))
    saida.append([r.status_code, r.text])
rota = "/api/v1/system/teste-glitchtip"
print("SAIDA" + json.dumps({"respostas": saida, "rotas": [r.path for r in app.main.app.routes].count(rota),
                            "documentada": rota in app.main.app.openapi()["paths"]}))
if "sentry_sdk" in sys.modules:
    sys.modules["sentry_sdk"].flush(timeout=5)
"""


@pytest.fixture
def rodar(tmp_path):
    falso = GlitchTipFalso()

    def _rodar(pedidos, ligado="1", **variaveis):
        ambiente = {k: v for k, v in os.environ.items() if "SENTRY" not in k and "COMMIT" not in k and not k.startswith("APP_")}
        ambiente.update(DATABASE_URL="postgresql://u:p@localhost/db", SECRET_KEY="x", PYTHONPATH=str(BACKEND),
                        GF_SENTRY_DSN_BACKEND=falso.dsn, SOURCE_COMMIT=COMMIT, **variaveis)
        if ligado is not None:
            ambiente["GF_SENTRY_TESTE"] = ligado
        r = subprocess.run([sys.executable, "-c", PROGRAMA, json.dumps(pedidos), json.dumps({**SEGREDOS, "ua": NAVEGADOR})],
                           cwd=tmp_path, env=ambiente, capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr[-1500:]
        resultado = json.loads(r.stdout.split("SAIDA", 1)[1].splitlines()[0])
        return resultado, falso

    yield _rodar
    falso.servidor.shutdown()
    falso.servidor.server_close()


def _eventos(falso):
    saida = []
    for corpo in falso.corpos:
        linhas = [linha for linha in corpo.split(b"\n") if linha]
        saida += [json.loads(linhas[i + 1]) for i in range(1, len(linhas) - 1, 2)]
    return saida


@pytest.mark.parametrize("valor", [None, "", "0", "true", "sim", " 1", "11"])
def test_sem_a_variavel_a_rota_nao_existe_nem_para_o_administrador(rodar, valor):
    resultado, falso = rodar([["GET", "admin"], ["POST", "admin"], ["POST", None]], ligado=valor)
    assert [status for status, _ in resultado["respostas"]] == [404, 404, 404]
    assert resultado["rotas"] == 0
    assert falso.corpos == []


def test_so_administrador_ativo_dispara(rodar):
    quem = [None, "lixo", "nao-existe", "inativo", "equipe", "adulto", "crianca"]
    resultado, falso = rodar([[metodo, q] for q in quem for metodo in ("GET", "POST")])
    assert [status for status, _ in resultado["respostas"]] == [401] * 8 + [403] * 6
    assert falso.corpos == []


def test_consultar_nao_gera_erro_e_a_rota_nao_aparece_na_documentacao(rodar):
    resultado, falso = rodar([["GET", "admin"]])
    status, texto = resultado["respostas"][0]
    assert status == 200 and json.loads(texto) == {"ligado": True, "commit": COMMIT[:7]}
    assert resultado["rotas"] == 2 and resultado["documentada"] is False
    assert falso.corpos == []


@pytest.mark.parametrize("ambiente,esperado", [({}, "production"), ({"GF_SENTRY_ENVIRONMENT": "homologacao"}, "homologacao")])
def test_erro_de_teste_chega_com_versao_ambiente_e_mensagem_fixa_sem_dado_pessoal(rodar, ambiente, esperado):
    resultado, falso = rodar([["POST", "admin"]], **ambiente)
    assert resultado["respostas"][0][0] == 500
    eventos = _eventos(falso)
    assert len(eventos) == 1, eventos
    evento = eventos[0]
    assert evento["release"] == f"gf-backend@{COMMIT[:7]}"
    assert evento["environment"] == esperado
    assert evento["tags"] == {"servico": "gf-backend", "metodo": "POST"}
    assert evento["transaction"] == "app.api.v1.endpoints.teste_glitchtip.gerar_erro_de_teste"
    excecoes = evento["exception"]["values"]
    # O middleware de log pode embrulhar o erro num ExceptionGroup; o último da lista é o que dá título ao evento.
    assert {k: excecoes[-1][k] for k in ("type", "module", "value")} == {
        "type": "ErroDeTesteGlitchTip", "module": "app.core.monitoramento", "value": "TESTE-GLITCHTIP (pode ignorar)"}
    assert [(e["type"], e["value"]) for e in excecoes[:-1]] in ([], [("ExceptionGroup", m.SEM_TEXTO)])
    quadro = excecoes[-1]["stacktrace"]["frames"][-1]
    assert quadro["filename"].endswith("endpoints/teste_glitchtip.py") and quadro["function"] == "gerar_erro_de_teste"
    # Conteúdo sem IP, sem User-Agent e sem usuário; nem o que veio no pedido.
    assert not {"user", "request", "contexts", "server_name", "breadcrumbs", "extra"} & set(evento)
    _sem_segredos(falso.tudo())
    for proibido in (NAVEGADOR, "Mozilla", "tok-admin", "127.0.0.1", "testclient"):
        assert proibido not in b"\n".join(falso.corpos).decode()
    # User-Agent da conexão: o do SDK do servidor, nunca o de quem chamou. Nenhum cabeçalho leva IP.
    cabecalhos = "\n".join(falso.cabecalhos)
    assert "sentry.python" in cabecalhos and "Mozilla" not in cabecalhos and "forwarded" not in cabecalhos.lower()


# ---------------------------------------------------------------- a exceção do filtro não abre brecha

def _valor(**campos):
    base = {"type": "ErroDeTesteGlitchTip", "module": "app.core.monitoramento", "value": m.MENSAGEM_DE_TESTE}
    return m.filtrar_evento({"exception": {"values": [{**base, **campos}]}})["exception"]["values"][0]["value"]


def test_mensagem_fixa_so_passa_inteira_e_no_tipo_certo():
    assert _valor() == m.MENSAGEM_DE_TESTE
    for campos in ({"value": m.MENSAGEM_DE_TESTE + " Guilhermina"}, {"value": "Guilhermina " + m.MENSAGEM_DE_TESTE},
                   {"value": m.MENSAGEM_DE_TESTE + "\n"}, {"value": m.MENSAGEM_DE_TESTE.lower()}, {"value": "Guilhermina"},
                   {"value": None}, {"value": [m.MENSAGEM_DE_TESTE]}, {"type": "ValueError", "module": None},
                   {"module": None}, {"module": "builtins"}, {"module": "Guilhermina"}, {"type": "Guilhermina"}):
        assert _valor(**campos) == m.SEM_TEXTO, campos


def test_erro_de_teste_nao_aceita_texto_de_fora():
    assert str(m.ErroDeTesteGlitchTip()) == "TESTE-GLITCHTIP (pode ignorar)"
    with pytest.raises(TypeError):
        m.ErroDeTesteGlitchTip("Guilhermina")
