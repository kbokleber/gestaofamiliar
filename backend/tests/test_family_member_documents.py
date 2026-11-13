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


def test_content_disposition_usa_o_nome_real():
    from app.utils.file_response import content_disposition

    header = content_disposition("exame do joão.pdf")
    assert header.startswith("attachment;")
    assert "filename*=UTF-8''exame%20do%20jo%C3%A3o.pdf" in header
    assert 'filename="carteirinha.pdf"' in content_disposition("carteirinha.pdf")


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
    edicao = schemas["FamilyMemberEdit"]["properties"]["documents"]
    assert "index" in edicao["description"]
    assert "base64" in edicao["description"]
    parametros_edicao = {
        parametro["name"]
        for parametro in spec["paths"]["/api/v1/healthcare/members/{member_id}"]["get"]["parameters"]
    }
    assert {"include_history", "include_documents", "photo_thumb"} <= parametros_edicao
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
    corpo = detalhe.json()
    assert "appointments" not in corpo
    assert "procedures" not in corpo
    assert "medications" not in corpo
    assert json.loads(corpo["documents"]) == [
        {"index": 0, "name": "carteirinha.pdf", "type": "application/pdf", "size": 1}
    ]
    completo = cliente.get(
        f"/api/v1/healthcare/members/{member_id}",
        headers=headers,
        params={"include_documents": True, "include_history": True},
    )
    assert completo.status_code == 200
    assert json.loads(completo.json()["documents"]) == ANEXO
    assert completo.json()["appointments"] == []

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


def _jpeg_base64(largura: int, altura: int) -> str:
    import base64
    import os
    from io import BytesIO
    from PIL import Image

    imagem = Image.frombytes("RGB", (largura, altura), os.urandom(largura * altura * 3))
    buffer = BytesIO()
    imagem.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def test_editar_membro_com_anexo_nao_traz_historico_e_salvar_preserva_o_arquivo():
    """Abre a edição, altera o cadastro sem reenviar o anexo e confere o download."""
    from app.models.healthcare import MedicalAppointment, MedicalProcedure, Medication

    cliente, db = _cliente()
    headers = {"X-API-Token": TOKEN}
    foto = _jpeg_base64(900, 700)
    anexo = [{"name": "carteirinha.pdf", "type": "application/pdf", "size": 4, "data": "YQ=="}]
    criado = cliente.post(
        "/api/v1/healthcare/members",
        headers=headers,
        json={
            "name": "Ana",
            "birth_date": "1990-04-02",
            "documents": json.dumps(anexo),
            "photo": foto,
        },
    )
    assert criado.status_code == 201, criado.text
    member_id = criado.json()["id"]

    agora = datetime.now(timezone.utc)
    blob_consulta = "C" * 80_000
    blob_exame = "E" * 80_000
    blob_remedio = "R" * 40_000
    db.add(MedicalAppointment(
        family_member_id=member_id,
        doctor_name="Dra. Luz",
        specialty="Clínica",
        appointment_date=agora,
        location="Clínica",
        reason="retorno",
        diagnosis="",
        prescription="",
        notes="",
        documents=json.dumps([{"name": "consulta.pdf", "type": "application/pdf", "size": 80_000, "data": blob_consulta}]),
        created_at=agora,
        updated_at=agora,
    ))
    db.add(MedicalProcedure(
        family_member_id=member_id,
        procedure_name="Hemograma",
        procedure_date=agora,
        doctor_name="Dra. Luz",
        location="Lab",
        description="coleta",
        results="",
        follow_up_notes="",
        documents=json.dumps([{"name": "exame.pdf", "type": "application/pdf", "size": 80_000, "data": blob_exame}]),
        created_at=agora,
        updated_at=agora,
    ))
    db.add(Medication(
        family_member_id=member_id,
        name="Vitamina",
        dosage="1cp",
        frequency="once",
        start_date=date(2026, 1, 1),
        prescribed_by="",
        prescription_number="",
        instructions="",
        side_effects="",
        notes="",
        documents=json.dumps([{"name": "receita.pdf", "type": "application/pdf", "size": 40_000, "data": blob_remedio}]),
        created_at=agora,
        updated_at=agora,
    ))
    db.commit()
    db.expire_all()

    leve = cliente.get(f"/api/v1/healthcare/members/{member_id}", headers=headers)
    assert leve.status_code == 200, leve.text
    corpo = leve.json()
    assert "appointments" not in corpo
    assert "procedures" not in corpo
    assert "medications" not in corpo
    assert blob_consulta not in leve.text
    assert blob_exame not in leve.text
    assert blob_remedio not in leve.text
    meta = json.loads(corpo["documents"])
    assert meta == [{"index": 0, "name": "carteirinha.pdf", "type": "application/pdf", "size": 4}]
    assert "data" not in meta[0]
    assert corpo["photo"]
    assert len(corpo["photo"]) < len(foto) / 5

    antigo = cliente.get(
        f"/api/v1/healthcare/members/{member_id}",
        headers=headers,
        params={"include_history": True, "include_documents": True, "photo_thumb": False},
    )
    assert antigo.status_code == 200
    assert blob_consulta in antigo.text
    assert blob_exame in antigo.text
    assert blob_remedio in antigo.text
    assert antigo.json()["photo"] == foto
    assert len(leve.content) < len(antigo.content) / 5, (len(leve.content), len(antigo.content))

    # Salvar o cadastro sem o campo documents, como a tela faz quando a lista não mudou.
    salvo = cliente.put(
        f"/api/v1/healthcare/members/{member_id}",
        headers=headers,
        json={"name": "Ana Maria", "notes": "sem mexer nos anexos"},
    )
    assert salvo.status_code == 200, salvo.text
    assert salvo.json()["name"] == "Ana Maria"
    assert json.loads(salvo.json()["documents"]) == anexo
    baixado = cliente.get(
        f"/api/v1/healthcare/members/{member_id}/documents/0/download",
        headers=headers,
    )
    assert baixado.status_code == 200
    assert baixado.content == b"a"

    # Reenviar só os metadados que a edição recebeu também não pode apagar o arquivo.
    reenvio = cliente.put(
        f"/api/v1/healthcare/members/{member_id}",
        headers=headers,
        json={"documents": corpo["documents"]},
    )
    assert reenvio.status_code == 200, reenvio.text
    assert cliente.get(
        f"/api/v1/healthcare/members/{member_id}/documents/0/download",
        headers=headers,
    ).content == b"a"

    # Troca de lista: o antigo segue pelo index e o novo vai com data.
    novo = {
        "name": "receita-nova.pdf",
        "type": "application/pdf",
        "size": 1,
        "data": "Yg==",
    }
    troca = cliente.put(
        f"/api/v1/healthcare/members/{member_id}",
        headers=headers,
        json={"documents": json.dumps([meta[0], novo])},
    )
    assert troca.status_code == 200, troca.text
    assert cliente.get(
        f"/api/v1/healthcare/members/{member_id}/documents/0/download",
        headers=headers,
    ).content == b"a"
    assert cliente.get(
        f"/api/v1/healthcare/members/{member_id}/documents/1/download",
        headers=headers,
    ).content == b"b"

    invalido = cliente.put(
        f"/api/v1/healthcare/members/{member_id}",
        headers=headers,
        json={"documents": json.dumps([{"index": 9, "name": "sumiu.pdf", "type": "application/pdf", "size": 1}])},
    )
    assert invalido.status_code == 400
    assert cliente.get(
        f"/api/v1/healthcare/members/{member_id}/documents/0/download",
        headers=headers,
    ).content == b"a"
    db.close()
