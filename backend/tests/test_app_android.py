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

def apk_assinado(cert: bytes, recheio: bytes = b"conteudo-de-teste" * 100, cert_v3: bytes | None = None) -> bytes:
    """ZIP com um bloco de assinatura v2 mínimo contendo [cert] (e um v3 com [cert_v3], se dado)."""
    import io
    import struct
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("classes.dex", recheio)
    zipb = buf.getvalue()
    eocd = zipb.rfind(b"PK\x05\x06")
    (cd,) = struct.unpack_from("<I", zipb, eocd + 16)

    def lp(b: bytes) -> bytes:
        return struct.pack("<I", len(b)) + b

    def bloco(ident: int, certificado: bytes) -> bytes:
        dados_assinados = lp(b"") + lp(lp(certificado)) + lp(b"")
        assinante = lp(dados_assinados) + lp(b"") + lp(b"")
        valor = lp(lp(assinante))
        return struct.pack("<Q", 4 + len(valor)) + struct.pack("<I", ident) + valor

    par = bloco(0x7109871A, cert) + (bloco(0xF05368C0, cert_v3) if cert_v3 is not None else b"")
    tamanho = len(par) + 8 + 16
    bloco = struct.pack("<Q", tamanho) + par + struct.pack("<Q", tamanho) + b"APK Sig Block 42"
    novo = zipb[:cd] + bloco + zipb[cd:]
    eocd += len(bloco)
    return novo[:eocd + 16] + struct.pack("<I", cd + len(bloco)) + novo[eocd + 20:]


CERT_FAMILIA = b"certificado-da-familia"
APK = apk_assinado(CERT_FAMILIA)


@pytest.fixture(autouse=True)
def _assinatura_da_familia(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "APP_ASSINATURA_SHA256", hashlib.sha256(CERT_FAMILIA).hexdigest())


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
    ultima = cliente.get("/api/v1/app-android/ultima")
    assert ultima.json()["versao"] == "1.0.4"
    # Atualização dinâmica: nenhum cache guarda a versão antiga; a publicação nova aparece na hora.
    assert ultima.headers["cache-control"] == "no-store"
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


def test_so_aceita_apk_da_familia_e_nao_volta_versao(ambiente):
    from app.services.apk_assinatura import certificados, comparar_versoes

    cliente, *_ = ambiente
    assert certificados(APK) == {hashlib.sha256(CERT_FAMILIA).hexdigest()}
    # Assinado com outra chave (ex.: token vazado): recusado.
    r = _enviar(cliente, versao="9.9.9", conteudo=apk_assinado(b"chave-de-outra-pessoa"))
    assert r.status_code == 422 and "chave" in r.json()["detail"]
    # Certificado da família copiado no v2, mas v3 de outra chave: recusado (o Android usaria o v3).
    misto = apk_assinado(CERT_FAMILIA, cert_v3=b"chave-de-outra-pessoa")
    assert len(certificados(misto)) == 2
    assert _enviar(cliente, versao="9.9.9", conteudo=misto).status_code == 422
    # ZIP sem bloco de assinatura também é recusado.
    assert _enviar(cliente, conteudo=b"PK\x03\x04" + b"x" * 100).status_code == 422
    assert cliente.get("/api/v1/app-android/ultima").status_code == 404

    assert _enviar(cliente, versao="2.0.10").status_code == 201
    antiga = _enviar(cliente, versao="2.0.9")
    assert antiga.status_code == 422 and "mais antiga" in antiga.json()["detail"]
    assert _enviar(cliente, versao="2.0.10").status_code == 201  # a mesma versão pode ser reenviada
    assert _enviar(cliente, versao="2.1").status_code == 201
    assert comparar_versoes("2.0.10", "2.0.9") > 0 and comparar_versoes("2.0", "2.0.0") == 0


def test_token_de_publicacao_so_publica_e_pode_ser_revogado(ambiente):
    cliente, _db, estado, adulto = ambiente
    token = cliente.post("/api/v1/app-android/token-publicacao").json()["token"]
    assert cliente.get("/api/v1/app-android/token-publicacao").json()["ativo"] is True

    estado["anonimo"] = True  # a publicação automática não usa login
    r = cliente.post(
        "/api/v1/app-android/publicar",
        data={"versao": "2.0.0"},
        files={"arquivo": ("app.apk", APK, "application/vnd.android.package-archive")},
        headers={"X-App-Publish-Token": token},
    )
    assert r.status_code == 201, r.text
    assert cliente.get("/api/v1/app-android/ultima").json()["versao"] == "2.0.0"
    errado = cliente.post(
        "/api/v1/app-android/publicar", data={"versao": "2.0.1"},
        files={"arquivo": ("app.apk", APK, "application/octet-stream")},
        headers={"X-App-Publish-Token": "x" * 40},
    )
    assert errado.status_code == 401
    # O token não serve para mais nada: a rota de admin continua pedindo login.
    assert _enviar(cliente, versao="2.0.2").status_code == 401

    estado["anonimo"] = False
    novo = cliente.post("/api/v1/app-android/token-publicacao").json()["token"]
    assert novo != token
    estado["anonimo"] = True
    antigo = cliente.post(
        "/api/v1/app-android/publicar", data={"versao": "2.0.3"},
        files={"arquivo": ("app.apk", APK, "application/octet-stream")},
        headers={"X-App-Publish-Token": token},
    )
    assert antigo.status_code == 401  # gerar outro invalida o anterior
    estado["anonimo"] = False
    assert cliente.delete("/api/v1/app-android/token-publicacao").status_code == 204
    estado["user"] = adulto
    assert cliente.post("/api/v1/app-android/token-publicacao").status_code == 403


def test_celular_do_adulto_registra_e_recebe_avisos(ambiente):
    from app.models.user import User as U
    from app.services import avisos_app

    cliente, db, estado, adulto = ambiente
    estado["user"] = adulto
    r = cliente.post("/api/v1/app-android/dispositivos/registrar", json={"device_label": "Celular", "app_versao": 4})
    assert r.status_code == 200, r.text
    token = r.json()["device_token"]
    cab = {"X-Device-Token": token}
    assert cliente.post("/api/v1/app-android/dispositivos/avisos", json={"app_versao": 4}, headers=cab).json()["avisos"] == []

    avisos_app.enfileirar(db, db.query(U).get(2), "Localização", "Guilherme chegou na Escola", "/localizacao", tipo="alerta-x")
    db.commit()
    lista = cliente.post("/api/v1/app-android/dispositivos/avisos", json={"app_versao": 4}, headers=cab).json()["avisos"]
    assert [a["texto"] for a in lista] == ["Guilherme chegou na Escola"]
    vazio = cliente.post("/api/v1/app-android/dispositivos/avisos",
                         json={"app_versao": 4, "avisos_recebidos": [lista[0]["id"]]}, headers=cab).json()["avisos"]
    assert vazio == []
    assert cliente.post("/api/v1/app-android/dispositivos/revogar-me", headers=cab).status_code == 204
    assert cliente.post("/api/v1/app-android/dispositivos/avisos", json={}, headers=cab).status_code == 401


def test_crianca_nao_registra_celular_de_adulto(ambiente):
    from app.models.user import User as U

    cliente, db, estado, _adulto = ambiente
    agora = datetime.now(timezone.utc)
    crianca = U(id=9, username="gui", password="x", email="", first_name="Gui", last_name="", is_staff=False,
                is_superuser=False, is_active=True, is_child=True, date_joined=agora, family_id=1)
    db.add(crianca)
    db.commit()
    estado["user"] = crianca
    assert cliente.post("/api/v1/app-android/dispositivos/registrar", json={}).status_code == 403
