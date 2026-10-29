"""Anexos na criação de comunicados: multipart, base64, validação e trava da integração."""

import base64
import io
import json
import os
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.api.v1.endpoints.estudos as estudos
from app.api.deps import get_current_user
from app.api.v1.endpoints.estudos import router
from app.db.base import Base, get_db
from app.models.estudo import Atividade
from app.models.family import Family
from app.models.user import User


# ---------------------------------------------------------------------------
# Geradores de arquivos de teste
# ---------------------------------------------------------------------------
def png_bytes(cor=(200, 30, 30), tamanho=(12, 12)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", tamanho, cor).save(buf, format="PNG")
    return buf.getvalue()


def jpg_bytes(cor=(30, 120, 200), tamanho=(12, 12)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", tamanho, cor).save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def png_grande() -> bytes:
    """PNG de ruído grande (>5 MB), que encolhe ao ser reduzido para 1600px."""
    lado = 2000
    imagem = Image.frombytes("RGB", (lado, lado), os.urandom(lado * lado * 3))
    buf = io.BytesIO()
    imagem.save(buf, format="PNG")
    return buf.getvalue()


PDF_MINIMO = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 100 100]>>endobj\n"
    b"xref\n0 4\n0000000000 65535 f \n"
    b"trailer<</Root 1 0 R/Size 4>>\n%%EOF\n"
)


@pytest.fixture()
def ambiente(tmp_path, monkeypatch):
    # Cache de anexos isolado por teste (não suja backend/var).
    monkeypatch.setattr(estudos, "PASTA_ANEXOS", tmp_path / "anexo_cache")

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
    filho = usuario(
        id=16,
        username="guilherme",
        first_name="Guilherme",
        family_id=1,
        is_child=True,
    )
    db.add_all([admin, filho])
    # Comunicado da integração recente (sem anexos) para id 100.
    db.add(Atividade(
        id=100,
        aluno_id=16,
        family_id=1,
        titulo="Da escola (recente)",
        descricao="",
        professor="",
        data=date.today(),
        tipo="comunicado",
        status=None,
        criado_pelo_app=False,
        created_by_id=1,
        created_at=agora,
    ))
    # Comunicado da integração antigo (>24h) para id 102.
    db.add(Atividade(
        id=102,
        aluno_id=16,
        family_id=1,
        titulo="Da escola (antigo)",
        descricao="",
        professor="",
        data=date.today(),
        tipo="comunicado",
        status=None,
        criado_pelo_app=False,
        created_by_id=1,
        created_at=agora - timedelta(hours=30),
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
    yield {"cliente": cliente, "db": db, "admin": admin, "filho": filho, "estado": estado}
    db.close()


def _base_payload(**extra):
    payload = {
        "titulo": "Comunicado com anexo",
        "descricao": "",
        "disciplina": None,
        "professor": "",
        "data": str(date.today()),
        "prazo_entrega": None,
        "tipo": "comunicado",
        "autor": "Secretaria",
        "numero": "1",
        "aluno_ids": [16],
    }
    payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# Multipart
# ---------------------------------------------------------------------------
def test_multipart_pdf_e_duas_imagens(ambiente):
    cliente = ambiente["cliente"]
    arquivos = [
        ("files", ("edital.pdf", PDF_MINIMO, "application/pdf")),
        ("files", ("foto1.png", png_bytes(), "image/png")),
        ("files", ("foto2.jpg", jpg_bytes(), "image/jpeg")),
    ]
    resposta = cliente.post(
        "/api/v1/estudos/atividades",
        data={"payload": json.dumps(_base_payload())},
        files=arquivos,
    )
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert len(corpo["anexos"]) == 3
    nomes = {a["name"] for a in corpo["anexos"]}
    assert nomes == {"edital.pdf", "foto1.png", "foto2.jpg"}
    assert corpo["criado_pelo_app"] is True
    for anexo in corpo["anexos"]:
        assert anexo["size"] > 0
        assert anexo["type"] in {"application/pdf", "image/png", "image/jpeg"}


def test_multipart_sem_arquivos_cria_normal(ambiente):
    cliente = ambiente["cliente"]
    resposta = cliente.post(
        "/api/v1/estudos/atividades",
        data={"payload": json.dumps(_base_payload())},
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["anexos"] == []


# ---------------------------------------------------------------------------
# JSON base64
# ---------------------------------------------------------------------------
def test_json_anexos_base64(ambiente):
    cliente = ambiente["cliente"]
    payload = _base_payload(anexos=[
        {"nome": "a.png", "content_type": "image/png", "conteudo_base64": base64.b64encode(png_bytes()).decode()},
        {"nome": "b.pdf", "content_type": "application/pdf", "conteudo_base64": base64.b64encode(PDF_MINIMO).decode()},
    ])
    resposta = cliente.post("/api/v1/estudos/atividades", json=payload)
    assert resposta.status_code == 201, resposta.text
    assert len(resposta.json()["anexos"]) == 2


def test_json_sem_anexos_antigo_continua_ok(ambiente):
    """Payload JSON clássico, sem o campo anexos, continua funcionando."""
    cliente = ambiente["cliente"]
    resposta = cliente.post("/api/v1/estudos/atividades", json=_base_payload())
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["anexos"] == []


# ---------------------------------------------------------------------------
# Validação e transação
# ---------------------------------------------------------------------------
def test_arquivo_invalido_nao_grava_nada(ambiente):
    cliente = ambiente["cliente"]
    db = ambiente["db"]
    antes = db.query(Atividade).count()
    arquivos = [
        ("files", ("foto1.png", png_bytes(), "image/png")),
        ("files", ("ruim.png", b"isto nao eh png", "image/png")),
    ]
    resposta = cliente.post(
        "/api/v1/estudos/atividades",
        data={"payload": json.dumps(_base_payload())},
        files=arquivos,
    )
    assert resposta.status_code == 400, resposta.text
    assert "ruim.png" in resposta.json()["detail"]
    assert db.query(Atividade).count() == antes


def test_arquivo_grande_eh_comprimido(ambiente):
    cliente = ambiente["cliente"]
    bruto = png_grande()
    assert len(bruto) > 5 * 1024 * 1024
    arquivos = [("files", ("grande.png", bruto, "image/png"))]
    resposta = cliente.post(
        "/api/v1/estudos/atividades",
        data={"payload": json.dumps(_base_payload())},
        files=arquivos,
    )
    assert resposta.status_code == 201, resposta.text
    anexos = resposta.json()["anexos"]
    assert len(anexos) == 1
    assert anexos[0]["size"] < len(bruto)


def test_dois_arquivos_iguais_viram_um(ambiente):
    cliente = ambiente["cliente"]
    imagem = png_bytes()
    arquivos = [
        ("files", ("igual.png", imagem, "image/png")),
        ("files", ("igual.png", imagem, "image/png")),
    ]
    resposta = cliente.post(
        "/api/v1/estudos/atividades",
        data={"payload": json.dumps(_base_payload())},
        files=arquivos,
    )
    assert resposta.status_code == 201, resposta.text
    assert len(resposta.json()["anexos"]) == 1


def test_filho_nao_cria(ambiente):
    cliente = ambiente["cliente"]
    ambiente["estado"]["user"] = ambiente["filho"]
    resposta = cliente.post("/api/v1/estudos/atividades", json=_base_payload())
    assert resposta.status_code == 403


# ---------------------------------------------------------------------------
# Trava da integração
# ---------------------------------------------------------------------------
def test_integracao_put_delete_continuam_403(ambiente):
    cliente = ambiente["cliente"]
    payload = _base_payload(aluno_id=16)
    payload.pop("aluno_ids", None)
    assert cliente.put("/api/v1/estudos/atividades/100", json=payload).status_code == 403
    assert cliente.delete("/api/v1/estudos/atividades/100").status_code == 403


def test_integracao_anexar_em_menos_de_24h_depois_bloqueia(ambiente):
    cliente = ambiente["cliente"]
    # id 100 é da integração, recente e sem anexos: aceita o 1º lote.
    primeiro = cliente.post(
        "/api/v1/estudos/atividades/100/anexos",
        files={"file": ("foto.png", png_bytes(), "image/png")},
    )
    assert primeiro.status_code == 200, primeiro.text
    assert len(primeiro.json()["anexos"]) == 1
    # Agora já tem anexo: volta a ser só leitura.
    segundo = cliente.post(
        "/api/v1/estudos/atividades/100/anexos",
        files={"file": ("foto2.png", png_bytes(cor=(10, 10, 10)), "image/png")},
    )
    assert segundo.status_code == 403


def test_integracao_antiga_nao_aceita_anexo(ambiente):
    cliente = ambiente["cliente"]
    # id 102 tem mais de 24h: bloqueado mesmo sem anexos.
    resposta = cliente.post(
        "/api/v1/estudos/atividades/102/anexos",
        files={"file": ("foto.png", png_bytes(), "image/png")},
    )
    assert resposta.status_code == 403
