"""Comunicados: origem app vs integração, bloqueio de edição e marca de lido."""

from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.v1.endpoints.estudos import router
from app.db.base import Base, get_db
from app.models.estudo import Atividade, ComunicadoLido
from app.models.family import Family
from app.models.user import User


@pytest.fixture()
def ambiente():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    agora = datetime.now(timezone.utc)
    db.add(Family(id=1, name="Bueno", codigo_unico="bueno", created_at=agora, updated_at=agora))
    db.flush()

    def usuario(**dados):
        base = dict(
            password="x",
            email="",
            first_name="",
            last_name="",
            is_staff=False,
            is_superuser=False,
            is_active=True,
            is_child=False,
            date_joined=agora,
            allowed_menus=["estudos"],
        )
        base.update(dados)
        return User(**base)

    admin = usuario(
        id=1,
        username="kleber",
        first_name="Kleber",
        family_id=1,
        is_superuser=True,
        api_token="token-integracao",
    )
    staff = usuario(
        id=2,
        username="nilma",
        first_name="Nilma",
        family_id=1,
        is_staff=True,
    )
    filho = usuario(
        id=16,
        username="guilherme",
        first_name="Guilherme",
        family_id=1,
        is_child=True,
    )
    db.add_all([admin, staff, filho])
    db.add(Atividade(
        id=100,
        aluno_id=16,
        family_id=1,
        titulo="Da escola",
        descricao="",
        professor="",
        data=date.today(),
        tipo="comunicado",
        status=None,
        criado_pelo_app=False,
        created_by_id=1,
    ))
    db.add(Atividade(
        id=101,
        aluno_id=16,
        family_id=1,
        titulo="Do app",
        descricao="",
        professor="",
        data=date.today(),
        tipo="comunicado",
        status=None,
        criado_pelo_app=True,
        created_by_id=1,
    ))
    db.commit()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/estudos")

    def _db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _db
    estado = {"user": admin}

    async def _user():
        return estado["user"]

    app.dependency_overrides[get_current_user] = _user
    cliente = TestClient(app)
    yield {"cliente": cliente, "db": db, "admin": admin, "staff": staff, "filho": filho, "estado": estado}
    db.close()


def test_put_delete_bloqueados_para_integracao(ambiente):
    cliente = ambiente["cliente"]
    payload = {
        "titulo": "Tentativa",
        "descricao": "",
        "disciplina": None,
        "professor": "",
        "data": str(date.today()),
        "prazo_entrega": None,
        "tipo": "comunicado",
        "autor": None,
        "numero": None,
        "aluno_id": 16,
    }
    assert cliente.put("/api/v1/estudos/atividades/100", json=payload).status_code == 403
    assert cliente.delete("/api/v1/estudos/atividades/100").status_code == 403


def test_put_delete_permitidos_para_app(ambiente):
    cliente = ambiente["cliente"]
    payload = {
        "titulo": "Atualizado",
        "descricao": "ok",
        "disciplina": None,
        "professor": "",
        "data": str(date.today()),
        "prazo_entrega": None,
        "tipo": "comunicado",
        "autor": "Casa",
        "numero": "1",
        "aluno_id": 16,
    }
    put = cliente.put("/api/v1/estudos/atividades/101", json=payload)
    assert put.status_code == 200
    assert put.json()["titulo"] == "Atualizado"
    assert put.json()["criado_pelo_app"] is True
    assert cliente.delete("/api/v1/estudos/atividades/101").status_code == 200


def test_create_via_api_token_marca_integracao(ambiente):
    """Simula criação pela integração: X-API-Token presente → criado_pelo_app=False."""
    cliente = ambiente["cliente"]
    payload = {
        "titulo": "Integração nova",
        "descricao": "",
        "disciplina": None,
        "professor": "",
        "data": str(date.today()),
        "prazo_entrega": None,
        "tipo": "comunicado",
        "autor": "Secretaria",
        "numero": "99",
        "aluno_ids": [16],
    }
    # get_current_user overridden; o parâmetro api_key do create lê o header.
    resposta = cliente.post(
        "/api/v1/estudos/atividades",
        json=payload,
        headers={"X-API-Token": "token-integracao"},
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["criado_pelo_app"] is False
    novo_id = resposta.json()["id"]
    assert cliente.delete(f"/api/v1/estudos/atividades/{novo_id}").status_code == 403


def test_create_via_bearer_marca_app(ambiente):
    cliente = ambiente["cliente"]
    payload = {
        "titulo": "App novo",
        "descricao": "",
        "disciplina": None,
        "professor": "",
        "data": str(date.today()),
        "prazo_entrega": None,
        "tipo": "comunicado",
        "autor": None,
        "numero": None,
        "aluno_ids": [16],
    }
    resposta = cliente.post("/api/v1/estudos/atividades", json=payload)
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["criado_pelo_app"] is True
    novo_id = resposta.json()["id"]
    assert cliente.delete(f"/api/v1/estudos/atividades/{novo_id}").status_code == 200


def test_lido_por_pessoa_e_filtro_lista(ambiente):
    cliente = ambiente["cliente"]
    estado = ambiente["estado"]
    staff = ambiente["staff"]
    filho = ambiente["filho"]
    db = ambiente["db"]

    estado["user"] = staff
    assert cliente.post("/api/v1/estudos/atividades/100/lido").status_code == 200
    lista = cliente.get("/api/v1/estudos/atividades", params={"tipo": "comunicado"})
    assert lista.status_code == 200
    ids = {item["id"] for item in lista.json()}
    assert 100 not in ids
    assert 101 in ids

    busca = cliente.get("/api/v1/estudos/atividades", params={"tipo": "comunicado", "q": "escola"})
    assert busca.status_code == 200
    encontrado = next(item for item in busca.json() if item["id"] == 100)
    assert encontrado["lido"] is True

    assert cliente.delete("/api/v1/estudos/atividades/100/lido").status_code == 200
    lista2 = cliente.get("/api/v1/estudos/atividades", params={"tipo": "comunicado"})
    assert 100 in {item["id"] for item in lista2.json()}

    estado["user"] = filho
    assert cliente.post("/api/v1/estudos/atividades/100/lido").status_code == 403
    assert db.query(ComunicadoLido).count() == 0
