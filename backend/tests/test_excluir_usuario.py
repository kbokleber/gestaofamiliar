"""Excluir usuário: o banco decide antes do Keycloak, e nunca sobra exclusão pela metade."""
from datetime import date, datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import get_current_admin, get_current_user
from app.api.v1.endpoints import users
from app.core.keycloak_admin import KeycloakAdminError
from app.db.base import Base, get_db
from app.models.family import Family
from app.models.healthcare import FamilyMember
from app.models.location import LocationChildSettings, LocationDevice
from app.models.user import Profile, User


@pytest.fixture()
def ambiente(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    event.listen(engine, "connect", lambda conexao, _: conexao.execute("PRAGMA foreign_keys=ON"))  # como o Postgres
    Base.metadata.create_all(bind=engine)
    fabrica = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    db = fabrica()
    agora = datetime.now(timezone.utc)
    db.add(Family(id=1, name="F", codigo_unico="f", created_at=agora, updated_at=agora))
    db.flush()
    for id_, nome, admin in ((1, "admin", True), (16, "gui", False)):
        db.add(User(id=id_, username=nome, password="x", email="", first_name=nome, last_name="", is_staff=False, is_superuser=admin,
                    is_active=True, is_child=not admin, date_joined=agora, family_id=1))
    db.flush()
    db.add(Profile(user_id=16, created_at=agora))
    db.add(FamilyMember(id=101, name="G", family_id=1, birth_date=date(2012, 1, 2), created_at=agora, updated_at=agora))
    db.commit()
    app = FastAPI()
    app.include_router(users.router, prefix="/u")

    def _db():
        sessao = fabrica()
        try:
            yield sessao
        finally:
            sessao.close()

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = app.dependency_overrides[get_current_admin] = lambda: db.get(User, 1)
    no_keycloak = []
    monkeypatch.setattr(users.settings, "AUTH_KEYCLOAK_ENABLED", True)
    monkeypatch.setattr(users, "delete_keycloak_user", no_keycloak.append)
    yield TestClient(app, raise_server_exceptions=False), db, no_keycloak, monkeypatch
    db.close()


def _existe(db):
    db.expire_all()
    return db.get(User, 16) is not None, db.query(Profile).filter(Profile.user_id == 16).count() == 1


def _pref(db, membro):
    db.add(LocationChildSettings(child_user_id=16, family_id=1, apelido="Gui", family_member_id=membro))
    db.commit()


@pytest.mark.parametrize("preparar", [lambda db: None, lambda db: _pref(db, 101), lambda db: _pref(db, None)],
                         ids=["nunca teve vínculo", "com vínculo", "vínculo já tirado"])
def test_exclui_com_ou_sem_vinculo_de_foto(ambiente, preparar):
    cliente, db, no_keycloak, _ = ambiente
    preparar(db)
    r = cliente.delete("/u/16")
    assert (r.status_code, r.json()) == (200, {"message": "Usuário excluído com sucesso"})
    assert _existe(db) == (False, False) and no_keycloak == ["gui"]
    assert db.query(LocationChildSettings).count() == 0
    assert db.get(FamilyMember, 101) is not None  # o membro da família fica


def test_com_dados_ligados_responde_409_e_nao_toca_no_keycloak(ambiente):
    cliente, db, no_keycloak, _ = ambiente
    _pref(db, 101)
    db.add(LocationDevice(family_id=1, child_user_id=16, token_hash="h", label="Celular"))
    db.commit()
    r = cliente.delete("/u/16")
    assert r.status_code == 409 and "Desative" in r.json()["detail"]
    assert "FOREIGN" not in r.text and "location_device" not in r.text
    assert no_keycloak == [] and _existe(db) == (True, True)
    assert db.get(LocationChildSettings, 16).family_member_id == 101  # nada pela metade


def test_se_o_keycloak_falha_o_banco_fica_como_estava(ambiente):
    cliente, db, _, monkeypatch = ambiente
    _pref(db, 101)

    def falha(_usuario):
        raise KeycloakAdminError("segredo interno", status_code=502)

    monkeypatch.setattr(users, "delete_keycloak_user", falha)
    r = cliente.delete("/u/16")
    assert r.status_code == 502 and "segredo" not in r.text
    assert _existe(db) == (True, True) and db.get(LocationChildSettings, 16).family_member_id == 101


def test_o_banco_aceita_antes_de_chamar_o_keycloak(ambiente):
    cliente, db, _, monkeypatch = ambiente
    ordem = []
    event.listen(db.get_bind(), "before_cursor_execute", lambda c, cur, sql, *a: ordem.append("banco") if sql.startswith("DELETE FROM auth_user") else None)
    monkeypatch.setattr(users, "delete_keycloak_user", lambda u: ordem.append("keycloak"))
    assert cliente.delete("/u/16").status_code == 200
    assert ordem == ["banco", "keycloak"]


def test_o_que_ja_era_recusado_continua(ambiente):
    cliente, _, no_keycloak, _ = ambiente
    assert cliente.delete("/u/999").status_code == 404
    assert cliente.delete("/u/1").status_code == 400
    assert no_keycloak == []
