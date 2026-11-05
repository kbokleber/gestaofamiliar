from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.v1.endpoints.provas import router
from app.db.base import Base, get_db
from app.models.family import Family
from app.models.prova import Avaliacao, Boletim, BoletimLinha, Cronograma
from app.models.user import User
from app.services.eclass import chave_item_eclass, mapear_categoria


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
    yield cliente, db, estado, filho
    db.close()


def test_mapa_categoria():
    assert mapear_categoria("AV1") == ("AV1", "AV1")
    assert mapear_categoria("RD2") == ("REDACAO", "RD2")
    assert mapear_categoria("RC1") == ("RECUPERACAO", "RC1")
    assert mapear_categoria("TB3") == ("PRODUTIVIDADE", "TB3")
    assert mapear_categoria("TD1") == ("PRODUTIVIDADE", "TD1")
    assert mapear_categoria("SI1") == ("OUTRO", "SI1")
    assert mapear_categoria("PAAEB") == ("OUTRO", "PAAEB")


def test_sincronizar_avaliacoes_e_boletim(ambiente):
    cliente, db, estado, filho = ambiente
    payload = {
        "fonte": "e-class",
        "scraped_at": "2026-11-05T13:55:00-03:00",
        "aluno": {"profile": "Gui", "aluno_id": 16, "turma_portal": "EFUND09MB", "nome": "Guilherme"},
        "bimestre": 3,
        "ano_letivo": 2026,
        "disciplinas": [
            {
                "disciplina": "Ciências",
                "professor": "Prof. Teste",
                "nota_parcial": 8.8,
                "itens": [
                    {
                        "data": "2026-10-01",
                        "tipo_codigo": "RC1",
                        "atividade": "Recuperação Única - mundo microscópio (RC1)",
                        "alcancado": 6.5,
                        "valor": 10.0,
                        "detalhe": {
                            "codigo": "RC1",
                            "descricao": "Avaliação Teórica",
                            "realizado_em": "2026-10-01",
                            "nota_final": 6.5,
                            "composicao": [
                                {"realizado_em": "2026-08-24", "avaliacao": "AV1", "nota_final": 10.0},
                                {"realizado_em": "2026-09-18", "avaliacao": "AV2", "nota_final": 5.5},
                            ],
                        },
                    },
                    {
                        "data": "2026-09-10",
                        "tipo_codigo": "TB1",
                        "atividade": "TB1 Produtividade 1 - Esportes",
                        "alcancado": 9.0,
                        "valor": 10.0,
                    },
                ],
            }
        ],
        "boletim": {
            "linhas": [
                {
                    "disciplina": "Ciências",
                    "b1_nota": 7.0, "b1_faltas": 0,
                    "b2_nota": 8.0, "b2_faltas": 1,
                    "b3_nota": 8.8, "b3_faltas": 0,
                },
                {
                    "disciplina": "Arte",
                    "b1_nota": 5.0, "b1_faltas": 0,
                    "b2_nota": 6.7, "b2_faltas": 0,
                    "b3_nota": 9.9, "b3_faltas": 1,
                },
            ],
            "total_faltas_por_bimestre": None,
        },
        "provas_agenda": [
            {
                "titulo": "PAAEB Prova cognitiva 9º ano",
                "tipo_badge": "CPB Prova",
                "prazo": "2026-11-10",
                "modalidade": "Híbrido",
                "codigo": "WSAV70OK",
                "questoes": 77,
            }
        ],
    }

    dry = cliente.post("/api/v1/estudos/eclass/sincronizar?dry_run=true", json=payload)
    assert dry.status_code == 200, dry.text
    assert dry.json()["avaliacoes"]["criadas"] == 3
    assert db.query(Avaliacao).count() == 0

    criado = cliente.post("/api/v1/estudos/eclass/sincronizar", json=payload)
    assert criado.status_code == 200, criado.text
    corpo = criado.json()
    assert corpo["avaliacoes"]["criadas"] == 3
    assert corpo["boletim"]["acao"] == "criado"
    assert db.query(Avaliacao).count() == 3
    assert db.query(Boletim).count() == 1
    assert db.query(Cronograma).count() == 1

    rc = db.query(Avaliacao).filter(Avaliacao.tipo_codigo_eclass == "RC1").one()
    assert rc.categoria == "RECUPERACAO"
    assert float(rc.nota_alcancada) == 6.5
    assert float(rc.valor) == 10.0
    assert rc.professor == "Prof. Teste"
    assert rc.fonte == "eclass"
    assert rc.composicao and len(rc.composicao) == 2
    assert rc.chave_origem.startswith("eclass-16-B3-ciencias-RC1-")

    tb = db.query(Avaliacao).filter(Avaliacao.tipo_codigo_eclass == "TB1").one()
    assert tb.categoria == "PRODUTIVIDADE"
    assert tb.categoria_rotulo == "TB1"

    paaeb = db.query(Avaliacao).filter(Avaliacao.tipo_codigo_eclass == "PAAEB").one()
    assert paaeb.categoria == "OUTRO"
    assert paaeb.chave_origem == "eclass-16-PAAEB-WSAV70OK"

    de_novo = cliente.post("/api/v1/estudos/eclass/sincronizar", json=payload)
    assert de_novo.status_code == 200, de_novo.text
    assert de_novo.json()["avaliacoes"] == {"criadas": 0, "atualizadas": 0, "inalteradas": 3}
    assert db.query(Avaliacao).count() == 3

    boletim = cliente.get("/api/v1/estudos/boletim", params={"aluno_id": 16, "ano_letivo": 2026})
    assert boletim.status_code == 200, boletim.text
    dados = boletim.json()
    assert dados["aluno_id"] == 16
    assert len(dados["linhas"]) == 2
    ciencias = next(item for item in dados["linhas"] if item["disciplina"] == "Ciências")
    assert ciencias["b3_nota"] == 8.8
    assert ciencias["nota_parcial"] == 8.8
    assert ciencias["bimestre_nota_parcial"] == 3
    assert ciencias["professor"] == "Prof. Teste"

    detalhe = cliente.get(f"/api/v1/estudos/avaliacoes/{rc.id}")
    assert detalhe.status_code == 200
    assert detalhe.json()["nota_alcancada"] == 6.5
    assert detalhe.json()["tipo_codigo_eclass"] == "RC1"

    esperado = chave_item_eclass(
        16, 3, "Ciências", "RC1",
        __import__("datetime").date(2026, 10, 1),
        "Recuperação Única - mundo microscópio (RC1)",
    )
    assert rc.chave_origem == esperado


def test_sync_nao_cria_linha_boletim_a_partir_de_avaliacoes(ambiente):
    """Cartões Arte A / Arte R / Cultura Geral ficam só em Avaliações — não no boletim."""
    cliente, db, estado, filho = ambiente
    payload = {
        "fonte": "e-class",
        "aluno": {"profile": "Gui", "aluno_id": 16, "turma_portal": "EFUND09MB", "nome": "Guilherme"},
        "bimestre": 3,
        "ano_letivo": 2026,
        "disciplinas": [
            {
                "disciplina": "Arte A",
                "professor": "Prof. Arte",
                "nota_parcial": 9.0,
                "itens": [
                    {
                        "data": "2026-09-01",
                        "tipo_codigo": "TB1",
                        "atividade": "Trabalho Arte A",
                        "alcancado": 9.0,
                        "valor": 10.0,
                    }
                ],
            },
            {
                "disciplina": "Cultura Geral",
                "nota_parcial": None,
                "itens": [],
            },
        ],
        "boletim": {
            "linhas": [
                {
                    "disciplina": "Arte",
                    "b1_nota": 5.0, "b1_faltas": 0,
                    "b2_nota": 6.7, "b2_faltas": 0,
                    "b3_nota": 9.9, "b3_faltas": 1,
                },
            ],
        },
    }
    resp = cliente.post("/api/v1/estudos/eclass/sincronizar", json=payload)
    assert resp.status_code == 200, resp.text
    assert db.query(Avaliacao).filter(Avaliacao.disciplina == "Arte A").count() == 1
    nomes = {linha.disciplina for linha in db.query(BoletimLinha).all()}
    assert nomes == {"Arte"}
    assert "Arte A" not in nomes
    assert "Cultura Geral" not in nomes


def test_sync_substituir_linhas_remove_orfas(ambiente):
    cliente, db, estado, filho = ambiente
    base = {
        "fonte": "e-class",
        "aluno": {"profile": "Gui", "aluno_id": 16, "turma_portal": "EFUND09MB", "nome": "Guilherme"},
        "bimestre": 3,
        "ano_letivo": 2026,
        "disciplinas": [],
        "boletim": {
            "linhas": [
                {"disciplina": "Arte", "b3_nota": 9.9, "b3_faltas": 1},
                {"disciplina": "Arte A", "b3_nota": None, "b3_faltas": None},
                {"disciplina": "Cultura Geral", "b3_nota": None, "b3_faltas": None},
            ],
        },
    }
    assert cliente.post("/api/v1/estudos/eclass/sincronizar", json=base).status_code == 200
    assert db.query(BoletimLinha).count() == 3

    limpo = {
        **base,
        "boletim": {
            "substituir_linhas": True,
            "linhas": [
                {"disciplina": "Arte", "b3_nota": 9.9, "b3_faltas": 1},
            ],
        },
    }
    resp = cliente.post("/api/v1/estudos/eclass/sincronizar", json=limpo)
    assert resp.status_code == 200, resp.text
    corpo = resp.json()["boletim"]
    assert corpo["substituir_linhas"] is True
    assert corpo["removidas"] == 2
    assert corpo["linhas"] == 1
    nomes = {linha.disciplina for linha in db.query(BoletimLinha).all()}
    assert nomes == {"Arte"}


def test_delete_linha_boletim(ambiente):
    cliente, db, estado, filho = ambiente
    payload = {
        "fonte": "e-class",
        "aluno": {"profile": "Gui", "aluno_id": 16, "turma_portal": "EFUND09MB", "nome": "Guilherme"},
        "bimestre": 3,
        "ano_letivo": 2026,
        "disciplinas": [],
        "boletim": {
            "linhas": [
                {"disciplina": "Arte", "b3_nota": 9.9, "b3_faltas": 1},
                {"disciplina": "Cultura Geral", "b3_nota": None, "b3_faltas": None},
            ],
        },
    }
    assert cliente.post("/api/v1/estudos/eclass/sincronizar", json=payload).status_code == 200
    orfa = db.query(BoletimLinha).filter(BoletimLinha.disciplina == "Cultura Geral").one()
    arte = db.query(BoletimLinha).filter(BoletimLinha.disciplina == "Arte").one()
    boletim_id = orfa.boletim_id

    resp = cliente.delete(f"/api/v1/estudos/boletim/linhas/{orfa.id}")
    assert resp.status_code == 204, resp.text
    assert db.query(BoletimLinha).filter(BoletimLinha.id == orfa.id).first() is None
    assert db.query(BoletimLinha).filter(BoletimLinha.id == arte.id).one().disciplina == "Arte"
    assert db.query(Boletim).filter(Boletim.id == boletim_id).one() is not None

    inexistente = cliente.delete("/api/v1/estudos/boletim/linhas/99999")
    assert inexistente.status_code == 404
