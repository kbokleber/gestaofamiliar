from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.v1.endpoints.apontamentos import router as apontamentos_router
from app.api.v1.endpoints.provas import router as provas_router
from app.db.base import Base, get_db
from app.models.estudo import Apontamento
from app.models.family import Family
from app.models.prova import Avaliacao, Boletim, BoletimLinha, Cronograma, CronogramaAluno
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
    gui = usuario(id=16, username="guilherme", first_name="Guilherme", family_id=1, is_child=True, allowed_menus=["estudos"])
    gio = usuario(id=17, username="giovana", first_name="Giovana", family_id=1, is_child=True, allowed_menus=["estudos"])
    db.add_all([adulto, gui, gio])

    # Cronograma compartilhado (os dois vinculados) — não pode vazar linha e-class do irmão.
    cronograma = Cronograma(
        id=10, family_id=1, chave_origem="compartilhado-teste",
        titulo="Teste", bimestre=3, ano_letivo=2026, status="ativo", created_by_id=1,
    )
    db.add(cronograma)
    db.flush()
    db.add_all([
        CronogramaAluno(cronograma_id=10, aluno_id=16, family_id=1),
        CronogramaAluno(cronograma_id=10, aluno_id=17, family_id=1),
    ])
    av_gui = Avaliacao(
        family_id=1, cronograma_id=10,
        chave_origem="eclass-16-B3-ciencias-RC1-2026-10-01-aaaa",
        disciplina="Ciências", categoria="RECUPERACAO", categoria_rotulo="RC1",
        tipo_codigo_eclass="RC1", titulo="RC Gui", fonte="eclass",
        nota_alcancada=6.5, valor=10, data_inicio=date(2026, 10, 1),
        created_by_id=1,
    )
    av_gio = Avaliacao(
        family_id=1, cronograma_id=10,
        chave_origem="eclass-17-B3-arte-TB1-2026-09-01-bbbb",
        disciplina="Arte", categoria="PRODUTIVIDADE", categoria_rotulo="TB1",
        tipo_codigo_eclass="TB1", titulo="TB Gio", fonte="eclass",
        nota_alcancada=9.0, valor=10, data_inicio=date(2026, 9, 1),
        created_by_id=1,
    )
    db.add_all([av_gui, av_gio])

    for aluno_id, disc in ((16, "Ciências"), (17, "Arte")):
        bol = Boletim(family_id=1, aluno_id=aluno_id, ano_letivo=2026, fonte="e-class", created_by_id=1)
        db.add(bol)
        db.flush()
        db.add(BoletimLinha(
            family_id=1, boletim_id=bol.id, disciplina=disc,
            b3_nota=8.0 if aluno_id == 16 else 10.0, created_by_id=1,
        ))

    db.add_all([
        Apontamento(
            family_id=1, aluno_id=16, chave_origem="eclass-16-apont-1",
            titulo="Nota Gui", descricao="só gui", ano_letivo=2026, bimestre=3, created_by_id=1,
        ),
        Apontamento(
            family_id=1, aluno_id=17, chave_origem="eclass-17-apont-1",
            titulo="Nota Gio", descricao="só gio", ano_letivo=2026, bimestre=3, created_by_id=1,
        ),
    ])
    db.commit()

    app = FastAPI()
    app.include_router(provas_router, prefix="/api/v1/estudos")
    app.include_router(apontamentos_router, prefix="/api/v1/estudos")
    estado = {"user": gui}

    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: estado["user"]
    cliente = TestClient(app)
    yield cliente, db, estado, av_gui, av_gio
    db.close()


def test_filho_so_ve_proprias_avaliacoes_eclass(ambiente):
    cliente, db, estado, av_gui, av_gio = ambiente
    estado["user"] = db.get(User, 16)
    # Pedindo aluno_id da irmã — deve ignorar e devolver só o próprio.
    resp = cliente.get("/api/v1/estudos/avaliacoes", params={
        "so_eclass": True, "incluir_sem_data": True, "aluno_id": 17, "ano_letivo": 2026,
    })
    assert resp.status_code == 200
    ids = {item["id"] for item in resp.json()}
    assert av_gui.id in ids
    assert av_gio.id not in ids

    estado["user"] = db.get(User, 17)
    resp = cliente.get("/api/v1/estudos/avaliacoes", params={
        "so_eclass": True, "incluir_sem_data": True, "aluno_id": 16,
    })
    ids = {item["id"] for item in resp.json()}
    assert av_gio.id in ids
    assert av_gui.id not in ids


def test_filho_nao_abre_detalhe_do_irmao(ambiente):
    cliente, db, estado, av_gui, av_gio = ambiente
    estado["user"] = db.get(User, 16)
    assert cliente.get(f"/api/v1/estudos/avaliacoes/{av_gio.id}").status_code == 404
    assert cliente.get(f"/api/v1/estudos/avaliacoes/{av_gui.id}").status_code == 200


def test_filho_boletim_forca_proprio_id(ambiente):
    cliente, db, estado, av_gui, av_gio = ambiente
    estado["user"] = db.get(User, 16)
    # Pede boletim da Giovana — backend força Guilherme.
    resp = cliente.get("/api/v1/estudos/boletim", params={"aluno_id": 17, "ano_letivo": 2026})
    assert resp.status_code == 200
    assert resp.json()["aluno_id"] == 16
    assert resp.json()["linhas"][0]["disciplina"] == "Ciências"


def test_filho_apontamentos_so_proprios(ambiente):
    cliente, db, estado, av_gui, av_gio = ambiente
    estado["user"] = db.get(User, 16)
    resp = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 17, "ano_letivo": 2026})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["titulo"] == "Nota Gui"

    estado["user"] = db.get(User, 17)
    resp = cliente.get("/api/v1/estudos/apontamentos", params={"aluno_id": 16})
    assert [item["titulo"] for item in resp.json()] == ["Nota Gio"]


def test_adulto_ve_os_dois(ambiente):
    cliente, db, estado, av_gui, av_gio = ambiente
    estado["user"] = db.get(User, 1)
    todos = cliente.get("/api/v1/estudos/avaliacoes", params={"so_eclass": True, "incluir_sem_data": True})
    assert {item["id"] for item in todos.json()} >= {av_gui.id, av_gio.id}
    gui = cliente.get("/api/v1/estudos/avaliacoes", params={"so_eclass": True, "incluir_sem_data": True, "aluno_id": 16})
    assert {item["id"] for item in gui.json()} == {av_gui.id}
