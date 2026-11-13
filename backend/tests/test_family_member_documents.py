"""Contrato do campo documents no cadastro de membro da família."""
from datetime import date

from app.schemas.healthcare import FamilyMemberCreate, FamilyMemberUpdate


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
