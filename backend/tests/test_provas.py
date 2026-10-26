import base64
import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.api.v1.endpoints.provas import router
from app.db.base import Base, get_db
from app.models.estudo import Atividade
from app.models.family import Family
from app.models.prova import Avaliacao, AvaliacaoHistorico, Cronograma, EventoEscolar
from app.models.user import User

FIXTURE = Path(__file__).parent / "fixtures" / "avaliacoes-extraidas-EFUND09MA_MB.json"
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
NOME_PDF = "Critérios Avaliativos e Cronograma das Atividades_4º bimestre_ EFUND09MA_MB.pdf"


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

    adulto = usuario(id=1, username="adulto", first_name="Kleber", last_name="Bueno", family_id=1, is_superuser=True)
    filho = usuario(
        id=16, username="guilherme", first_name="Guilherme", last_name="Bueno",
        family_id=1, is_child=True, allowed_menus=["estudos"],
    )
    irma = usuario(
        id=17, username="giovana", first_name="Giovana", last_name="Bueno",
        family_id=1, is_child=True, allowed_menus=["estudos"],
    )
    vizinho = usuario(id=3, username="vizinho", family_id=2, is_superuser=True)
    db.add_all([adulto, filho, irma, vizinho])
    db.add(Atividade(
        id=18,
        aluno_id=16,
        family_id=1,
        titulo="Cronograma",
        descricao="",
        professor="",
        data=date(2026, 10, 15),
        tipo="comunicado",
        status=None,
        anexos=json.dumps([{
            "name": NOME_PDF,
            "type": "application/pdf",
            "size": len(PDF),
            "data": base64.b64encode(PDF).decode("ascii"),
        }]),
        created_by_id=1,
    ))
    db.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/estudos")
    estado = {"user": adulto}

    def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = lambda: estado["user"]
    cliente = TestClient(app)
    yield cliente, db, estado, filho, irma, vizinho
    db.close()


def _payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_fixture_do_nono_ano(ambiente):
    cliente, db, estado, filho, irma, vizinho = ambiente
    payload = _payload()
    original = next(
        item["criterio_correcao"]
        for item in payload["avaliacoes"]
        if item["chave_origem"].endswith("lingua-portuguesa-av1-1")
    )

    simulado = cliente.post("/api/v1/estudos/cronogramas/importar?dry_run=true", json=payload)
    assert simulado.status_code == 200, simulado.text
    assert simulado.json()["avaliacoes"]["criadas"] == 41
    assert db.query(Cronograma).count() == 0

    criado = cliente.post("/api/v1/estudos/cronogramas/importar", json=payload)
    assert criado.status_code == 200, criado.text
    relatorio = criado.json()
    assert relatorio["cronograma"] == "criado"
    assert relatorio["avaliacoes"]["criadas"] == 41
    assert db.query(Cronograma).count() == 1
    assert db.query(Avaliacao).count() == 41
    assert db.query(Avaliacao).filter(Avaliacao.sem_data.is_(False)).count() == 37
    assert db.query(Avaliacao).filter(Avaliacao.sem_data.is_(True)).count() == 4
    assert db.query(EventoEscolar).count() == 23
    cronograma_id = relatorio["cronograma_id"]

    de_novo = cliente.post("/api/v1/estudos/cronogramas/importar", json=payload)
    assert de_novo.status_code == 200, de_novo.text
    assert de_novo.json()["avaliacoes"] == {"criadas": 0, "atualizadas": 0, "inalteradas": 41, "removidas": 0}
    assert de_novo.json()["cronograma"] == "inalterado"
    assert db.query(Avaliacao).count() == 41
    assert db.query(EventoEscolar).count() == 23

    outubro = cliente.get("/api/v1/estudos/calendario", params={
        "de": "2026-10-01", "ate": "2026-10-31", "aluno_id": 16, "incluir_eventos_escolares": False,
    })
    assert outubro.status_code == 200, outubro.text
    eventos = outubro.json()
    portugues = [item for item in eventos if item["disciplina"] == "Língua Portuguesa" and item["categoria"] == "AV1"]
    assert any(item["inicio"] == "2026-10-23" and item["fim"] == "2026-10-28" and item["periodo"] for item in portugues)
    geografia = [item for item in eventos if item["disciplina"] == "Geografia" and item["categoria"] == "AV1"]
    assert len(geografia) == 2
    assert {item["inicio"] for item in geografia} == {"2026-10-22", "2026-10-27"}
    historia = [item for item in eventos if item["disciplina"] == "História" and item["categoria"] == "AV1"]
    assert len(historia) == 4
    assert all(item["turma"] for item in historia)
    leitura = [item for item in eventos if item.get("titulo") == "PROJETO LEITURA"]
    assert leitura and leitura[0]["inicio"] == "2026-10-19" and leitura[0]["fim"] == "2026-12-02"

    dia = cliente.get("/api/v1/estudos/calendario", params={
        "de": "2026-10-23", "ate": "2026-10-23", "aluno_id": 16,
        "agrupar": "dia", "incluir_eventos_escolares": False,
    })
    itens = dia.json()["2026-10-23"]
    assert any(item["disciplina"] == "Língua Portuguesa" and item["categoria"] == "AV1" and item["inicio_periodo"] for item in itens)
    assert any(
        item["titulo"] == "PROJETO LEITURA" and item["periodo"] and not item["inicio_periodo"] and not item["fim_periodo"]
        for item in itens
    )
    assert any(item["disciplina"] == "Ensino Religioso" and "LAPBOOK" in item["titulo"] for item in itens)

    novembro = cliente.get("/api/v1/estudos/avaliacoes", params={
        "categoria": "AV2", "de": "2026-11-01", "ate": "2026-11-30", "aluno_id": 16,
    })
    assert len(novembro.json()) == 5
    portugues_lista = cliente.get("/api/v1/estudos/avaliacoes", params={
        "disciplina": "Língua Portuguesa", "aluno_id": 16, "incluir_sem_data": True,
    })
    assert len(portugues_lista.json()) == 7

    mapa = next(item for item in portugues_lista.json() if item["chave_origem"].endswith("lingua-portuguesa-av1-1"))
    detalhe = cliente.get(f"/api/v1/estudos/avaliacoes/{mapa['id']}")
    assert detalhe.status_code == 200
    assert detalhe.json()["criterio_correcao"] == original

    pdf = cliente.get(f"/api/v1/estudos/cronogramas/{cronograma_id}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert "inline" in pdf.headers["content-disposition"].lower()
    assert pdf.content.startswith(b"%PDF")

    estado["user"] = irma
    assert cliente.get("/api/v1/estudos/avaliacoes", params={"incluir_sem_data": True}).json() == []
    assert cliente.post("/api/v1/estudos/cronogramas/importar", json=payload).status_code == 403
    estado["user"] = filho
    assert len(cliente.get("/api/v1/estudos/avaliacoes", params={"incluir_sem_data": True}).json()) == 41
    assert cliente.post("/api/v1/estudos/cronogramas/importar", json=payload).status_code == 403
    estado["user"] = vizinho
    assert cliente.get(f"/api/v1/estudos/avaliacoes/{mapa['id']}").status_code == 404
    estado["user"] = db.query(User).filter(User.id == 1).one()

    mudado = copy.deepcopy(payload)
    ciencias = next(item for item in mudado["avaliacoes"] if item["chave_origem"].endswith("ciencias-av1-1"))
    ciencias["data_texto"] = "29/10"
    ciencias["ocorrencias"] = [{"data_inicio": "2026-10-29", "data_fim": "2026-10-29", "turma": None}]
    atualizado = cliente.post("/api/v1/estudos/cronogramas/importar", json=mudado)
    assert atualizado.status_code == 200, atualizado.text
    assert atualizado.json()["avaliacoes"]["atualizadas"] == 1
    assert db.query(AvaliacaoHistorico).count() == 1

    invalido = copy.deepcopy(payload)
    invalido["avaliacoes"][0]["ocorrencias"][0]["data_inicio"] = "2026-10-28"
    invalido["avaliacoes"][0]["ocorrencias"][0]["data_fim"] = "2026-10-01"
    assert cliente.post("/api/v1/estudos/cronogramas/importar", json=invalido).status_code == 422
    invalido = copy.deepcopy(payload)
    invalido["avaliacoes"][0]["categoria"] = "PROVA"
    assert cliente.post("/api/v1/estudos/cronogramas/importar", json=invalido).status_code == 422
    invalido = copy.deepcopy(payload)
    invalido["documento"]["aluno_ids"] = [1]
    resposta = cliente.post("/api/v1/estudos/cronogramas/importar", json=invalido)
    assert resposta.status_code == 422
    assert "aluno_ids" in json.dumps(resposta.json())
    invalido = copy.deepcopy(payload)
    invalido["avaliacoes"][1]["chave_origem"] = invalido["avaliacoes"][0]["chave_origem"]
    assert cliente.post("/api/v1/estudos/cronogramas/importar", json=invalido).status_code == 422
