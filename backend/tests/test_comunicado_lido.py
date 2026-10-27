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
    db.add(Family(id=2, name="Outra", codigo_unico="outra", created_at=agora, updated_at=agora))
    db.flush()

    def usuario(**dados):
        base = dict(
            password="x", email="", first_name="", last_name="", is_staff=False,
            is_superuser=False, is_active=True, is_child=False, date_joined=agora,
        )
        base.update(dados)
        return User(**base)

    kleber = usuario(id=1, username="kleber", first_name="Kleber", family_id=1, is_superuser=True)
    nilma = usuario(id=2, username="nilma", first_name="Nilma", family_id=1, is_staff=True)
    guilherme = usuario(
        id=16, username="guilherme", first_name="Guilherme",
        family_id=1, is_child=True, allowed_menus=["estudos"],
    )
    vizinho = usuario(id=3, username="vizinho", family_id=2, is_superuser=True)
    db.add_all([kleber, nilma, guilherme, vizinho])
    db.add(Atividade(
        id=18, aluno_id=16, family_id=1, titulo="Reunião de pais",
        descricao="Venha", professor="", data=date.today(), tipo="comunicado", status=None,
    ))
    db.commit()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/estudos")
    estado = {"user": kleber}

    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: estado["user"]
    cliente = TestClient(app)
    yield cliente, db, estado, kleber, nilma, guilherme, vizinho
    db.close()


def _comunicados(cliente, **params):
    params.setdefault("tipo", "comunicado")
    return cliente.get("/api/v1/estudos/atividades", params=params)


def test_lido_por_pessoa_e_some_da_lista(ambiente):
    cliente, db, estado, kleber, nilma, guilherme, vizinho = ambiente

    # Superuser vê o comunicado e ele vem como não lido.
    resp = _comunicados(cliente)
    assert resp.status_code == 200, resp.text
    assert [i["id"] for i in resp.json()] == [18]
    assert resp.json()[0]["lido"] is False

    # Marca como lido -> some da lista principal.
    assert cliente.post("/api/v1/estudos/atividades/18/lido").json() == {"lido": True}
    assert [i["id"] for i in _comunicados(cliente).json()] == []
    assert db.query(ComunicadoLido).count() == 1

    # Mas volta na busca, marcado como lido.
    busca = _comunicados(cliente, q="Reunião")
    assert [i["id"] for i in busca.json()] == [18]
    assert busca.json()[0]["lido"] is True

    # Staff (Nilma) tem estado próprio: ainda vê o comunicado.
    estado["user"] = nilma
    resp = _comunicados(cliente)
    assert [i["id"] for i in resp.json()] == [18]
    assert resp.json()[0]["lido"] is False
    # Nilma marca para si -> some só para ela.
    assert cliente.post("/api/v1/estudos/atividades/18/lido").status_code == 200
    assert [i["id"] for i in _comunicados(cliente).json()] == []
    assert db.query(ComunicadoLido).count() == 2

    # Superuser desmarca -> volta para ele, sem afetar a Nilma.
    estado["user"] = kleber
    assert cliente.delete("/api/v1/estudos/atividades/18/lido").json() == {"lido": False}
    assert [i["id"] for i in _comunicados(cliente).json()] == [18]
    estado["user"] = nilma
    assert [i["id"] for i in _comunicados(cliente).json()] == []


def test_filho_nao_marca_e_ve_como_hoje(ambiente):
    cliente, db, estado, kleber, nilma, guilherme, vizinho = ambiente

    # O filho marcado por engano? Não pode: 403.
    estado["user"] = guilherme
    assert cliente.post("/api/v1/estudos/atividades/18/lido").status_code == 403
    assert cliente.delete("/api/v1/estudos/atividades/18/lido").status_code == 403

    # Filho continua vendo o próprio comunicado, sempre como não lido,
    # mesmo que outra pessoa já tenha marcado como lido.
    estado["user"] = kleber
    cliente.post("/api/v1/estudos/atividades/18/lido")
    estado["user"] = guilherme
    resp = _comunicados(cliente)
    assert [i["id"] for i in resp.json()] == [18]
    assert resp.json()[0]["lido"] is False


def test_nao_marca_atividade_comum(ambiente):
    cliente, db, estado, *_ = ambiente
    db.add(Atividade(
        id=20, aluno_id=16, family_id=1, titulo="Lição", descricao="",
        professor="", data=date.today(), tipo="atividade", status="pendente",
        prazo_entrega=datetime.now(timezone.utc),
    ))
    db.commit()
    assert cliente.post("/api/v1/estudos/atividades/20/lido").status_code == 400
