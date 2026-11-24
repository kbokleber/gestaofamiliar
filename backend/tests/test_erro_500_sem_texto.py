"""Resposta 5xx nunca leva o texto da exceção: frase fixa para o usuário, detalhe só no log do servidor."""
import ast
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  registra as tabelas usadas pelos relacionamentos
from app.api.deps import get_current_admin, get_current_family, get_current_user
from app.api.v1.endpoints import finance, healthcare, maintenance, telegram, users
from app.core.keycloak_admin import KeycloakAdminError
from app.db.base import Base, get_db
from app.models.family import Family
from app.models.finance import FinanceCategory, FinanceEntry
from app.models.healthcare import FamilyMember
from app.models.maintenance import Equipment, MaintenanceOrder
from app.models.telegram import FamilyAIConfig, FamilyTelegramConfig, TelegramUserLink
from app.models.user import User
from app.telegram import ai_service
from app.utils import file_response

APP = Path(__file__).resolve().parents[1] / "app"
SEGREDO = "Guilhermina-Segredo"
TEXTO = f"(psycopg2.errors.X) INSERT INTO t VALUES ('{SEGREDO}', -23.987654)"

# ---------------------------------------------------------------- 1) varredura do código

RESPOSTAS = {"HTTPException", "JSONResponse", "Response", "PlainTextResponse", "HTMLResponse", "ORJSONResponse",
             "UJSONResponse", "StarletteHTTPException"}
# Únicos casos sem frase fixa, por arquivo e função. Cada um foi conferido:
PERMITIDOS = {
    # Só mostra o texto com ENVIRONMENT=development (tests/test_ambiente.py).
    ("main.py", "global_exception_handler"),
    # Repassa um HTTPException nosso, com status e frase já escolhidos.
    ("api/v1/endpoints/estudos.py", "_processar_anexos_entrada"),
}


def _status(no):
    """Número do status, ou None quando não dá para saber lendo o código."""
    if isinstance(no, ast.Constant) and isinstance(no.value, int):
        return no.value
    nome = no.attr if isinstance(no, ast.Attribute) else no.id if isinstance(no, ast.Name) else ""
    partes = nome.split("_")
    return int(partes[1]) if len(partes) > 1 and partes[0] == "HTTP" and partes[1].isdigit() else None


def _fixo(no):
    """Texto escrito no código, sem nenhuma parte variável."""
    if no is None or isinstance(no, ast.Constant):
        return True
    if isinstance(no, ast.Dict):
        return all(_fixo(x) for x in [*no.keys, *no.values])
    if isinstance(no, (ast.List, ast.Tuple)):
        return all(_fixo(x) for x in no.elts)
    return False


def _nome(funcao):
    return funcao.attr if isinstance(funcao, ast.Attribute) else getattr(funcao, "id", "")


def problemas(codigo, arquivo="x.py"):
    achados = []

    def visitar(no, funcao):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcao = no.name
        if isinstance(no, ast.ImportFrom):
            for item in no.names:
                # Apelido esconderia a chamada da varredura.
                if item.name in RESPOSTAS and item.asname not in (None, item.name, "StarletteHTTPException"):
                    achados.append((no.lineno, f"{item.name} com apelido {item.asname}"))
        if isinstance(no, (ast.Assign, ast.AnnAssign)):
            alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
            if isinstance(no.value, ast.Name) and no.value.id in RESPOSTAS:
                achados.append((no.lineno, f"{no.value.id} guardado em outra variável"))
            if any(isinstance(a, ast.Attribute) and a.attr == "status_code" for a in alvos):
                s = _status(no.value)
                if (s is None or s >= 500) and (arquivo, funcao) not in {("core/keycloak_admin.py", "__init__")}:
                    achados.append((no.lineno, "status_code trocado depois da criação da resposta"))
        if isinstance(no, ast.Call) and _nome(no.func) in RESPOSTAS and (arquivo, funcao) not in PERMITIDOS:
            http = _nome(no.func).endswith("HTTPException")
            posicoes = ["status_code", "detail", "headers"] if http else ["content", "status_code", "headers"]
            args = dict(zip(posicoes, no.args))
            solto = any(isinstance(a, ast.Starred) for a in no.args)
            for k in no.keywords:
                solto = solto or k.arg is None
                args[k.arg] = k.value
            padrao = None if http else ast.Constant(200)
            status_no = args.pop("status_code", padrao)
            s = None if status_no is None or solto else _status(status_no)
            if s is None or s >= 500:
                if solto or not all(_fixo(v) for v in args.values()):
                    achados.append((no.lineno, "resposta 5xx (ou de status desconhecido) sem frase fixa"))
        for filho in ast.iter_child_nodes(no):
            visitar(filho, funcao)

    visitar(ast.parse(codigo), "")
    return achados


def test_nenhuma_resposta_5xx_do_app_tem_texto_variavel():
    achados = []
    for caminho in sorted(APP.rglob("*.py")):
        arquivo = caminho.relative_to(APP).as_posix()
        achados += [f"app/{arquivo}:{linha}: {motivo}" for linha, motivo in problemas(caminho.read_text(encoding="utf-8"), arquivo)]
    assert not achados, "\n".join(achados)


def test_a_varredura_le_mesmo_o_app():
    chamadas = sum(1 for p in APP.rglob("*.py") for no in ast.walk(ast.parse(p.read_text(encoding="utf-8")))
                   if isinstance(no, ast.Call) and _nome(no.func) in RESPOSTAS)
    assert chamadas > 100
    for arquivo, funcao in PERMITIDOS:
        nomes = {no.name for no in ast.walk(ast.parse((APP / arquivo).read_text(encoding="utf-8")))
                 if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef))}
        assert funcao in nomes, f"exceção sem uso: {arquivo}:{funcao}"


@pytest.mark.parametrize("trecho", [
    'raise HTTPException(status_code=500, detail=str(e))',
    'raise HTTPException(500, str(e))',
    'raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro: {e}")',
    'raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro: {str(e)}")',
    'raise HTTPException(status_code=HTTP_502_BAD_GATEWAY, detail="Erro: " + repr(e))',
    'raise HTTPException(status_code=503, detail="Erro: %s" % e)',
    'raise HTTPException(status_code=500, detail="Erro: {}".format(e))',
    'raise HTTPException(status_code=500, detail=e.args[0])',
    'raise HTTPException(status_code=500, detail={"erro": str(e)})',
    'raise HTTPException(status_code=500, detail=["x", str(e)])',
    'raise HTTPException(status_code=500, detail="x", headers={"X-Erro": str(e)})',
    'msg = str(e); raise HTTPException(status_code=500, detail=msg)',
    'raise HTTPException(status_code=500, detail=traceback.format_exc())',
    'raise HTTPException(status_code=codigo, detail=str(e))',
    'raise HTTPException(*partes)',
    'raise HTTPException(**partes)',
    'raise fastapi.HTTPException(500, str(e))',
    'return JSONResponse({"detail": str(e)}, 500)',
    'return JSONResponse(status_code=500, content={"detail": str(e)})',
    'return PlainTextResponse(str(e), status_code=500)',
    'return Response(content=str(e), status_code=500)',
    'from fastapi import HTTPException as H',
    'H = HTTPException',
    'response.status_code = 500',
    'response.status_code = codigo',
])
def test_a_varredura_pega_as_formas_de_vazar(trecho):
    assert problemas(trecho), trecho


@pytest.mark.parametrize("trecho", [
    'raise HTTPException(status_code=500, detail="Erro ao criar equipamento")',
    'raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Fora do ar.")',
    'raise HTTPException(status_code=400, detail=str(e))',
    'raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Anexo {i} não encontrado.")',
    'return JSONResponse(content=dados)',
    'return Response(conteudo, media_type=tipo)',
    'if r.status_code == 500: pass',
])
def test_a_varredura_nao_incomoda_quem_esta_certo(trecho):
    assert problemas(trecho) == []


# Único uso do texto de um erro qualquer fora do log: só compara ("value too long") para escolher o 400.
PERMITIDOS_USO = {("api/v1/endpoints/maintenance.py", "update_maintenance_order")}
AMPLOS = {"Exception", "BaseException", "SQLAlchemyError", "DBAPIError", "IntegrityError", "OperationalError"}


def _nomes_do_tipo(tipo):
    if tipo is None:
        return {"Exception"}
    return {_nome(x) for x in (tipo.elts if isinstance(tipo, ast.Tuple) else [tipo])}


def _percorrer(no):
    """Todos os nós abaixo, sem entrar em funções internas."""
    for filho in ast.iter_child_nodes(no):
        if not isinstance(filho, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            yield filho
            yield from _percorrer(filho)


def capturas(codigo, arquivo="x.py"):
    """Erro qualquer usado fora do log, e HTTPException nossa engolida por um except amplo."""
    achados = []

    def visitar(no, funcao):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcao = no.name
        if isinstance(no, ast.ExceptHandler) and _nomes_do_tipo(no.type) & AMPLOS:
            livres = set()
            for x in ast.walk(no):
                if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and _nome(x.func.value) in {"logger", "logging"}:
                    livres |= {id(y) for y in ast.walk(x)}
                if isinstance(x, ast.Raise) and x.cause is not None:
                    livres |= {id(y) for y in ast.walk(x.cause)}
            for x in ast.walk(no):
                if id(x) in livres or (arquivo, funcao) in PERMITIDOS_USO:
                    continue
                if isinstance(x, ast.Name) and (x.id == no.name or x.id == "traceback"):
                    achados.append((x.lineno, "texto de um erro qualquer usado fora do log"))
                if isinstance(x, ast.Attribute) and x.attr in {"exc_info", "exception"} and _nome(x.value) == "sys":
                    achados.append((x.lineno, "texto de um erro qualquer usado fora do log"))
        if isinstance(no, ast.Try):
            corpo = [x for item in no.body for x in [item, *_percorrer(item)]]
            lanca = any(isinstance(x, ast.Raise) and isinstance(x.exc, ast.Call) and _nome(x.exc.func) == "HTTPException" for x in corpo)
            protegido = False
            for h in no.handlers:
                nomes = _nomes_do_tipo(h.type)
                protegido = protegido or "HTTPException" in nomes
                repassa = isinstance(h.body[-1], ast.Raise) and h.body[-1].exc is None
                if lanca and not protegido and not repassa and nomes & {"Exception", "BaseException"}:
                    achados.append((h.lineno, "HTTPException engolida por except amplo"))
        for filho in ast.iter_child_nodes(no):
            visitar(filho, funcao)

    visitar(ast.parse(codigo), "")
    return achados


def test_erro_qualquer_so_vai_para_o_log_e_httpexception_nao_e_engolida():
    achados = []
    for caminho in sorted(APP.rglob("*.py")):
        arquivo = caminho.relative_to(APP).as_posix()
        achados += [f"app/{arquivo}:{linha}: {motivo}" for linha, motivo in capturas(caminho.read_text(encoding="utf-8"), arquivo)]
    assert not achados, "\n".join(achados)


@pytest.mark.parametrize("corpo,motivo", [
    ("f()|Exception as e|return str(e)", "fora do log"),
    ("f()|Exception as e|reply(f'Erro ({str(e)[:80]})')", "fora do log"),
    ("f()|Exception as e|erros.append(Item(detail=str(e)))", "fora do log"),
    ("f()|Exception as e|return json.dumps({'error': repr(e)})", "fora do log"),
    ("f()|(ValueError, SQLAlchemyError) as e|return str(e)", "fora do log"),
    ("f()|IntegrityError as e|return e.orig", "fora do log"),
    ("f()|Exception|return traceback.format_exc()", "fora do log"),
    ("f()|Exception|return str(sys.exc_info()[1])", "fora do log"),
    ("raise HTTPException(404)|Exception|raise HTTPException(status_code=500, detail='x')", "engolida"),
    ("if x: raise HTTPException(status_code=400, detail='x')|Exception|return None", "engolida"),
])
def test_a_varredura_de_capturas_pega(corpo, motivo):
    tenta, tipo, trata = corpo.split("|")
    achados = capturas(f"def g():\n    try:\n        {tenta}\n    except {tipo}:\n        {trata}\n")
    assert any(motivo in m for _, m in achados), achados


@pytest.mark.parametrize("codigo", [
    "try:\n    f()\nexcept Exception as e:\n    logger.exception('x %s', e)\n",
    "try:\n    f()\nexcept LancamentoInvalido as e:\n    x.append(str(e))\nexcept Exception:\n    logger.exception('x')\n",
    "try:\n    raise HTTPException(404)\nexcept HTTPException:\n    raise\nexcept Exception:\n    pass\n",
    "try:\n    raise HTTPException(404)\nexcept Exception:\n    db.rollback()\n    raise\n",
])
def test_a_varredura_de_capturas_nao_incomoda_quem_esta_certo(codigo):
    assert capturas(codigo) == []


# ---------------------------------------------------------------- 2) cada um dos 10 pontos, de verdade

@pytest.fixture()
def ambiente(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    agora = datetime.now(timezone.utc)
    db.add(Family(id=1, name="F", codigo_unico="f", created_at=agora, updated_at=agora))
    admin = User(id=1, username="admin", password="x", email="", first_name="", last_name="", is_staff=False,
                 is_superuser=True, is_active=True, is_child=False, date_joined=agora, family_id=1)
    db.add(admin)
    db.add(Equipment(id=1, name="Geladeira", family_id=1, owner_id=1, created_at=agora, updated_at=agora))
    db.add(MaintenanceOrder(id=1, equipment_id=1, title="T", description="D", created_by_id=1, created_at=agora, updated_at=agora))
    db.add(FamilyMember(id=1, name="M", birth_date=date(2010, 1, 2), gender="F", relationship_type="filha", family_id=1,
                        order=0, created_at=agora, updated_at=agora))
    db.commit()
    app = FastAPI()
    app.include_router(healthcare.router, prefix="/h")
    app.include_router(maintenance.router, prefix="/m")
    app.include_router(users.router, prefix="/u")
    app.include_router(finance.router, prefix="/f")
    app.include_router(telegram.router, prefix="/t")

    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_current_family] = lambda: 1
    monkeypatch.setattr(users.settings, "AUTH_KEYCLOAK_ENABLED", False)
    yield TestClient(app, raise_server_exceptions=False), db, monkeypatch
    monkeypatch.undo()
    db.close()


def _explode(*_args, **_kwargs):
    raise RuntimeError(TEXTO)


USUARIO = {"username": "novo", "email": "novo@example.com", "password": "Senha-123456", "first_name": "N", "last_name": "S", "family_id": 1}
PONTOS = {
    "membros": ("GET", "/h/members", None, ("query",), "Erro ao carregar membros da família"),
    "ordem dos membros": ("PUT", "/h/members/reorder", [{"id": 1, "order": 2}], ("commit",), "Erro ao atualizar ordem"),
    "criar equipamento": ("POST", "/m/equipment", {"name": "TV", "type": "eletronico"}, ("commit",), "Erro ao criar equipamento"),
    "excluir equipamento": ("DELETE", "/m/equipment/1", None, ("delete",), "Erro ao excluir equipamento"),
    "ver ordem": ("GET", "/m/orders/1", None, ("query",), "Erro ao carregar detalhes da ordem"),
    "salvar ordem": ("PUT", "/m/orders/1", {"title": "X"}, ("commit",), "Erro ao salvar ordem de manutenção"),
    "atualizar ordem": ("PUT", "/m/orders/1", {"title": "X"}, ("query",), "Erro inesperado ao atualizar ordem de manutenção"),
    "excluir ordem": ("DELETE", "/m/orders/1", None, ("delete",), "Erro ao excluir ordem de manutenção"),
    "criar usuário": ("POST", "/u/", USUARIO, ("commit",), "Erro ao criar usuário"),
}


@pytest.mark.parametrize("ponto", PONTOS)
def test_endpoint_responde_frase_fixa_e_o_texto_fica_so_no_log(ambiente, caplog, ponto):
    cliente, db, monkeypatch = ambiente
    metodo, caminho, corpo, falham, frase = PONTOS[ponto]
    for nome in falham:
        monkeypatch.setattr(db, nome, _explode)
    caplog.set_level(logging.ERROR)
    r = cliente.request(metodo, caminho, **({"json": corpo} if corpo is not None else {}))
    assert (r.status_code, r.json()) == (500, {"detail": frase})
    assert SEGREDO not in r.text + str(dict(r.headers)) and "psycopg2" not in r.text
    assert SEGREDO in caplog.text, "o detalhe precisa continuar no log do servidor"


def test_anexo_que_nao_decodifica_responde_frase_fixa(monkeypatch, caplog):
    monkeypatch.setattr(file_response.base64, "b64decode", _explode)
    caplog.set_level(logging.ERROR)
    with pytest.raises(HTTPException) as erro:
        file_response.get_document_response(json.dumps([{"name": "a.pdf", "data": "YQ=="}]), 0)
    assert (erro.value.status_code, erro.value.detail) == (500, "Erro ao decodificar o arquivo")
    assert SEGREDO in caplog.text


# ---------------------------------------------------------------- 3) sucesso e validação continuam iguais

def test_sucesso_continua_igual(ambiente):
    cliente, db, _ = ambiente
    assert cliente.get("/h/members").status_code == 200
    assert cliente.put("/h/members/reorder", json=[{"id": 1, "order": 2}]).json() == {"status": "success", "message": "Ordem atualizada com sucesso"}
    assert cliente.post("/m/equipment", json={"name": "TV", "type": "eletronico"}).status_code == 201
    assert cliente.get("/m/orders/1").status_code == 200
    assert cliente.put("/m/orders/1", json={"title": "Novo"}).json()["title"] == "Novo"
    assert cliente.delete("/m/orders/1").status_code == 204
    assert cliente.delete("/m/equipment/1").status_code == 204
    assert cliente.post("/u/", json=USUARIO).status_code == 200
    r = file_response.get_document_response(json.dumps([{"name": "a.pdf", "data": "YQ=="}]), 0)
    assert r.status_code == 200


def test_validacao_e_nao_encontrado_continuam_iguais(ambiente):
    cliente, db, monkeypatch = ambiente
    for metodo, caminho in (("GET", "/m/orders/99"), ("DELETE", "/m/orders/99")):
        r = cliente.request(metodo, caminho)
        assert (r.status_code, r.json()["detail"]) == (404, "Ordem de manutenção não encontrada")
    assert cliente.put("/m/orders/99", json={"title": "X"}).status_code == 404
    assert cliente.delete("/m/equipment/99").status_code == 404
    assert cliente.post("/m/equipment", json={}).status_code == 422

    def grande(*_a, **_k):
        raise RuntimeError("value too long for type character varying(100)")

    monkeypatch.setattr(db, "commit", grande)
    r = cliente.put("/m/orders/1", json={"title": "X"})
    assert r.status_code == 400 and r.json()["detail"].startswith("Documento muito grande.")


# ---------------------------------------------------------------- 4) pontos levantados pelo QA

def _lancamento(**extra):
    return {"description": "Mercado", "amount": 10, "date": "2026-11-23", "type": "EXPENSE", **extra}


@pytest.mark.parametrize("erro", [RuntimeError, ValueError, KeyError])
def test_importacao_em_lote_nao_devolve_o_texto_do_erro(ambiente, caplog, erro):
    cliente, db, monkeypatch = ambiente

    def falha(*_a, **_k):
        raise erro(TEXTO)

    caplog.set_level(logging.ERROR)
    monkeypatch.setattr(db, "begin_nested", falha)
    r = cliente.post("/f/entries/bulk", json={"entries": [_lancamento()]})
    assert (r.status_code, r.json()) == (200, {"created": 0, "errors": [{"index": 0, "detail": "Erro ao importar lançamento"}]})
    assert SEGREDO not in r.text
    assert SEGREDO in caplog.text


def test_importacao_em_lote_mantem_as_frases_proprias_e_o_que_deu_certo(ambiente):
    cliente, db, _ = ambiente
    agora = datetime.now(timezone.utc)
    db.add(FinanceCategory(id=1, name="Salário", type="INCOME", family_id=1, is_active=True, created_by_id=1, created_at=agora))
    db.commit()
    r = cliente.post("/f/entries/bulk", json={"entries": [
        _lancamento(), _lancamento(type="OUTRO"), _lancamento(category_id=99), _lancamento(category_id=1)]})
    assert r.status_code == 200 and r.json() == {"created": 1, "errors": [
        {"index": 1, "detail": "Tipo de lançamento inválido (use INCOME ou EXPENSE)"},
        {"index": 2, "detail": "Categoria não encontrada para esta família"},
        {"index": 3, "detail": "Categoria incompatível com o tipo do lançamento (receita/despesa)"}]}


FERRAMENTAS = [t["function"]["name"] for t in ai_service.TOOLS]


class ClienteIaFalso:
    """Guarda tudo o que seria enviado ao provedor externo."""

    def __init__(self, ferramenta=None, erro=None):
        self.enviado, self.ferramenta, self.erro = [], ferramenta, erro
        self.chat = self.completions = self

    def create(self, **pedido):
        from types import SimpleNamespace as N
        self.enviado.append(json.dumps(pedido, default=str, ensure_ascii=False))
        if self.erro:
            raise self.erro
        chamadas = [N(id="1", function=N(name=self.ferramenta, arguments="{}"))] if len(self.enviado) == 1 else None
        return N(choices=[N(message=N(tool_calls=chamadas, content="pronto"))])


@pytest.mark.parametrize("ferramenta", FERRAMENTAS)
def test_nada_do_erro_vai_para_o_provedor_de_ia(ambiente, caplog, ferramenta):
    _, db, monkeypatch = ambiente
    usuario = db.get(User, 1)
    assert usuario.family_id == 1
    falso = ClienteIaFalso(ferramenta)
    monkeypatch.setattr(ai_service, "_get_llm_client", lambda *_a: (falso, "m", "openai"))
    monkeypatch.setattr(db, "query", _explode)
    caplog.set_level(logging.ERROR)
    assert ai_service.process_message_with_ai("oi", usuario, db) == "pronto"
    assert len(falso.enviado) == 2
    assert ai_service.ERRO_FERRAMENTA in falso.enviado[1]
    assert SEGREDO not in "".join(falso.enviado) and "psycopg2" not in "".join(falso.enviado)
    assert SEGREDO in caplog.text


def test_falha_do_provedor_de_ia_vira_frase_fixa(ambiente, caplog):
    _, db, monkeypatch = ambiente
    falso = ClienteIaFalso(erro=RuntimeError(TEXTO))
    monkeypatch.setattr(ai_service, "_get_llm_client", lambda *_a: (falso, "m", "openai"))
    caplog.set_level(logging.ERROR)
    assert ai_service.process_message_with_ai("oi", db.get(User, 1), db) == "Erro ao processar com IA. Tente de novo mais tarde."
    assert SEGREDO in caplog.text


@pytest.mark.parametrize("onde", ["processamento", "provedor"])
def test_chat_do_telegram_recebe_so_frase_fixa(ambiente, caplog, onde):
    cliente, db, monkeypatch = ambiente
    agora = datetime.now(timezone.utc)
    db.add(FamilyTelegramConfig(family_id=1, bot_token="t", created_at=agora, updated_at=agora))
    db.add(FamilyAIConfig(family_id=1, enabled=True, provider="openai", openai_api_key="k", created_at=agora, updated_at=agora))
    db.add(TelegramUserLink(user_id=1, telegram_user_id=7, telegram_chat_id=7, use_ai=True))
    db.commit()
    enviadas = []
    monkeypatch.setattr(telegram, "_send_telegram_message", lambda _t, _c, texto: enviadas.append(texto))
    monkeypatch.setattr(telegram, "get_user_family_ids", lambda *_a: [1])
    if onde == "processamento":
        monkeypatch.setattr(telegram, "process_message_with_ai", _explode)
        frase = "Erro ao processar. Tente de novo ou use /ajuda."
    else:
        monkeypatch.setattr(ai_service, "_get_llm_client", lambda *_a: (ClienteIaFalso(erro=RuntimeError(TEXTO)), "m", "openai"))
        frase = "Erro ao processar com IA. Tente de novo mais tarde."
    caplog.set_level(logging.ERROR)
    r = cliente.post("/t/webhook/1", json={"message": {"chat": {"id": 7}, "from": {"id": 7}, "text": "oi"}})
    assert (r.status_code, r.json(), enviadas) == (200, {"ok": True}, [frase])
    assert SEGREDO in caplog.text


@pytest.mark.parametrize("codigo", [502, 503, 500])
def test_mensagem_do_keycloak_fica_so_no_log(ambiente, caplog, codigo):
    cliente, _, monkeypatch = ambiente
    monkeypatch.setattr(users.settings, "AUTH_KEYCLOAK_ENABLED", True)
    monkeypatch.setattr(users, "find_user_id", lambda _u: None)

    def recusa(**_k):
        raise KeycloakAdminError(f"Could not execute JDBC {SEGREDO}", status_code=codigo)

    monkeypatch.setattr(users, "upsert_user", recusa)
    caplog.set_level(logging.ERROR)
    r = cliente.post("/u/", json=USUARIO)
    assert (r.status_code, r.json()) == (codigo, {"detail": "Não foi possível concluir a operação no Keycloak."})
    assert SEGREDO not in r.text
    assert SEGREDO in caplog.text


def test_404_do_keycloak_continua_404_com_a_frase_nossa(monkeypatch):
    monkeypatch.setattr(users.settings, "AUTH_KEYCLOAK_ENABLED", True)

    def nao_achou():
        raise KeycloakAdminError("Usuário não encontrado no Keycloak.", status_code=404)

    with pytest.raises(HTTPException) as erro:
        users._keycloak_or_http(nao_achou)
    assert (erro.value.status_code, erro.value.detail) == (404, "Usuário não encontrado no Keycloak.")


def test_todo_erro_404_do_keycloak_tem_frase_escrita_no_codigo():
    arvore = ast.parse((APP / "core/keycloak_admin.py").read_text(encoding="utf-8"))
    com_404 = [no for no in ast.walk(arvore) if isinstance(no, ast.Call) and _nome(no.func) == "KeycloakAdminError"
               and any(k.arg == "status_code" and _status(k.value) != 502 and _status(k.value) != 503 for k in no.keywords)]
    assert com_404 and all(isinstance(no.args[0], ast.Constant) for no in com_404)


# ---------------------------------------------------------------- 5) 400/404 que viravam 500

@pytest.mark.parametrize("admin,frase", [(False, "Família não especificada"), (True, "Nenhuma família encontrada")])
def test_reordenar_membros_sem_familia_volta_a_ser_400(ambiente, admin, frase):
    cliente, db, _ = ambiente
    from app.api import deps
    usuario = User(id=50, username="x", is_superuser=admin, is_staff=False, family_id=None)
    usuario._cached_family_ids = []
    cliente.app.dependency_overrides[deps.get_current_user] = lambda: usuario
    cliente.app.dependency_overrides[deps.get_current_family] = lambda: None
    r = cliente.put("/h/members/reorder", json=[{"id": 1, "order": 2}])
    assert (r.status_code, r.json()) == (400, {"detail": frase})


@pytest.mark.parametrize("documentos,status", [("[]", 404), (None, 404), ("isto nao e json", 500), ('[{"name": "a"}]', 500)])
def test_comprovante_vazio_volta_a_ser_404(ambiente, documentos, status):
    cliente, db, _ = ambiente
    agora = datetime.now(timezone.utc)
    db.add(FinanceEntry(id=1, description="d", amount=1, date=date(2026, 11, 23), type="EXPENSE", family_id=1, created_by_id=1,
                        created_at=agora, updated_at=agora, documents=documentos))
    db.commit()
    r = cliente.get("/f/entries/1/receipt")
    assert r.status_code == status
    if status == 500:
        assert r.json() == {"detail": "Erro ao ler comprovante"}


def test_comprovante_valido_continua_igual(ambiente):
    cliente, db, _ = ambiente
    agora = datetime.now(timezone.utc)
    db.add(FinanceEntry(id=1, description="d", amount=1, date=date(2026, 11, 23), type="EXPENSE", family_id=1, created_by_id=1,
                        created_at=agora, updated_at=agora, documents=json.dumps([{"name": "a.pdf", "type": "application/pdf", "content": "YQ=="}])))
    db.commit()
    r = cliente.get("/f/entries/1/receipt")
    assert (r.status_code, r.content, r.headers["content-type"]) == (200, b"a", "application/pdf")
