"""Anexos do membro da família: contrato, OpenAPI e API com X-API-Token."""
import json
import os
from datetime import date, datetime, timezone

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("SECRET_KEY", "test")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  registra as tabelas usadas pelos relacionamentos
from app.api.v1.endpoints.healthcare import router
from app.db.base import Base, get_db
from app.models.family import Family
from app.models.user import User
from app.schemas.healthcare import DOCUMENTS_EXAMPLE, FamilyMemberCreate, FamilyMemberUpdate

ANEXO = [{"name": "carteirinha.pdf", "type": "application/pdf", "size": 1, "data": "YQ=="}]
ANEXO_JSON = json.dumps(ANEXO)
TOKEN = "token-integracao"


def test_update_sem_documents_nao_inclui_o_campo():
    data = FamilyMemberUpdate(name="Ana")
    dumped = data.model_dump(exclude_unset=True)
    assert "documents" not in dumped
    assert dumped["name"] == "Ana"


def test_update_com_documents_nulo_limpa_anexos():
    data = FamilyMemberUpdate.model_validate({"documents": None, "notes": "ok"})
    dumped = data.model_dump(exclude_unset=True)
    assert "documents" in dumped
    assert dumped["documents"] is None
    assert dumped["notes"] == "ok"
    assert "name" not in dumped


def test_update_com_documents_json_persiste_o_valor():
    payload = '[{"name":"carteirinha.pdf","type":"application/pdf","size":12,"data":"YQ=="}]'
    data = FamilyMemberUpdate.model_validate({"documents": payload})
    dumped = data.model_dump(exclude_unset=True)
    assert dumped["documents"] == payload


def test_create_documents_e_opcional_e_nulo_por_padrao():
    data = FamilyMemberCreate(name="Ana", birth_date=date(2010, 1, 2))
    dumped = data.model_dump()
    assert dumped["documents"] is None


def _cliente():
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
    db.add(User(
        id=1,
        password="x",
        username="kleber",
        first_name="Kleber",
        last_name="",
        email="",
        is_staff=False,
        is_superuser=True,
        is_active=True,
        is_child=False,
        date_joined=agora,
        family_id=1,
        api_token=TOKEN,
    ))
    db.commit()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/healthcare")

    def _db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _db
    cliente = TestClient(app)
    return cliente, db


def test_openapi_documenta_anexos_e_api_token():
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/healthcare")
    spec = app.openapi()
    esquema = spec["components"]["securitySchemes"]["APIKeyHeader"]
    assert esquema["type"] == "apiKey"
    assert esquema["in"] == "header"
    assert esquema["name"] == "X-API-Token"

    rotas_procedimento = {
        method
        for path, ops in spec["paths"].items()
        if "/documents/" in path and "/procedures/" in path
        for method in ops
    }
    rotas_membro = {
        method
        for path, ops in spec["paths"].items()
        if "/documents/" in path and "/members/" in path
        for method in ops
    }
    assert rotas_procedimento == {"get"}
    assert rotas_membro == rotas_procedimento

    download = spec["paths"]["/api/v1/healthcare/members/{member_id}/documents/{doc_index}/download"]["get"]
    assert {"APIKeyHeader": []} in download["security"]
    assert "application/octet-stream" in download["responses"]["200"]["content"]

    schemas = spec["components"]["schemas"]
    for nome in ("FamilyMemberCreate", "FamilyMemberUpdate", "FamilyMemberDetail"):
        campo = schemas[nome]["properties"]["documents"]
        assert "base64" in campo["description"]
        assert campo["examples"] == [DOCUMENTS_EXAMPLE]
    assert "preserva" in schemas["FamilyMemberUpdate"]["properties"]["documents"]["description"]
    assert "include_documents" in {
        parametro["name"]
        for parametro in spec["paths"]["/api/v1/healthcare/members"]["get"]["parameters"]
    }


def test_api_token_envia_lista_baixa_e_preserva_anexo():
    cliente, db = _cliente()
    headers = {"X-API-Token": TOKEN}
    sem_auth = cliente.post("/api/v1/healthcare/members", json={"name": "Ana", "birth_date": "2010-01-02"})
    assert sem_auth.status_code == 401

    criado = cliente.post(
        "/api/v1/healthcare/members",
        headers=headers,
        json={"name": "Ana", "birth_date": "2010-01-02", "documents": ANEXO_JSON},
    )
    assert criado.status_code == 201, criado.text
    member_id = criado.json()["id"]
    assert json.loads(criado.json()["documents"]) == ANEXO

    lista = cliente.get("/api/v1/healthcare/members", headers=headers)
    assert lista.status_code == 200
    item = lista.json()[0]
    assert item["documents"] is None
    assert item["has_documents"] is True

    com_anexo = cliente.get(
        "/api/v1/healthcare/members",
        headers=headers,
        params={"include_documents": True, "include_photos": False},
    )
    assert json.loads(com_anexo.json()[0]["documents"]) == ANEXO

    detalhe = cliente.get(f"/api/v1/healthcare/members/{member_id}", headers=headers)
    assert detalhe.status_code == 200
    assert json.loads(detalhe.json()["documents"]) == ANEXO

    download = cliente.get(
        f"/api/v1/healthcare/members/{member_id}/documents/0/download",
        headers=headers,
    )
    assert download.status_code == 200
    assert download.content == b"a"
    assert download.headers["content-type"].startswith("application/pdf")
    assert 'filename="carteirinha.pdf"' in download.headers["content-disposition"]
    assert cliente.get(
        f"/api/v1/healthcare/members/{member_id}/documents/0/download",
    ).status_code == 401

    parcial = cliente.put(
        f"/api/v1/healthcare/members/{member_id}",
        headers=headers,
        json={"notes": "sem mexer nos anexos"},
    )
    assert parcial.status_code == 200, parcial.text
    assert json.loads(parcial.json()["documents"]) == ANEXO

    novo = [{"name": "outra.png", "type": "image/png", "size": 1, "data": "Yg=="}]
    troca = cliente.put(
        f"/api/v1/healthcare/members/{member_id}",
        headers=headers,
        json={"documents": json.dumps(novo)},
    )
    assert troca.status_code == 200
    assert json.loads(troca.json()["documents"]) == novo
    baixado = cliente.get(
        f"/api/v1/healthcare/members/{member_id}/documents/0/download",
        headers=headers,
    )
    assert baixado.content == b"b"

    limpo = cliente.put(
        f"/api/v1/healthcare/members/{member_id}",
        headers=headers,
        json={"documents": None},
    )
    assert limpo.status_code == 200
    assert limpo.json()["documents"] is None
    db.close()
