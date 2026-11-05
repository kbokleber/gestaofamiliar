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
