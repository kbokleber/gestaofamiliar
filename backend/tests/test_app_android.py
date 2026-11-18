"""Download público do app da criança em /app e envio de versão só por admin."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("SECRET_KEY", "test")

import hashlib
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import get_current_user
from app.api.v1.endpoints.app_android import router
from app.db.base import Base, get_db
from app.models.family import Family
from app.models.user import User

APK = b"PK\x03\x04" + b"conteudo-de-teste" * 100


@pytest.fixture()
def ambiente():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    agora = datetime.now(timezone.utc)
    db.add(Family(id=1, name="Bueno", codigo_unico="bueno", created_at=agora, updated_at=agora))
    db.flush()

    def usuario(**d):
        base = dict(password="x", email="", first_name="", last_name="", is_staff=False, is_superuser=False,
                    is_active=True, is_child=False, date_joined=agora, family_id=1)
        base.update(d)
        return User(**base)

    admin = usuario(id=1, username="admin", is_superuser=True)
    adulto = usuario(id=2, username="adulto")
    db.add_all([admin, adulto])
    db.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1/app-android")
    estado = {"user": admin, "anonimo": False}

    def _db():
        yield db

    def _usuario():
        if estado["anonimo"]:
            raise HTTPException(status_code=401, detail="não autenticado")
        return estado["user"]

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _usuario
    yield TestClient(app), db, estado, adulto
    db.close()


def _enviar(cliente, versao="1.0.2", conteudo=APK, nome="app-release.apk"):
    return cliente.post(
        "/api/v1/app-android/upload",
        data={"versao": versao},
        files={"arquivo": (nome, conteudo, "application/vnd.android.package-archive")},
    )


def test_sem_versao_da_404(ambiente):
    cliente, *_ = ambiente
    assert cliente.get("/api/v1/app-android/ultima").status_code == 404
    assert cliente.get("/api/v1/app-android/download").status_code == 404


def test_admin_envia_e_qualquer_um_baixa(ambiente):
    cliente, _db, estado, _adulto = ambiente
    r = _enviar(cliente)
    assert r.status_code == 201, r.text
    assert r.json()["versao"] == "1.0.2"
    assert r.json()["sha256"] == hashlib.sha256(APK).hexdigest()

    estado["anonimo"] = True  # o celular da criança baixa sem login
    info = cliente.get("/api/v1/app-android/ultima").json()
    assert info == {
        "versao": "1.0.2", "tamanho_bytes": len(APK), "sha256": hashlib.sha256(APK).hexdigest(),
        "publicado_em": info["publicado_em"], "arquivo": "/api/v1/app-android/download",
    }
    baixado = cliente.get("/api/v1/app-android/download")
    assert baixado.status_code == 200
    assert baixado.content == APK
    assert baixado.headers["content-type"] == "application/vnd.android.package-archive"
    assert 'filename="GestaoFamiliar-crianca-1.0.2.apk"' in baixado.headers["content-disposition"]


def test_versao_nova_substitui_e_guarda_so_tres(ambiente):
    from app.models.app_android import AppAndroid

    cliente, db, _estado, _adulto = ambiente
    for i in range(5):
        assert _enviar(cliente, versao=f"1.0.{i}", conteudo=APK + bytes([i])).status_code == 201
    assert cliente.get("/api/v1/app-android/ultima").json()["versao"] == "1.0.4"
    assert cliente.get("/api/v1/app-android/download").content == APK + bytes([4])
    assert db.query(AppAndroid).count() == 3


def test_so_admin_envia_e_arquivo_precisa_ser_apk(ambiente):
    cliente, _db, estado, adulto = ambiente
    assert _enviar(cliente, conteudo=b"<html>nao sou apk</html>").status_code == 422
    assert _enviar(cliente, nome="foto.png").status_code == 422
    assert _enviar(cliente, versao="1.0 beta").status_code == 422
    estado["user"] = adulto
    assert _enviar(cliente).status_code == 403
    estado["anonimo"] = True
    assert _enviar(cliente).status_code == 401
    assert cliente.get("/api/v1/app-android/ultima").status_code == 404
