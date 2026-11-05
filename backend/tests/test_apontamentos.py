from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.v1.endpoints.apontamentos import router
from app.db.base import Base, get_db
from app.models.estudo import Apontamento
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
            password="x", email="", first_name="", last_name="", is_staff=False,
            is_superuser=False, is_active=True, is_child=False, date_joined=agora,
        )
        base.update(dados)
        return User(**base)

    adulto = usuario(id=1, username="adulto", first_name="Kleber", family_id=1, is_superuser=True)
    filho = usuario(
        id=16, username="guilherme", first_name="Guilherme",
        family_id=1, is_child=True, allowed_menus=["estudos"],
    )
    db.add_all([adulto, filho])
    db.commit()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/estudos")
    estado = {"user": adulto}

    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: estado["user"]
    cliente = TestClient(app)
    yield cliente, db, estado
    db.close()


def test_importar_e_listar_apontamentos(ambiente):
    cliente, db, estado = ambiente
    payload = {
        "fonte": "e-class",
        "aluno": {"aluno_id": 16, "nome": "Guilherme"},
        "bimestre": 3,
        "ano_letivo": 2026,
        "itens": [
            {
                "data": "2026-09-12",
                "disciplina": "Matemática",
                "professor": "Prof. A",
                "tipo": "Observação",
                "titulo": "Participação em aula",
                "descricao": "Colaborou na resolução em grupo.",
            }
        ],
    }
    dry = cliente.post("/api/v1/estudos/apontamentos/importar?dry_run=true", json=payload)
    assert dry.status_code == 200, dry.text
    assert dry.json()["apontamentos"]["criados"] == 1
    assert db.query(Apontamento).count() == 0

    criado = cliente.post("/api/v1/estudos/apontamentos/importar", json=payload)
    assert criado.status_code == 200, criado.text
    assert criado.json()["apontamentos"]["criados"] == 1
    assert db.query(Apontamento).count() == 1

    de_novo = cliente.post("/api/v1/estudos/apontamentos/importar", json=payload)
    assert de_novo.json()["apontamentos"] == {"criados": 0, "atualizados": 0, "inalterados": 1}

    lista = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 16, "ano_letivo": 2026})
    assert lista.status_code == 200
    assert len(lista.json()) == 1
    assert lista.json()[0]["titulo"] == "Participação em aula"
    assert lista.json()[0]["disciplina"] == "Matemática"

    detalhe = cliente.get(f"/api/v1/estudos/apontamentos/{lista.json()[0]['id']}")
    assert detalhe.status_code == 200
    assert "Colaborou" in detalhe.json()["descricao"]


def test_filtro_bimestre_infere_pela_data_quando_nulo(ambiente):
    """e-class costuma não mandar bimestre; filtro deve usar a data do apontamento."""
    from datetime import date

    cliente, db, estado = ambiente
    db.add(Apontamento(
        family_id=1,
        aluno_id=16,
        chave_origem="eclass-16-apont-B0-2026-lingua-2026-10-21-abc",
        data=date(2026, 10, 21),
        disciplina="Língua Portuguesa",
        professor="",
        tipo="Observação",
        titulo="Conversas em excesso",
        descricao="x",
        bimestre=None,
        ano_letivo=2026,
        fonte="e-class",
        hash_conteudo="a",
        created_by_id=1,
    ))
    db.add(Apontamento(
        family_id=1,
        aluno_id=16,
        chave_origem="eclass-16-apont-B0-2026-lingua-2026-05-11-def",
        data=date(2026, 5, 11),
        disciplina="Língua Inglesa",
        professor="",
        tipo="Produtividade",
        titulo="Não fez avaliação",
        descricao="y",
        bimestre=None,
        ano_letivo=2026,
        fonte="e-class",
        hash_conteudo="b",
        created_by_id=1,
    ))
    db.commit()

    todos = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 16, "ano_letivo": 2026})
    assert todos.status_code == 200
    assert len(todos.json()) == 2
    assert {item["bimestre"] for item in todos.json()} == {2, 4}

    b4 = cliente.get(
        "/api/v1/estudos/apontamentos",
        params={"aluno_id": 16, "ano_letivo": 2026, "bimestre": 4},
    )
    assert b4.status_code == 200
    assert len(b4.json()) == 1
    assert b4.json()[0]["titulo"] == "Conversas em excesso"
    assert b4.json()[0]["bimestre"] == 4

    b2 = cliente.get(
        "/api/v1/estudos/apontamentos",
        params={"aluno_id": 16, "ano_letivo": 2026, "bimestre": 2},
    )
    assert len(b2.json()) == 1
    assert b2.json()[0]["bimestre"] == 2

    b3 = cliente.get(
        "/api/v1/estudos/apontamentos",
        params={"aluno_id": 16, "ano_letivo": 2026, "bimestre": 3},
    )
    assert b3.json() == []


def test_import_preenche_bimestre_pela_data(ambiente):
    cliente, db, estado = ambiente
    payload = {
        "fonte": "e-class",
        "aluno": {"aluno_id": 16, "nome": "Guilherme"},
        "ano_letivo": 2026,
        "itens": [
            {
                "data": "2026-09-30",
                "disciplina": "Ensino Religioso",
                "tipo": "Nota inferior a média",
                "titulo": "Produtividade - Coragem para ser fiel (TB1)",
                "descricao": "",
            }
        ],
    }
    resp = cliente.post("/api/v1/estudos/apontamentos/importar", json=payload)
    assert resp.status_code == 200, resp.text
    item = db.query(Apontamento).one()
    assert item.bimestre == 3
    lista = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 16, "bimestre": 3})
    assert len(lista.json()) == 1


def test_lido_por_pessoa_e_filtro(ambiente):
    from datetime import date

    from app.models.estudo import ApontamentoLido

    cliente, db, estado = ambiente
    db.add(Apontamento(
        family_id=1, aluno_id=16, chave_origem="eclass-16-apont-lido",
        data=date(2026, 10, 21), disciplina="Língua Portuguesa", professor="",
        tipo="Observação", titulo="Conversas em excesso", descricao="x",
        bimestre=4, ano_letivo=2026, fonte="e-class", hash_conteudo="a", created_by_id=1,
    ))
    db.commit()
    item_id = db.query(Apontamento).one().id

    lista = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 16})
    assert lista.status_code == 200
    assert lista.json()[0]["lido"] is False

    marcado = cliente.post(f"/api/v1/estudos/apontamentos/{item_id}/lido")
    assert marcado.status_code == 200
    assert marcado.json() == {"lido": True}
    assert db.query(ApontamentoLido).count() == 1

    aberta = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 16})
    assert aberta.json() == []
    lidas = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 16, "lidos": 1})
    assert len(lidas.json()) == 1
    assert lidas.json()[0]["lido"] is True

    desmarcado = cliente.delete(f"/api/v1/estudos/apontamentos/{item_id}/lido")
    assert desmarcado.json() == {"lido": False}
    de_volta = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 16})
    assert len(de_volta.json()) == 1
    assert de_volta.json()[0]["lido"] is False

    estado["user"] = db.get(__import__("app.models.user", fromlist=["User"]).User, 16)
    assert cliente.post(f"/api/v1/estudos/apontamentos/{item_id}/lido").status_code == 403
    filho = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 17})
    assert len(filho.json()) == 1
    assert filho.json()[0]["lido"] is False
