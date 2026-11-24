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
from app.api.v1.endpoints import healthcare, maintenance, users
from app.db.base import Base, get_db
from app.models.family import Family
from app.models.healthcare import FamilyMember
from app.models.maintenance import Equipment, MaintenanceOrder
from app.models.user import User
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
    # KeycloakAdminError.detail é frase escrita em core/keycloak_admin.py (ou a regra recusada pelo Keycloak).
    ("api/v1/endpoints/users.py", "_keycloak_or_http"),
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
