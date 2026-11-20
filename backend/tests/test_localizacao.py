"""Localização das crianças: pareamento, bateria, lugares e trajeto."""
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/db")
os.environ.setdefault("SECRET_KEY", "test")

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.api.deps import get_current_user
from app.api.v1.endpoints.localizacao import router
from app.core.menus import aplicar_perfil_menus, normalize_menus
from app.db.base import Base, get_db
from app.models.family import Family
from app.models.location import LocationPairingCode
from app.models.user import User
from app.services import localizacao as servico
from app.services.localizacao import (
    EnderecoNaoEncontrado,
    GeocodificacaoIndisponivel,
    calcular_trajeto,
    distancia_m,
    escolher_lugar,
    frase_evento,
    sugerir_preposicao,
)


def _ponto(**dados):
    base = dict(
        id=1, device_id=1, accuracy_m=10, speed_mps=None, battery_level=80,
        latitude=0, longitude=0, recorded_at=datetime(2026, 11, 18, 15, tzinfo=timezone.utc),
    )
    base.update(dados)
    return SimpleNamespace(**base)


def test_menus_de_localizacao_sao_so_para_adulto():
    assert normalize_menus(["localizacao", "estudos"]) == ["estudos", "localizacao"]
    with pytest.raises(ValueError):
        normalize_menus(["inexistente"])
    assert aplicar_perfil_menus(["estudos", "localizacao"], is_child=True) == ["estudos"]
    assert aplicar_perfil_menus(["localizacao"], is_child=False) == ["localizacao"]
    assert aplicar_perfil_menus(None, is_child=True) is None


def test_frases_e_lugar_mais_especifico():
    assert sugerir_preposicao("Escola Municipal") == "na"
    assert sugerir_preposicao("Parque") == "no"
    assert sugerir_preposicao("Casa") == "em"
    assert frase_evento("chegada", "na", "Escola") == "Chegou na Escola"
    assert frase_evento("saida", "na", "Escola") == "Saiu da Escola"
    assert frase_evento("saida", "em", "Casa") == "Saiu de Casa"

    casa = SimpleNamespace(id=1, nome="Casa", preposicao="em", latitude=-23.55, longitude=-46.63, raio_m=120)
    area = SimpleNamespace(id=2, nome="Bairro", preposicao="no", latitude=-23.55, longitude=-46.63, raio_m=800)
    assert escolher_lugar(-23.55, -46.63, [area, casa]).id == 1
    assert escolher_lugar(-23.50, -46.60, [casa, area]) is None


def test_trajeto_calcula_distancia_velocidade_parada_e_ignora_lacuna():
    inicio = datetime(2026, 11, 18, 15, 0, tzinfo=timezone.utc)
    um_km = 1000 / 111_320
    pontos = [
        _ponto(id=1, latitude=-23.55 - um_km, longitude=-46.63, recorded_at=inicio, speed_mps=None),
        _ponto(id=2, latitude=-23.55, longitude=-46.63, recorded_at=inicio + timedelta(minutes=5), speed_mps=10),
        _ponto(id=3, latitude=-23.55, longitude=-46.63, recorded_at=inicio + timedelta(minutes=10), speed_mps=0),
        _ponto(id=4, latitude=-23.55, longitude=-46.63, recorded_at=inicio + timedelta(minutes=15), speed_mps=0),
    ]
    trajeto = calcular_trajeto(pontos)
    esperado = distancia_m(pontos[0].latitude, pontos[0].longitude, pontos[1].latitude, pontos[1].longitude)
    assert trajeto["distancia_m"] == pytest.approx(esperado, abs=1)
    assert trajeto["velocidade_maxima_kmh"] == pytest.approx(36.0, abs=0.1)
    assert trajeto["velocidade_media_kmh"] == pytest.approx(esperado / 300 * 3.6, abs=0.2)
    assert trajeto["fonte_velocidade"] == "gps"
    assert len(trajeto["paradas"]) == 1
    assert trajeto["paradas"][0]["duracao_segundos"] == 600

    longe = _ponto(
        id=2,
        latitude=-23.55 + (50_000 / 111_320),
        recorded_at=inicio + timedelta(hours=2),
    )
    lacuna = calcular_trajeto([pontos[0], longe])
    assert lacuna["distancia_m"] == 0
    assert lacuna["pontos"][1]["lacuna_antes"] is True


@pytest.fixture()
def ambiente(monkeypatch):
    monkeypatch.setattr(
        servico,
        "consultar_nominatim",
        lambda consulta, countrycodes=None: {
            "latitude": -23.56,
            "longitude": -46.64,
            "endereco_formatado": "Escola, São Paulo",
        },
    )
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    # Igual à API (app/db/base.py): sem autoflush, para pegar erros que só aparecem em produção.
    db = sessionmaker(bind=engine, autocommit=False, autoflush=False)()
    agora = datetime.now(timezone.utc)
    db.add_all([
        Family(id=1, name="Bueno", codigo_unico="bueno", created_at=agora, updated_at=agora),
        Family(id=2, name="Outra", codigo_unico="outra", created_at=agora, updated_at=agora),
    ])
    db.flush()

    def usuario(**dados):
        base = dict(
            password="x", email="", first_name="", last_name="", is_staff=False,
            is_superuser=False, is_active=True, is_child=False, date_joined=agora,
        )
        base.update(dados)
        return User(**base)

    kleber = usuario(id=1, username="kleber", first_name="Kleber", family_id=1, is_superuser=True)
    tia = usuario(id=2, username="tia", first_name="Tia", family_id=1, allowed_menus=["estudos"])
    mae = usuario(id=3, username="mae", first_name="Mãe", family_id=1, allowed_menus=["localizacao"])
    gui = usuario(id=16, username="guilherme", first_name="Guilherme", family_id=1, is_child=True, allowed_menus=["estudos"])
    gio = usuario(id=17, username="giovana", first_name="Giovana", family_id=1, is_child=True, allowed_menus=["estudos"])
    primo = usuario(id=18, username="primo", first_name="Primo", family_id=2, is_child=True, allowed_menus=["estudos"])
    db.add_all([kleber, tia, mae, gui, gio, primo])
    db.commit()

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/localizacao")
    estado = {"user": kleber, "anonimo": False}

    def _db():
        yield db

    def _usuario():
        if estado["anonimo"]:
            raise HTTPException(status_code=401, detail="Não foi possível validar as credenciais")
        return estado["user"]

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _usuario
    cliente = TestClient(app)
    yield cliente, db, estado
    db.close()


def _iso(momento: datetime) -> str:
    return momento.isoformat()


def _parear(cliente, child_id, rotulo):
    codigo = cliente.post("/api/v1/localizacao/pareamentos", json={"child_user_id": child_id})
    assert codigo.status_code == 200, codigo.text
    troca = cliente.post(
        "/api/v1/localizacao/dispositivos/parear",
        json={"code": codigo.json()["codigo"].lower(), "device_label": rotulo},
    )
    assert troca.status_code == 200, troca.text
    return troca.json()


def _enviar(cliente, token, **corpo):
    return cliente.post(
        "/api/v1/localizacao/dispositivos/posicao",
        json=corpo,
        headers={"X-Device-Token": token},
    )


def test_familia_ve_bateria_frase_trajeto_e_nao_ve_adulto(ambiente):
    cliente, db, estado = ambiente
    casa = (-23.55, -46.63)
    escola = (-23.56, -46.64)
    um_km = 1000 / 111_320
    fora = (casa[0] - um_km, casa[1])
    base = datetime.now(servico.FUSO).replace(hour=12, minute=0, second=0, microsecond=0)
    if base > datetime.now(servico.FUSO):
        base = base - timedelta(days=1)
    dia = base.date().isoformat()

    for corpo in (
        {"nome": "Casa", "preposicao": "em", "endereco": "Rua da Casa, 10", "latitude": casa[0], "longitude": casa[1], "raio_m": 150},
        {"nome": "Escola", "preposicao": "na", "endereco": "Rua da Escola, 20", "latitude": escola[0], "longitude": escola[1], "raio_m": 150},
    ):
        criado = cliente.post("/api/v1/localizacao/lugares", json=corpo)
        assert criado.status_code == 201, criado.text

    gui = _parear(cliente, 16, "Celular do Gui")
    gio = _parear(cliente, 17, "Celular da Gio")
    assert "device_token" in gui
    assert cliente.post("/api/v1/localizacao/dispositivos/parear", json={"code": "AAAA-AAAA"}).status_code == 400

    primeiro = _enviar(
        cliente, gui["device_token"],
        latitude=fora[0], longitude=fora[1], accuracy_m=12, battery_level=90,
        recorded_at=_iso(base),
    )
    assert primeiro.status_code == 200, primeiro.text
    lista = cliente.get("/api/v1/localizacao/criancas")
    assert lista.status_code == 200
    por_nome = {item["nome"]: item for item in lista.json()}
    assert set(por_nome) == {"Guilherme", "Giovana"}
    assert por_nome["Guilherme"]["status"]["frase"] == "Guilherme está fora dos lugares cadastrados"
    assert por_nome["Guilherme"]["bateria"] == 90
    assert por_nome["Giovana"]["status"]["frase"] == "Giovana ainda não enviou localização"

    chegada = _enviar(
        cliente, gui["device_token"],
        latitude=casa[0], longitude=casa[1], accuracy_m=8, speed_mps=10, battery_level=80,
        recorded_at=_iso(base + timedelta(minutes=5)),
    )
    repetido = _enviar(
        cliente, gui["device_token"],
        latitude=casa[0], longitude=casa[1], accuracy_m=8, speed_mps=10, battery_level=80,
        recorded_at=_iso(base + timedelta(minutes=5)),
    )
    assert repetido.json()["repetido"] is True
    assert repetido.json()["id"] == chegada.json()["id"]
    _enviar(
        cliente, gui["device_token"],
        latitude=casa[0], longitude=casa[1], battery_level=78, speed_mps=0,
        recorded_at=_iso(base + timedelta(minutes=10)),
    )
    _enviar(
        cliente, gui["device_token"],
        latitude=casa[0], longitude=casa[1], battery_level=76, speed_mps=0, accuracy_m=5,
        recorded_at=_iso(base + timedelta(minutes=15)),
    )

    lista = cliente.get("/api/v1/localizacao/criancas").json()
    guilherme = next(item for item in lista if item["nome"] == "Guilherme")
    assert guilherme["status"]["frase"] == "Guilherme está em Casa"
    assert guilherme["bateria"] == 76
    assert guilherme["aparelhos"][0]["bateria"] == 76
    assert guilherme["aparelhos"][0]["nome"] == "Celular do Gui"
    assert "device_token" not in cliente.get("/api/v1/localizacao/criancas").text
    assert gui["device_token"] not in cliente.get("/api/v1/localizacao/criancas").text

    trajeto = cliente.get("/api/v1/localizacao/criancas/16/trajeto", params={"dia": dia})
    assert trajeto.status_code == 200, trajeto.text
    corpo = trajeto.json()
    percorrido = distancia_m(fora[0], fora[1], casa[0], casa[1])
    assert corpo["distancia_m"] == pytest.approx(percorrido, abs=1)
    assert corpo["velocidade_maxima_kmh"] == pytest.approx(36.0, abs=0.1)
    assert corpo["velocidade_media_kmh"] == pytest.approx(percorrido / 300 * 3.6, abs=0.2)
    assert len(corpo["paradas"]) == 1
    assert [evento["frase"] for evento in corpo["eventos"]] == ["Chegou em Casa"]
    assert len(corpo["pontos"]) == 4

    ontem = cliente.get(
        "/api/v1/localizacao/criancas/16/trajeto",
        params={"dia": (base.date() - timedelta(days=1)).isoformat()},
    )
    assert ontem.json()["pontos"] == []

    na_escola = _enviar(
        cliente, gio["device_token"],
        latitude=escola[0], longitude=escola[1], accuracy_m=15, battery_level=40,
        recorded_at=_iso(base + timedelta(minutes=20)),
    )
    assert na_escola.status_code == 200
    giovana = next(item for item in cliente.get("/api/v1/localizacao/criancas").json() if item["nome"] == "Giovana")
    assert giovana["status"]["frase"] == "Giovana está na Escola"
    assert giovana["bateria"] == 40
    assert cliente.get("/api/v1/localizacao/criancas/17/trajeto", params={"dia": dia}).json()["eventos"] == []

    _enviar(
        cliente, gio["device_token"],
        latitude=fora[0], longitude=fora[1], battery_level=39,
        recorded_at=_iso(base + timedelta(minutes=30)),
    )
    eventos_gio = cliente.get("/api/v1/localizacao/criancas/17/trajeto", params={"dia": dia}).json()["eventos"]
    assert [evento["frase"] for evento in eventos_gio] == ["Saiu da Escola"]

    casa_id = next(lugar["id"] for lugar in cliente.get("/api/v1/localizacao/lugares").json() if lugar["nome"] == "Casa")
    editado = cliente.put(f"/api/v1/localizacao/lugares/{casa_id}", json={
        "nome": "Lar", "preposicao": "no", "endereco": "Rua da Casa, 10",
        "latitude": casa[0], "longitude": casa[1], "raio_m": 150,
    })
    assert editado.status_code == 200
    guilherme = next(item for item in cliente.get("/api/v1/localizacao/criancas").json() if item["nome"] == "Guilherme")
    assert guilherme["status"]["frase"] == "Guilherme está no Lar"
    historico = cliente.get("/api/v1/localizacao/criancas/16/trajeto", params={"dia": dia}).json()["eventos"]
    assert historico[0]["frase"] == "Chegou em Casa"

    estado["user"] = db.get(User, 3)
    assert cliente.get("/api/v1/localizacao/criancas").status_code == 200
    estado["user"] = db.get(User, 2)
    assert cliente.get("/api/v1/localizacao/criancas").status_code == 403
    estado["user"] = db.get(User, 16)
    bloqueio = cliente.get("/api/v1/localizacao/criancas")
    assert bloqueio.status_code == 403
    assert "adultos" in bloqueio.json()["detail"]
    estado["user"] = db.get(User, 1)

    assert cliente.post("/api/v1/localizacao/pareamentos", json={"child_user_id": 1}).status_code == 404
    assert cliente.post("/api/v1/localizacao/pareamentos", json={"child_user_id": 18}).status_code == 404
    assert cliente.get("/api/v1/localizacao/criancas/18/trajeto").status_code == 404
    assert cliente.delete("/api/v1/localizacao/lugares/999").status_code == 404

    estado["anonimo"] = True
    assert cliente.get("/api/v1/localizacao/criancas").status_code == 401
    estado["anonimo"] = False
    assert _enviar(cliente, gui["device_token"], latitude=120, longitude=0).status_code == 422
    assert _enviar(
        cliente, gui["device_token"], latitude=casa[0], longitude=casa[1], speed_mps=500, battery_level=70,
        recorded_at=_iso(base + timedelta(minutes=40)),
    ).status_code == 200

    revogado = cliente.post(f"/api/v1/localizacao/dispositivos/{gui['device_id']}/revogar")
    assert revogado.status_code == 200
    assert _enviar(
        cliente, gui["device_token"], latitude=casa[0], longitude=casa[1], battery_level=10,
        recorded_at=_iso(base + timedelta(minutes=45)),
    ).status_code == 401

    proprio = cliente.post(
        "/api/v1/localizacao/dispositivos/revogar-me",
        headers={"X-Device-Token": gio["device_token"]},
    )
    assert proprio.status_code == 200
    assert _enviar(
        cliente, gio["device_token"], latitude=escola[0], longitude=escola[1],
        recorded_at=_iso(base + timedelta(minutes=50)),
    ).status_code == 401


def test_codigo_expirado_e_geocodificacao(ambiente, monkeypatch):
    cliente, db, estado = ambiente
    codigo = cliente.post("/api/v1/localizacao/pareamentos", json={"child_user_id": 16})
    assert codigo.status_code == 200
    registro = db.query(LocationPairingCode).one()
    registro.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()
    recusado = cliente.post("/api/v1/localizacao/dispositivos/parear", json={"code": codigo.json()["codigo"]})
    assert recusado.status_code == 400
    assert "expirado" in recusado.json()["detail"]

    busca = cliente.post("/api/v1/localizacao/lugares/geocodificar", json={"endereco": "Escola da Giovana"})
    assert busca.status_code == 200
    assert busca.json()["endereco_formatado"] == "Escola, São Paulo"

    monkeypatch.setattr(servico, "consultar_nominatim", lambda consulta, countrycodes=None: None)
    vazio = cliente.post("/api/v1/localizacao/lugares/geocodificar", json={"endereco": "lugar nenhum"})
    assert vazio.status_code == 404

    def falha(consulta, countrycodes=None):
        raise GeocodificacaoIndisponivel()

    monkeypatch.setattr(servico, "consultar_nominatim", falha)
    indisponivel = cliente.post("/api/v1/localizacao/lugares/geocodificar", json={"endereco": "Rua sem mapa"})
    assert indisponivel.status_code == 503


def test_horario_futuro_ou_antigo_demais(ambiente):
    cliente, _, _ = ambiente
    token = _parear(cliente, 16, "Celular")["device_token"]
    agora = datetime.now(timezone.utc)
    futuro = _enviar(
        cliente, token, latitude=-23.5, longitude=-46.6,
        recorded_at=_iso(agora + timedelta(hours=2)),
    )
    assert futuro.status_code == 400
    antigo = _enviar(
        cliente, token, latitude=-23.5, longitude=-46.6,
        recorded_at=_iso(agora - timedelta(days=8)),
    )
    assert antigo.status_code == 400


def test_geocodificar_sem_resultado_duas_tentativas(monkeypatch):
    chamadas = []

    def consulta(texto, countrycodes=None):
        chamadas.append(countrycodes)
        if countrycodes is None:
            return {"latitude": 1.0, "longitude": 2.0, "endereco_formatado": "Fora"}
        return None

    monkeypatch.setattr(servico, "consultar_nominatim", consulta)
    assert servico.geocodificar_endereco("Rua Distante")["endereco_formatado"] == "Fora"
    assert chamadas == ["br", None]
    with pytest.raises(EnderecoNaoEncontrado):
        servico.geocodificar_endereco("  ")


@pytest.fixture(autouse=True)
def _zerar_limites():
    from app.api.v1.endpoints import localizacao as rotas

    rotas.limite_pareamento_ip.zerar()
    rotas.limite_pareamento_total.zerar()
    yield
    rotas.limite_pareamento_ip.zerar()
    rotas.limite_pareamento_total.zerar()


def test_pareamento_limita_tentativas_por_ip(ambiente):
    cliente, _db, _estado = ambiente
    cabecalho = {"X-Forwarded-For": "200.1.1.1, 10.0.0.2"}  # cliente visto pelo Traefik, IP do Traefik
    for _ in range(10):
        errado = cliente.post(
            "/api/v1/localizacao/dispositivos/parear", json={"code": "ZZZZ-ZZZZ"}, headers=cabecalho
        )
        assert errado.status_code == 400
    bloqueado = cliente.post(
        "/api/v1/localizacao/dispositivos/parear", json={"code": "ZZZZ-ZZZZ"}, headers=cabecalho
    )
    assert bloqueado.status_code == 429
    assert "15 minutos" in bloqueado.json()["detail"]

    # Outro IP ainda consegue parear com um código válido.
    codigo = cliente.post("/api/v1/localizacao/pareamentos", json={"child_user_id": 16}).json()["codigo"]
    outro = cliente.post(
        "/api/v1/localizacao/dispositivos/parear",
        json={"code": codigo},
        headers={"X-Forwarded-For": "200.2.2.2, 10.0.0.2"},
    )
    assert outro.status_code == 200, outro.text


def test_limite_tentativas_libera_depois_da_janela():
    from app.services.limite_tentativas import LimiteTentativas

    limite = LimiteTentativas(maximo=2, janela_segundos=60)
    limite.registrar("ip", agora=0)
    limite.registrar("ip", agora=1)
    assert limite.excedido("ip", agora=2)
    assert not limite.excedido("ip", agora=61)


def test_historico_antigo_e_apagado(ambiente):
    from app.models.location import LocationPlaceEvent, LocationPoint

    cliente, db, _estado = ambiente
    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63, battery_level=50).status_code == 200
    ponto = db.query(LocationPoint).first()
    agora = datetime.now(timezone.utc)
    velho = LocationPoint(
        device_id=ponto.device_id, family_id=1, child_user_id=16, latitude=-23.5, longitude=-46.6,
        recorded_at=agora - timedelta(days=91), received_at=agora - timedelta(days=91),
    )
    evento_velho = LocationPlaceEvent(
        family_id=1, child_user_id=16, device_id=ponto.device_id, place_id=None, lugar_nome="Casa",
        preposicao="em", tipo="chegada", recorded_at=agora - timedelta(days=95), latitude=-23.55, longitude=-46.63,
    )
    db.add_all([velho, evento_velho])
    db.commit()

    resultado = servico.limpar_historico_antigo(db, agora)
    db.commit()
    assert resultado["pontos"] == 1
    assert resultado["eventos"] == 1
    assert resultado["codigos"] >= 1  # o código já usado no pareamento
    assert db.query(LocationPoint).count() == 1


def test_celular_revogado_quando_crianca_muda_de_familia(ambiente):
    cliente, db, _estado = ambiente
    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63).status_code == 200

    gui = db.query(User).filter(User.id == 16).first()
    gui.family_id = 2
    db.commit()

    recusado = _enviar(cliente, token, latitude=-23.55, longitude=-46.63)
    assert recusado.status_code == 401
    from app.models.location import LocationDevice

    assert db.query(LocationDevice).filter(LocationDevice.child_user_id == 16).first().revoked_at is not None


def test_apelido_no_mapa(ambiente):
    cliente, _db, estado = ambiente
    salvo = cliente.put("/api/v1/localizacao/criancas/16/apelido", json={"apelido": "  Gui  "})
    assert salvo.status_code == 200, salvo.text
    assert salvo.json() == {"crianca_id": 16, "apelido": "Gui"}
    assert cliente.put("/api/v1/localizacao/criancas/17/apelido", json={"apelido": "Gi"}).status_code == 200
    apelidos = {c["id"]: c["apelido"] for c in cliente.get("/api/v1/localizacao/criancas").json()}
    assert apelidos == {16: "Gui", 17: "Gi"}

    # Vazio volta a não ter apelido; criança de outra família não é alcançada.
    assert cliente.put("/api/v1/localizacao/criancas/17/apelido", json={"apelido": ""}).json()["apelido"] is None
    assert cliente.put("/api/v1/localizacao/criancas/18/apelido", json={"apelido": "X"}).status_code == 404
    assert cliente.put("/api/v1/localizacao/criancas/16/apelido", json={"apelido": "x" * 13}).status_code == 422


def test_ip_falso_no_x_forwarded_for_nao_dribla_o_limite(ambiente):
    cliente, _db, _estado = ambiente
    # O atacante inventa um IP diferente a cada pedido no começo do cabeçalho;
    # o Traefik acrescenta o IP real (203.0.113.7) e o nginx o do Traefik.
    for i in range(10):
        r = cliente.post(
            "/api/v1/localizacao/dispositivos/parear",
            json={"code": "ZZZZ-ZZZZ"},
            headers={"X-Forwarded-For": f"1.2.3.{i}, 203.0.113.7, 10.0.0.2"},
        )
        assert r.status_code == 400
    bloqueado = cliente.post(
        "/api/v1/localizacao/dispositivos/parear",
        json={"code": "ZZZZ-ZZZZ"},
        headers={"X-Forwarded-For": "9.9.9.9, 203.0.113.7, 10.0.0.2"},
    )
    assert bloqueado.status_code == 429

    # Quem está em outro IP continua conseguindo parear.
    codigo = cliente.post("/api/v1/localizacao/pareamentos", json={"child_user_id": 16}).json()["codigo"]
    legitimo = cliente.post(
        "/api/v1/localizacao/dispositivos/parear",
        json={"code": codigo},
        headers={"X-Forwarded-For": "200.9.9.9, 10.0.0.2"},
    )
    assert legitimo.status_code == 200, legitimo.text


def test_ip_do_pedido_le_de_tras_para_frente():
    from starlette.requests import Request
    from app.services.limite_tentativas import ip_do_pedido

    def pedido(xff):
        cab = [(b"x-forwarded-for", xff.encode())] if xff is not None else []
        return Request({"type": "http", "headers": cab, "client": ("10.0.0.2", 1)})

    assert ip_do_pedido(pedido("1.1.1.1, 203.0.113.7, 10.0.0.2")) == "203.0.113.7"
    assert ip_do_pedido(pedido("203.0.113.7, 10.0.0.2")) == "203.0.113.7"
    assert ip_do_pedido(pedido("203.0.113.7")) == "203.0.113.7"
    assert ip_do_pedido(pedido(None)) == "10.0.0.2"



def _atividade_de_hoje(db, aluno_id, titulo):
    from app.models.estudo import Atividade

    agora = datetime.now(timezone.utc)
    atividade = Atividade(
        aluno_id=aluno_id, family_id=1, titulo=titulo, descricao="", professor="",
        data=agora.date(), tipo="atividade", prazo_entrega=agora + timedelta(hours=2),
        created_at=agora, updated_at=agora,
    )
    db.add(atividade)
    db.commit()
    return atividade


_SEGUNDOS = iter(range(10_000))


def _enviar_app(cliente, token, recebidos=(), versao=3, notificacoes=True):
    """Envio como o app 1.0.2 faz: versão, notificações e avisos já mostrados."""
    momento = datetime.now(timezone.utc) - timedelta(minutes=10) + timedelta(seconds=next(_SEGUNDOS) * 2)
    return cliente.post(
        "/api/v1/localizacao/dispositivos/posicao",
        json={
            "latitude": -23.55, "longitude": -46.63, "recorded_at": _iso(momento),
            "app_versao": versao, "notificacoes": notificacoes, "avisos_recebidos": list(recebidos),
        },
        headers={"X-Device-Token": token},
    )


def _inscrever_navegador(db, user_id):
    from app.models.lembrete import PushInscricao

    db.add(PushInscricao(user_id=user_id, endpoint=f"https://push.example/{user_id}", p256dh="x", auth="y"))
    db.commit()


def test_lembrete_pelo_app_volta_ate_ser_confirmado(ambiente):
    from app.services import lembrete

    cliente, db, _estado = ambiente
    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    assert _enviar_app(cliente, token).json()["avisos"] == []
    _atividade_de_hoje(db, 16, "Lição de matemática")
    _atividade_de_hoje(db, 17, "Redação")

    resultado = lembrete.disparar_familia(db, 1)
    assert resultado["enviados"] == [
        {"filho": "Guilherme", "tarefas": ["Lição de matemática"], "canal": "app"},
    ]
    assert resultado["sem_inscricao"] == ["Giovana"]

    primeira = _enviar_app(cliente, token).json()["avisos"]
    assert len(primeira) == 1
    aviso = primeira[0]
    assert aviso["titulo"] == "Atividades para concluir"
    assert "Lição de matemática" in aviso["texto"]
    assert aviso["url"] == "/estudos/atividades?recorte=pendentes"

    # Resposta perdida: sem confirmação, o mesmo aviso volta.
    assert [a["id"] for a in _enviar_app(cliente, token).json()["avisos"]] == [aviso["id"]]
    # Confirmado, não volta mais.
    assert _enviar_app(cliente, token, recebidos=[aviso["id"]]).json()["avisos"] == []
    assert _enviar_app(cliente, token).json()["avisos"] == []


def test_app_antigo_parado_ou_sem_notificacao_usa_o_navegador(ambiente):
    from app.models.location import LocationDevice
    from app.services import lembrete

    cliente, db, _estado = ambiente
    _inscrever_navegador(db, 16)
    gui = db.query(User).filter(User.id == 16).first()
    token = _parear(cliente, 16, "Celular do Gui")["device_token"]

    # App 1.0.1: não informa versão, então não recebe avisos.
    _enviar(cliente, token, latitude=-23.55, longitude=-46.63)
    assert lembrete.canal_do_filho(db, gui) == "navegador"
    _atividade_de_hoje(db, 16, "Lição 1")
    assert lembrete.disparar_familia(db, 1)["enviados"][0]["canal"] == "navegador"
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63).json()["avisos"] == []

    # App novo, mas com notificações bloqueadas.
    _enviar_app(cliente, token, notificacoes=False)
    assert lembrete.canal_do_filho(db, gui) == "navegador"

    # App novo e ativo.
    _enviar_app(cliente, token)
    assert lembrete.canal_do_filho(db, gui) == "app"

    # Parado há 3 dias: volta ao navegador.
    aparelho = db.query(LocationDevice).filter(LocationDevice.child_user_id == 16).first()
    aparelho.last_seen_at = datetime.now(timezone.utc) - timedelta(days=3)
    db.commit()
    assert lembrete.canal_do_filho(db, gui) == "navegador"


def test_lembrete_novo_substitui_o_pendente_e_irmao_nao_recebe(ambiente):
    from app.models.lembrete import AvisoApp
    from app.services import lembrete

    cliente, db, _estado = ambiente
    token_gui = _parear(cliente, 16, "Celular do Gui")["device_token"]
    token_gio = _parear(cliente, 17, "Celular da Gio")["device_token"]
    _enviar_app(cliente, token_gui)
    _enviar_app(cliente, token_gio)
    _atividade_de_hoje(db, 16, "Lição 1")
    lembrete.disparar_familia(db, 1)
    lembrete.disparar_familia(db, 1)
    assert db.query(AvisoApp).filter(AvisoApp.child_user_id == 16, AvisoApp.entregue_em.is_(None)).count() == 1

    assert _enviar_app(cliente, token_gio).json()["avisos"] == []
    avisos_gui = _enviar_app(cliente, token_gui).json()["avisos"]
    assert len(avisos_gui) == 1
    # A Giovana não consegue confirmar (nem apagar) o aviso do irmão.
    _enviar_app(cliente, token_gio, recebidos=[avisos_gui[0]["id"]])
    assert len(_enviar_app(cliente, token_gui).json()["avisos"]) == 1


def test_celular_revogado_volta_ao_navegador(ambiente):
    from app.services import lembrete

    cliente, db, _estado = ambiente
    _inscrever_navegador(db, 17)
    gio = db.query(User).filter(User.id == 17).first()
    aparelho = _parear(cliente, 17, "Celular da Gio")
    _enviar_app(cliente, aparelho["device_token"])
    assert lembrete.canal_do_filho(db, gio) == "app"
    assert cliente.post(f"/api/v1/localizacao/dispositivos/{aparelho['device_id']}/revogar").status_code == 200
    assert lembrete.canal_do_filho(db, gio) == "navegador"


def test_lembrete_vale_ate_o_fim_da_janela():
    from app.services import lembrete

    fuso = lembrete.FUSO
    assert lembrete.fim_da_janela(datetime(2026, 11, 18, 18, 0, tzinfo=fuso)) == datetime(2026, 11, 19, 0, 0, tzinfo=timezone.utc)
    # Fora da janela (disparo de teste às 22h), vale 1 hora.
    assert lembrete.fim_da_janela(datetime(2026, 11, 18, 22, 0, tzinfo=fuso)) == datetime(2026, 11, 19, 2, 0, tzinfo=timezone.utc)


def _app_adulto(db, user_id):
    """Registra direto um celular de adulto (o app faz isso pelo login)."""
    from app.models.app_android import AppDispositivoAdulto

    db.add(AppDispositivoAdulto(family_id=1, user_id=user_id, token_hash=f"h{user_id}" * 8, label="Celular",
                                created_at=datetime.now(timezone.utc)))
    db.commit()


def _avisos_de(db, user_id):
    from app.models.lembrete import AvisoApp

    return [a.texto for a in db.query(AvisoApp).filter(AvisoApp.child_user_id == user_id).order_by(AvisoApp.id)]


def test_crianca_logada_conecta_o_celular_sem_codigo(ambiente):
    cliente, db, estado = ambiente
    estado["user"] = db.query(User).get(16)
    r = cliente.post("/api/v1/localizacao/dispositivos/parear-me", json={"device_label": "Celular do Gui"})
    assert r.status_code == 200, r.text
    assert r.json()["crianca_id"] == 16
    assert _enviar(cliente, r.json()["device_token"], latitude=-23.55, longitude=-46.63).status_code == 200
    # O mesmo celular passa para a Giovana: o token do Gui é revogado na troca.
    token_gui = r.json()["device_token"]
    estado["user"] = db.query(User).get(17)
    r2 = cliente.post("/api/v1/localizacao/dispositivos/parear-me", json={"token_anterior": token_gui})
    assert r2.status_code == 200 and r2.json()["crianca_id"] == 17
    assert _enviar(cliente, token_gui, latitude=-23.55, longitude=-46.63).status_code == 401
    assert _enviar(cliente, r2.json()["device_token"], latitude=-23.55, longitude=-46.63).status_code == 200
    # Adulto não vira "criança monitorada" pelo app.
    estado["user"] = db.query(User).get(3)
    assert cliente.post("/api/v1/localizacao/dispositivos/parear-me", json={}).status_code == 403


def test_alertas_de_chegada_saida_e_bateria_para_adultos_com_app(ambiente):
    cliente, db, estado = ambiente
    _app_adulto(db, 1)  # Kleber (admin) com app
    _app_adulto(db, 2)  # Tia com app, mas sem o menu Localização: não recebe
    casa = (-23.55, -46.63)
    um_km = 1000 / 111_320
    assert cliente.post("/api/v1/localizacao/lugares", json={
        "nome": "Casa", "preposicao": "em", "latitude": casa[0], "longitude": casa[1], "raio_m": 150,
    }).status_code == 201
    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    agora = datetime.now(timezone.utc)
    _enviar(cliente, token, latitude=casa[0] - um_km, longitude=casa[1], battery_level=40,
            recorded_at=_iso(agora - timedelta(minutes=10)))
    _enviar(cliente, token, latitude=casa[0], longitude=casa[1], battery_level=15,
            recorded_at=_iso(agora - timedelta(minutes=5)))
    _enviar(cliente, token, latitude=casa[0], longitude=casa[1], battery_level=12,
            recorded_at=_iso(agora - timedelta(minutes=1)))
    avisos = _avisos_de(db, 1)
    assert any(t.startswith("Guilherme chegou em Casa às ") for t in avisos), avisos
    assert "Bateria do celular de Guilherme em 15%." in avisos
    assert not any("12%" in t for t in avisos)  # um aviso por descarga
    assert _avisos_de(db, 2) == []


def test_alerta_sem_sinal_uma_vez_e_volta_a_valer_depois_de_novo_envio(ambiente):
    from app.models.location import LocationDevice
    from app.services import alertas_adultos

    cliente, db, estado = ambiente
    _app_adulto(db, 1)
    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    _enviar(cliente, token, latitude=-23.55, longitude=-46.63,
            recorded_at=_iso(datetime.now(timezone.utc) - timedelta(minutes=45)))
    aparelho = db.query(LocationDevice).filter(LocationDevice.child_user_id == 16).first()
    aparelho.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=40)
    db.commit()
    assert alertas_adultos.verificar_sem_sinal(db) == 1
    assert alertas_adultos.verificar_sem_sinal(db) == 0
    assert any("não envia localização desde" in t for t in _avisos_de(db, 1))
    r = _enviar(cliente, token, latitude=-23.55, longitude=-46.63)
    assert r.status_code == 200, r.text
    db.refresh(aparelho)
    assert aparelho.alerta_sem_sinal_em is None, r.json()


# ---------------------------------------------------------------- adultos no radar

def _parear_adulto(cliente, estado, db, user_id, **corpo):
    estado["user"] = db.query(User).get(user_id)
    return cliente.post("/api/v1/localizacao/dispositivos/parear-adulto", json=corpo)


def _adulto_outra_familia(db):
    agora = datetime.now(timezone.utc)
    tio = User(id=20, username="tio", first_name="Tio", family_id=2, password="x", email="",
               last_name="", is_staff=False, is_superuser=False, is_active=True, is_child=False,
               date_joined=agora, allowed_menus=["localizacao"])
    db.add(tio)
    db.commit()
    return tio


def test_adulto_compartilha_e_aparece_so_no_mapa_dos_adultos(ambiente):
    from app.models.lembrete import AvisoApp
    from app.models.location import LocationPlaceEvent

    cliente, db, estado = ambiente
    _app_adulto(db, 1)  # Kleber recebe alertas pelo app
    casa = (-23.55, -46.63)
    assert cliente.post("/api/v1/localizacao/lugares", json={
        "nome": "Casa", "preposicao": "em", "latitude": casa[0], "longitude": casa[1], "raio_m": 150,
    }).status_code == 201

    r = _parear_adulto(cliente, estado, db, 3, device_label="Celular da Mãe")
    assert r.status_code == 200, r.text
    assert r.json()["crianca_id"] == 3  # mesmo formato que o app 2.0.4 já lê
    token = r.json()["device_token"]
    agora = datetime.now(timezone.utc)
    um_km = 1000 / 111_320
    fora = _enviar(cliente, token, latitude=casa[0] - um_km, longitude=casa[1], battery_level=50,
                   recorded_at=_iso(agora - timedelta(minutes=10)))
    assert fora.status_code == 200, fora.text
    dentro = _enviar(cliente, token, latitude=casa[0], longitude=casa[1], battery_level=10,
                     recorded_at=_iso(agora - timedelta(minutes=5)), app_versao=9, notificacoes=True)
    assert dentro.status_code == 200 and dentro.json()["avisos"] == []

    # Decisão do Kleber: adulto aparece só no mapa. Sem chegada/saída, sem bateria, sem evento de lugar.
    assert db.query(AvisoApp).count() == 0
    assert db.query(LocationPlaceEvent).filter(LocationPlaceEvent.child_user_id == 3).count() == 0

    estado["user"] = db.query(User).get(1)
    # Rota antiga (/criancas, usada até hoje): continua só com as crianças.
    assert {c["nome"] for c in cliente.get("/api/v1/localizacao/criancas").json()} == {"Guilherme", "Giovana"}
    membros = cliente.get("/api/v1/localizacao/membros")
    assert membros.status_code == 200, membros.text
    por_nome = {m["nome"]: m for m in membros.json()}
    assert set(por_nome) == {"Guilherme", "Giovana", "Mãe"}
    assert por_nome["Mãe"]["adulto"] is True and por_nome["Guilherme"]["adulto"] is False
    assert por_nome["Mãe"]["bateria"] == 10
    assert por_nome["Mãe"]["status"]["frase"] == "Mãe está em Casa"
    dia = datetime.now(servico.FUSO).date().isoformat()
    trajeto = cliente.get(f"/api/v1/localizacao/membros/3/trajeto?dia={dia}")
    assert trajeto.status_code == 200, trajeto.text
    assert trajeto.json()["eventos"] == []
    # Pelas rotas antigas, o adulto continua invisível.
    assert cliente.get(f"/api/v1/localizacao/criancas/3/trajeto?dia={dia}").status_code == 404
    assert cliente.put("/api/v1/localizacao/criancas/3/apelido", json={"apelido": "Mã"}).status_code == 404
    assert cliente.put("/api/v1/localizacao/membros/3/apelido", json={"apelido": "Mã"}).json()["apelido"] == "Mã"
    # Adulto que nunca ligou o compartilhamento não aparece nem tem trajeto.
    assert cliente.get(f"/api/v1/localizacao/membros/1/trajeto?dia={dia}").status_code == 404


def test_crianca_nao_ve_adulto_em_nenhuma_rota(ambiente):
    cliente, db, estado = ambiente
    token_mae = _parear_adulto(cliente, estado, db, 3).json()["device_token"]
    assert _enviar(cliente, token_mae, latitude=-23.55, longitude=-46.63).status_code == 200
    estado["user"] = db.query(User).get(1)
    token_gui = _parear(cliente, 16, "Celular do Gui")["device_token"]

    estado["user"] = db.query(User).get(16)
    dia = datetime.now(servico.FUSO).date().isoformat()
    for metodo, rota, corpo in (
        ("get", "/api/v1/localizacao/membros", None),
        ("get", f"/api/v1/localizacao/membros/3/trajeto?dia={dia}", None),
        ("put", "/api/v1/localizacao/membros/3/apelido", {"apelido": "x"}),
        ("get", "/api/v1/localizacao/criancas", None),
        ("get", f"/api/v1/localizacao/criancas/3/trajeto?dia={dia}", None),
        ("get", "/api/v1/localizacao/lugares", None),
        ("post", "/api/v1/localizacao/dispositivos/parear-adulto", {}),
    ):
        resposta = getattr(cliente, metodo)(rota, **({"json": corpo} if corpo is not None else {}))
        assert resposta.status_code == 403, (rota, resposta.status_code, resposta.text)
        assert "Mãe" not in resposta.text
    # O celular da criança recebe a resposta da posição sem nada sobre o adulto.
    r = _enviar(cliente, token_gui, latitude=-23.55, longitude=-46.63)
    assert r.status_code == 200 and "Mãe" not in r.text
    # O token do adulto não serve para a criança pedir o mapa (só envia posição).
    assert cliente.get("/api/v1/localizacao/membros", headers={"X-Device-Token": token_mae}).status_code == 403


def test_adultos_no_mapa_isolados_por_familia(ambiente):
    cliente, db, estado = ambiente
    _adulto_outra_familia(db)
    token_tio = _parear_adulto(cliente, estado, db, 20).json()["device_token"]
    assert _enviar(cliente, token_tio, latitude=-22.9, longitude=-43.2).status_code == 200
    token_mae = _parear_adulto(cliente, estado, db, 3).json()["device_token"]
    assert _enviar(cliente, token_mae, latitude=-23.55, longitude=-46.63).status_code == 200
    dia = datetime.now(servico.FUSO).date().isoformat()

    estado["user"] = db.query(User).get(1)
    assert "Tio" not in {m["nome"] for m in cliente.get("/api/v1/localizacao/membros").json()}
    assert cliente.get(f"/api/v1/localizacao/membros/20/trajeto?dia={dia}").status_code == 404
    assert cliente.put("/api/v1/localizacao/membros/20/apelido", json={"apelido": "x"}).status_code == 404

    estado["user"] = db.query(User).get(20)
    vistos = {m["nome"] for m in cliente.get("/api/v1/localizacao/membros").json()}
    assert vistos == {"Primo", "Tio"}
    assert cliente.get(f"/api/v1/localizacao/membros/3/trajeto?dia={dia}").status_code == 404


def test_adulto_sem_menu_nao_compartilha_e_perde_o_token_ao_perder_o_menu(ambiente):
    cliente, db, estado = ambiente
    assert _parear_adulto(cliente, estado, db, 2).status_code == 403  # Tia: só Estudos
    r = _parear_adulto(cliente, estado, db, 3)
    token = r.json()["device_token"]
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63).status_code == 200
    mae = db.query(User).get(3)
    mae.allowed_menus = ["estudos"]
    db.commit()
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63).status_code == 401


def test_celular_do_adulto_revogado_trocado_ou_de_outra_familia_para_de_enviar(ambiente):
    from app.models.location import LocationDevice

    cliente, db, estado = ambiente
    primeiro = _parear_adulto(cliente, estado, db, 3).json()
    # Religar no mesmo celular revoga o token anterior.
    segundo = _parear_adulto(cliente, estado, db, 3, token_anterior=primeiro["device_token"]).json()
    assert _enviar(cliente, primeiro["device_token"], latitude=-23.55, longitude=-46.63).status_code == 401
    assert _enviar(cliente, segundo["device_token"], latitude=-23.55, longitude=-46.63).status_code == 200
    # Revogado pelo site.
    estado["user"] = db.query(User).get(1)
    assert cliente.post(f"/api/v1/localizacao/dispositivos/{segundo['device_id']}/revogar").status_code == 200
    assert _enviar(cliente, segundo["device_token"], latitude=-23.55, longitude=-46.63).status_code == 401
    # Mudou de família: revogado automaticamente.
    terceiro = _parear_adulto(cliente, estado, db, 3).json()
    mae = db.query(User).get(3)
    mae.family_id = 2
    db.commit()
    assert _enviar(cliente, terceiro["device_token"], latitude=-23.55, longitude=-46.63).status_code == 401
    assert db.query(LocationDevice).get(terceiro["device_id"]).revoked_at is not None


def test_celular_de_adulto_sem_sinal_nao_gera_alerta(ambiente):
    from app.models.location import LocationDevice
    from app.services import alertas_adultos

    cliente, db, estado = ambiente
    _app_adulto(db, 1)
    token = _parear_adulto(cliente, estado, db, 3).json()["device_token"]
    _enviar(cliente, token, latitude=-23.55, longitude=-46.63,
            recorded_at=_iso(datetime.now(timezone.utc) - timedelta(minutes=45)))
    aparelho = db.query(LocationDevice).filter(LocationDevice.child_user_id == 3).first()
    aparelho.last_seen_at = datetime.now(timezone.utc) - timedelta(minutes=40)
    db.commit()
    assert alertas_adultos.verificar_sem_sinal(db) == 0
    assert _avisos_de(db, 1) == []


def test_celular_de_adulto_nao_consome_os_alertas_do_adulto(ambiente):
    from app.services import avisos_app

    cliente, db, estado = ambiente
    token = _parear_adulto(cliente, estado, db, 3).json()["device_token"]
    avisos_app.enfileirar(db, db.query(User).get(3), "Localização", "Guilherme chegou na Escola", "/localizacao", tipo="alerta-y")
    db.commit()
    r = _enviar(cliente, token, latitude=-23.55, longitude=-46.63, app_versao=9)
    assert r.json()["avisos"] == []
    assert _avisos_de(db, 3) == ["Guilherme chegou na Escola"]  # continua na fila do canal de alertas


# ---------------------------------------------------------------- correções da Segurança (C1 a C3)

def test_c1_historico_do_adulto_fica_no_maximo_7_dias(ambiente):
    from app.models.location import LocationPoint

    cliente, db, estado = ambiente
    token_mae = _parear_adulto(cliente, estado, db, 3).json()["device_token"]
    estado["user"] = db.query(User).get(1)
    token_gui = _parear(cliente, 16, "Celular do Gui")["device_token"]
    agora = datetime.now(timezone.utc)
    for token in (token_mae, token_gui):
        assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63,
                       recorded_at=_iso(agora - timedelta(minutes=5))).status_code == 200
    # Pontos de 8 dias atrás (gravados direto, como se tivessem chegado na época).
    for dono, device in ((3, None), (16, None)):
        ultimo = db.query(LocationPoint).filter(LocationPoint.child_user_id == dono).first()
        db.add(LocationPoint(device_id=ultimo.device_id, family_id=1, child_user_id=dono, latitude=-23.5,
                             longitude=-46.6, recorded_at=agora - timedelta(days=8), received_at=agora))
    db.commit()
    # Antes da limpeza: o trajeto do adulto já não mostra nada além de 7 dias.
    dia_antigo = (agora - timedelta(days=8)).astimezone(servico.FUSO).date().isoformat()
    assert cliente.get(f"/api/v1/localizacao/membros/3/trajeto?dia={dia_antigo}").json()["pontos"] == []
    assert len(cliente.get(f"/api/v1/localizacao/membros/16/trajeto?dia={dia_antigo}").json()["pontos"]) == 1

    servico.limpar_historico_antigo(db, agora)
    db.commit()
    do_adulto = db.query(LocationPoint).filter(LocationPoint.child_user_id == 3).all()
    da_crianca = db.query(LocationPoint).filter(LocationPoint.child_user_id == 16).all()
    assert len(do_adulto) == 1 and como_utc_teste(do_adulto[0].recorded_at) > agora - timedelta(days=7)
    assert len(da_crianca) == 2  # criança continua com LOCALIZACAO_RETENCAO_DIAS (90)


def como_utc_teste(momento):
    return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)


def test_c2_parar_de_compartilhar_tira_o_adulto_do_mapa_e_apaga_os_pontos(ambiente):
    from app.models.location import LocationPoint

    cliente, db, estado = ambiente
    r = _parear_adulto(cliente, estado, db, 3).json()
    assert _enviar(cliente, r["device_token"], latitude=-23.55, longitude=-46.63).status_code == 200
    dia = datetime.now(servico.FUSO).date().isoformat()
    estado["user"] = db.query(User).get(1)
    assert "Mãe" in {m["nome"] for m in cliente.get("/api/v1/localizacao/membros").json()}

    # Parar de compartilhar pelo app (revogar-me).
    assert cliente.post("/api/v1/localizacao/dispositivos/revogar-me",
                        headers={"X-Device-Token": r["device_token"]}).status_code == 200
    assert "Mãe" not in {m["nome"] for m in cliente.get("/api/v1/localizacao/membros").json()}
    assert cliente.get(f"/api/v1/localizacao/membros/3/trajeto?dia={dia}").status_code == 404
    assert db.query(LocationPoint).filter(LocationPoint.child_user_id == 3).count() == 0

    # Revogado pelo site: mesmo efeito.
    r2 = _parear_adulto(cliente, estado, db, 3).json()
    assert _enviar(cliente, r2["device_token"], latitude=-23.55, longitude=-46.63).status_code == 200
    estado["user"] = db.query(User).get(1)
    assert cliente.post(f"/api/v1/localizacao/dispositivos/{r2['device_id']}/revogar").status_code == 200
    assert "Mãe" not in {m["nome"] for m in cliente.get("/api/v1/localizacao/membros").json()}
    assert cliente.get(f"/api/v1/localizacao/membros/3/trajeto?dia={dia}").status_code == 404
    assert db.query(LocationPoint).filter(LocationPoint.child_user_id == 3).count() == 0

    # Perdeu o menu Localização: some do mapa e do trajeto, mesmo com celular ativo.
    r3 = _parear_adulto(cliente, estado, db, 3).json()
    assert _enviar(cliente, r3["device_token"], latitude=-23.55, longitude=-46.63).status_code == 200
    mae = db.query(User).get(3)
    mae.allowed_menus = ["estudos"]
    db.commit()
    estado["user"] = db.query(User).get(1)
    assert "Mãe" not in {m["nome"] for m in cliente.get("/api/v1/localizacao/membros").json()}
    assert cliente.get(f"/api/v1/localizacao/membros/3/trajeto?dia={dia}").status_code == 404


def test_c2_crianca_que_assume_o_celular_do_adulto_apaga_os_pontos_dele(ambiente):
    from app.models.location import LocationPoint

    cliente, db, estado = ambiente
    r = _parear_adulto(cliente, estado, db, 3).json()
    assert _enviar(cliente, r["device_token"], latitude=-23.55, longitude=-46.63).status_code == 200
    estado["user"] = db.query(User).get(16)
    troca = cliente.post("/api/v1/localizacao/dispositivos/parear-me", json={"token_anterior": r["device_token"]})
    assert troca.status_code == 200
    assert db.query(LocationPoint).filter(LocationPoint.child_user_id == 3).count() == 0
    estado["user"] = db.query(User).get(1)
    assert "Mãe" not in {m["nome"] for m in cliente.get("/api/v1/localizacao/membros").json()}


def test_c3_um_celular_ativo_por_adulto_mesmo_sem_token_anterior(ambiente):
    from app.models.location import LocationDevice

    cliente, db, estado = ambiente
    tokens = [_parear_adulto(cliente, estado, db, 3).json()["device_token"] for _ in range(3)]
    ativos = db.query(LocationDevice).filter(LocationDevice.child_user_id == 3, LocationDevice.revoked_at.is_(None)).count()
    assert ativos == 1
    assert [_enviar(cliente, t, latitude=-23.55, longitude=-46.63).status_code for t in tokens] == [401, 401, 200]


def test_qa3_criancas_mantem_o_formato_do_204_e_membros_traz_adulto(ambiente):
    cliente, db, estado = ambiente
    token = _parear_adulto(cliente, estado, db, 3).json()["device_token"]
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63).status_code == 200
    estado["user"] = db.query(User).get(1)
    # Campos de /criancas no app/site 2.0.4 (schemas/location.py em 8216587), sem nada a mais.
    formato_204 = {
        "id", "nome", "apelido", "family_id", "bateria", "atualizado_em", "ha_segundos",
        "latitude", "longitude", "accuracy_m", "speed_kmh", "status", "aparelhos",
    }
    criancas = cliente.get("/api/v1/localizacao/criancas").json()
    assert criancas and all(set(item) == formato_204 for item in criancas)
    membros = cliente.get("/api/v1/localizacao/membros").json()
    assert all(set(item) == formato_204 | {"adulto"} for item in membros)
    assert {m["nome"]: m["adulto"] for m in membros} == {"Guilherme": False, "Giovana": False, "Mãe": True}


# ---------------------------------------------------------------- avós só são vistos + SOS

def _avo(db, family_id=1, user_id=30, menus=("compartilhar_localizacao",)):
    agora = datetime.now(timezone.utc)
    avo = User(id=user_id, username=f"avo{user_id}", first_name="Avô", last_name="", family_id=family_id,
               password="x", email="", is_staff=False, is_superuser=False, is_active=True, is_child=False,
               date_joined=agora, allowed_menus=list(menus))
    db.add(avo)
    db.commit()
    return avo


def test_avo_compartilha_e_aparece_mas_nunca_ve_ninguem(ambiente):
    from app.models.location import LocationDevice

    cliente, db, estado = ambiente
    _avo(db)
    _app_adulto(db, 30)  # o avô tem o app registrado para avisos
    token_mae = _parear_adulto(cliente, estado, db, 3).json()["device_token"]
    assert _enviar(cliente, token_mae, latitude=-23.55, longitude=-46.63).status_code == 200
    estado["user"] = db.query(User).get(1)
    token_gui = _parear(cliente, 16, "Celular do Gui")["device_token"]
    assert _enviar(cliente, token_gui, latitude=-23.55, longitude=-46.63, battery_level=10).status_code == 200

    r = _parear_adulto(cliente, estado, db, 30)
    assert r.status_code == 200, r.text
    resposta = _enviar(cliente, r.json()["device_token"], latitude=-23.56, longitude=-46.64, battery_level=70)
    assert resposta.status_code == 200 and resposta.json()["avisos"] == []

    # Quem vê o mapa vê o avô.
    estado["user"] = db.query(User).get(1)
    assert "Avô" in {m["nome"] for m in cliente.get("/api/v1/localizacao/membros").json()}

    # O avô não vê ninguém, em nenhuma rota de leitura ou de gestão.
    estado["user"] = db.query(User).get(30)
    dia = datetime.now(servico.FUSO).date().isoformat()
    aparelho_gui = db.query(LocationDevice).filter(LocationDevice.child_user_id == 16).first().id
    for metodo, rota, corpo in (
        ("get", "/api/v1/localizacao/membros", None),
        ("get", "/api/v1/localizacao/criancas", None),
        ("get", f"/api/v1/localizacao/membros/3/trajeto?dia={dia}", None),
        ("get", f"/api/v1/localizacao/criancas/16/trajeto?dia={dia}", None),
        ("put", "/api/v1/localizacao/membros/16/apelido", {"apelido": "x"}),
        ("get", "/api/v1/localizacao/lugares", None),
        ("post", "/api/v1/localizacao/pareamentos", {"child_user_id": 16}),
        ("post", f"/api/v1/localizacao/dispositivos/{aparelho_gui}/revogar", None),
        ("get", "/api/v1/localizacao/sos", None),
        ("get", "/api/v1/localizacao/sos/destinatarios", None),
        ("put", "/api/v1/localizacao/sos/destinatarios", {"user_ids": [30]}),
        ("post", "/api/v1/localizacao/sos/1/visto", None),
    ):
        resposta = getattr(cliente, metodo)(rota, **({"json": corpo} if corpo is not None else {}))
        assert resposta.status_code == 403, (rota, resposta.status_code, resposta.text)
        assert "Guilherme" not in resposta.text and "Mãe" not in resposta.text
    # Nem por alerta: bateria baixa do Gui e chegada/saída não vão para o avô.
    assert _avisos_de(db, 30) == []


def test_so_compartilhar_exige_a_permissao_e_cai_ao_perder(ambiente):
    cliente, db, estado = ambiente
    assert _parear_adulto(cliente, estado, db, 2).status_code == 403   # Tia: só Estudos
    assert _parear_adulto(cliente, estado, db, 16).status_code == 403  # criança
    avo = _avo(db)
    token = _parear_adulto(cliente, estado, db, 30).json()["device_token"]
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63).status_code == 200
    avo.allowed_menus = ["estudos"]
    db.commit()
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63).status_code == 401
    estado["user"] = db.query(User).get(1)
    assert "Avô" not in {m["nome"] for m in cliente.get("/api/v1/localizacao/membros").json()}


def _adulto_que_ve(db, user_id=31, nome="Ana"):
    agora = datetime.now(timezone.utc)
    pessoa = User(id=user_id, username=f"adulto{user_id}", first_name=nome, last_name="", family_id=1, password="x",
                  email="", is_staff=False, is_superuser=False, is_active=True, is_child=False, date_joined=agora,
                  allowed_menus=["localizacao"])
    db.add(pessoa)
    db.commit()
    return pessoa


def test_sos_avisa_so_os_escolhidos_com_nome_posicao_horario_e_bateria(ambiente):
    from app.models.location import LocationSos

    cliente, db, estado = ambiente
    _adulto_que_ve(db)  # Ana, id 31, vê o mapa
    for user_id in (1, 3, 31):
        _app_adulto(db, user_id)
    estado["user"] = db.query(User).get(1)
    opcoes = cliente.get("/api/v1/localizacao/sos/destinatarios").json()
    assert {o["nome"] for o in opcoes["opcoes"]} == {"Kleber", "Mãe", "Ana"} and opcoes["escolhidos"] == []
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [3, 31]}).json()["escolhidos"] == [3, 31]

    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63, battery_level=40,
                   recorded_at=_iso(datetime.now(timezone.utc) - timedelta(minutes=3))).status_code == 200
    sos = cliente.post("/api/v1/localizacao/dispositivos/sos", json={}, headers={"X-Device-Token": token})
    assert sos.status_code == 200, sos.text
    assert sos.json()["repetido"] is False and sos.json()["avisados"] == 2
    assert len(_avisos_de(db, 31)) == 1
    avisos_mae = _avisos_de(db, 3)
    assert len(avisos_mae) == 1
    assert avisos_mae[0].startswith("Guilherme pediu socorro às ") and "Última posição às " in avisos_mae[0] and "Bateria 40%." in avisos_mae[0]
    assert _avisos_de(db, 1) == []  # Kleber não foi escolhido

    # Toque repetido em menos de 2 min: o mesmo pedido, sem novo aviso.
    de_novo = cliente.post("/api/v1/localizacao/dispositivos/sos", json={}, headers={"X-Device-Token": token})
    assert de_novo.json() == {"id": sos.json()["id"], "repetido": True, "avisados": 2, "motivo": None}
    assert db.query(LocationSos).count() == 1

    # S1: o Kleber (não escolhido, não avisado) não vê o SOS nem a posição, e não marca Visto.
    assert cliente.get("/api/v1/localizacao/sos").json() == []
    assert cliente.post(f"/api/v1/localizacao/sos/{sos.json()['id']}/visto").status_code == 404
    # A Mãe (avisada) vê com a última posição; some do "aberto" quando ela marca Visto.
    estado["user"] = db.query(User).get(3)
    lista = cliente.get("/api/v1/localizacao/sos").json()
    assert lista[0]["nome"] == "Guilherme" and lista[0]["latitude"] == -23.55 and lista[0]["bateria"] == 40 and lista[0]["visto_em"] is None
    visto = cliente.post(f"/api/v1/localizacao/sos/{sos.json()['id']}/visto").json()
    assert visto["visto_em"] is not None and visto["visto_por"] == "Mãe"

    # Passados 2 min, um novo SOS vale de novo e usa a posição enviada pelo celular.
    registro = db.query(LocationSos).first()
    registro.created_at = datetime.now(timezone.utc) - timedelta(minutes=3)
    db.commit()
    novo = cliente.post("/api/v1/localizacao/dispositivos/sos", json={"latitude": -23.6, "longitude": -46.7, "battery_level": 35},
                        headers={"X-Device-Token": token})
    assert novo.json()["repetido"] is False
    assert db.query(LocationSos).order_by(LocationSos.id.desc()).first().latitude == -23.6


def test_sos_sem_escolhidos_avisa_quem_ve_o_mapa_e_nunca_quem_pediu_nem_avos(ambiente):
    cliente, db, estado = ambiente
    _avo(db)
    for user_id in (1, 2, 3, 30):
        _app_adulto(db, user_id)
    token = _parear_adulto(cliente, estado, db, 3).json()["device_token"]
    r = cliente.post("/api/v1/localizacao/dispositivos/sos", json={"latitude": -23.55, "longitude": -46.63},
                     headers={"X-Device-Token": token})
    assert r.status_code == 200 and r.json()["avisados"] == 1
    assert len(_avisos_de(db, 1)) == 1                        # Kleber (vê o mapa)
    assert _avisos_de(db, 3) == []                            # quem pediu
    assert _avisos_de(db, 2) == [] and _avisos_de(db, 30) == []  # Tia sem Localização; avô só é visto
    # O avô também pode pedir socorro (ele compartilha).
    token_avo = _parear_adulto(cliente, estado, db, 30).json()["device_token"]
    assert cliente.post("/api/v1/localizacao/dispositivos/sos", json={}, headers={"X-Device-Token": token_avo}).json()["avisados"] == 2


def test_sos_isolado_por_familia_e_longe_das_criancas(ambiente):
    cliente, db, estado = ambiente
    _adulto_outra_familia(db)  # Tio, família 2, com Localização
    estado["user"] = db.query(User).get(1)
    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    sos_id = cliente.post("/api/v1/localizacao/dispositivos/sos", json={"latitude": -23.55, "longitude": -46.63},
                          headers={"X-Device-Token": token}).json()["id"]
    estado["user"] = db.query(User).get(20)
    assert cliente.get("/api/v1/localizacao/sos").json() == []
    assert cliente.post(f"/api/v1/localizacao/sos/{sos_id}/visto").status_code == 404
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [3]}).status_code == 400
    estado["user"] = db.query(User).get(1)
    for invalido in ([16], [2], [20]):  # criança, adulto sem Localização, outra família
        assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": invalido}).status_code == 400
    estado["user"] = db.query(User).get(16)
    assert cliente.get("/api/v1/localizacao/sos").status_code == 403
    assert cliente.get("/api/v1/localizacao/sos/destinatarios").status_code == 403
    assert cliente.post("/api/v1/localizacao/dispositivos/sos", json={}).status_code == 401  # sem token de celular



def test_sos_s2_posicao_some_em_7_dias_registro_em_30_e_na_revogacao_do_adulto(ambiente):
    from app.models.location import LocationSos, LocationSosAvisado

    cliente, db, estado = ambiente
    estado["user"] = db.query(User).get(1)
    token_gui = _parear(cliente, 16, "Celular do Gui")["device_token"]
    corpo = {"latitude": -23.55, "longitude": -46.63, "accuracy_m": 5, "battery_level": 50}
    ids = []
    for dias in (31, 8, 0):
        r = cliente.post("/api/v1/localizacao/dispositivos/sos", json=corpo, headers={"X-Device-Token": token_gui})
        ids.append(r.json()["id"])
        registro = db.query(LocationSos).get(ids[-1])
        registro.created_at = datetime.now(timezone.utc) - timedelta(days=dias, minutes=5)
        db.commit()
    servico.limpar_historico_antigo(db)
    db.commit()
    db.expire_all()
    assert db.query(LocationSos).get(ids[0]) is None                     # 31 dias: apagado
    assert db.query(LocationSosAvisado).filter(LocationSosAvisado.sos_id == ids[0]).count() == 0
    oito = db.query(LocationSos).get(ids[1])                              # 8 dias: só o registro
    assert (oito.latitude, oito.longitude, oito.accuracy_m, oito.battery_level) == (None, None, None, None)
    hoje = db.query(LocationSos).get(ids[2])                              # recente: intacto
    assert hoje.latitude == -23.55 and hoje.battery_level == 50

    # Adulto que para de compartilhar: a posição dos SOS dele some na hora.
    r = _parear_adulto(cliente, estado, db, 3).json()
    sos_mae = cliente.post("/api/v1/localizacao/dispositivos/sos", json=corpo, headers={"X-Device-Token": r["device_token"]}).json()["id"]
    assert cliente.post("/api/v1/localizacao/dispositivos/revogar-me", headers={"X-Device-Token": r["device_token"]}).status_code == 200
    db.expire_all()
    registro = db.query(LocationSos).get(sos_mae)
    assert registro is not None and registro.latitude is None and registro.battery_level is None


def test_sos_s4_teto_de_10_por_familia_por_hora(ambiente):
    from app.models.location import LocationDevice, LocationSos

    cliente, db, estado = ambiente
    estado["user"] = db.query(User).get(1)
    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    aparelho = db.query(LocationDevice).filter(LocationDevice.child_user_id == 16).first()
    agora = datetime.now(timezone.utc)
    for i in range(10):
        db.add(LocationSos(family_id=1, user_id=17, device_id=aparelho.id, created_at=agora - timedelta(minutes=50 - i)))
    db.commit()
    r = cliente.post("/api/v1/localizacao/dispositivos/sos", json={}, headers={"X-Device-Token": token})
    assert r.status_code == 429
    assert db.query(LocationSos).count() == 10


def test_sos_s5_horario_fora_do_limite_usa_a_ultima_posicao_conhecida(ambiente):
    from app.models.location import LocationSos

    cliente, db, estado = ambiente
    estado["user"] = db.query(User).get(1)
    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    assert _enviar(cliente, token, latitude=-23.55, longitude=-46.63,
                   recorded_at=_iso(datetime.now(timezone.utc) - timedelta(minutes=2))).status_code == 200
    futuro = _iso(datetime.now(timezone.utc) + timedelta(hours=3))
    r = cliente.post("/api/v1/localizacao/dispositivos/sos", json={"latitude": 10.0, "longitude": 10.0, "recorded_at": futuro},
                     headers={"X-Device-Token": token})
    assert r.status_code == 200
    registro = db.query(LocationSos).get(r.json()["id"])
    assert registro.latitude == -23.55  # descartou a posição com horário inválido


def test_qa_lista_so_com_o_proprio_adulto_e_recusada(ambiente):
    """Reescrito para a regra de 2 elegíveis: lista de 1 (o próprio ou outro) é recusada."""
    cliente, db, estado = ambiente
    _adulto_que_ve(db)
    estado["user"] = db.query(User).get(1)
    r = cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [1]})
    assert r.status_code == 400 and "pelo menos 2 adultos" in r.json()["detail"]
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [3]}).status_code == 400
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [1, 3]}).status_code == 200
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [3, 31]}).status_code == 200
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": []}).status_code == 200  # vazio: regra atual


def test_qa_mae_salva_so_o_kleber_e_recusado_e_sempre_sobra_um_elegivel(ambiente):
    """O outro caminho do QA: quem salva não está na lista, mas a pessoa da lista também pede SOS."""
    from app.models.location import LocationSos

    cliente, db, estado = ambiente
    _adulto_que_ve(db)
    for user_id in (1, 3, 31):
        _app_adulto(db, user_id)
    estado["user"] = db.query(User).get(3)
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [1]}).status_code == 400   # Mãe salva [Kleber]
    estado["user"] = db.query(User).get(1)
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [3]}).status_code == 400   # Kleber salva [Mãe]
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [3, 31]}).status_code == 200
    # Com a lista [Mãe, Ana], o SOS de qualquer uma delas ainda avisa a outra.
    for quem, outra in ((3, 31), (31, 3)):
        token = _parear_adulto(cliente, estado, db, quem).json()["device_token"]
        r = cliente.post("/api/v1/localizacao/dispositivos/sos", json={"latitude": -23.55, "longitude": -46.63},
                         headers={"X-Device-Token": token}).json()
        assert r["avisados"] == 1 and r["motivo"] is None
    assert len(_avisos_de(db, 31)) == 1 and len(_avisos_de(db, 3)) == 1
    assert db.query(LocationSos).filter(LocationSos.avisados == 0).count() == 0


def test_qa_unica_escolhida_perde_o_menu_sos_fica_com_zero_avisados_e_alerta_o_admin(ambiente):
    """Reescrito para a regra de 2 elegíveis: os DOIS escolhidos perdem o menu depois de salvos."""
    from app.models.location import LocationSos

    cliente, db, estado = ambiente
    _adulto_que_ve(db)
    for user_id in (1, 3, 31):
        _app_adulto(db, user_id)
    estado["user"] = db.query(User).get(1)
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [3, 31]}).status_code == 200
    for user_id in (3, 31):
        pessoa = db.query(User).get(user_id)
        pessoa.allowed_menus = ["estudos"]
    db.commit()

    # A lista salva não muda em silêncio: os dois continuam nela, marcados como sem acesso.
    lista = cliente.get("/api/v1/localizacao/sos/destinatarios").json()
    assert lista["escolhidos"] == [3, 31] and {p["nome"] for p in lista["sem_acesso"]} == {"Mãe", "Ana"}
    # Salvar mantendo-os mais só o Kleber (1 elegível) é recusado; incluir alguém novo sem acesso, também.
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [3, 31, 1]}).status_code == 400
    assert cliente.put("/api/v1/localizacao/sos/destinatarios", json={"user_ids": [2]}).status_code == 400
    assert cliente.get("/api/v1/localizacao/sos/destinatarios").json()["escolhidos"] == [3, 31]

    token = _parear(cliente, 16, "Celular do Gui")["device_token"]
    r = cliente.post("/api/v1/localizacao/dispositivos/sos", json={"latitude": -23.55, "longitude": -46.63},
                     headers={"X-Device-Token": token}).json()
    assert r["avisados"] == 0 and r["motivo"] == "sem destinatário elegível" and r["repetido"] is False
    assert db.query(LocationSos).get(r["id"]).motivo == "sem destinatário elegível"
    assert _avisos_de(db, 1) == [] and _avisos_de(db, 3) == [] and _avisos_de(db, 31) == []

    # O admin vê o alerta (sem posição); quem não é admin, não.
    alerta = cliente.get("/api/v1/localizacao/sos/sem-destinatario").json()
    assert [(a["nome"], a["motivo"]) for a in alerta] == [("Guilherme", "sem destinatário elegível")]
    assert "latitude" not in alerta[0] and "bateria" not in alerta[0]
    _adulto_outra_familia(db)
    estado["user"] = db.query(User).get(20)
    assert cliente.get("/api/v1/localizacao/sos/sem-destinatario").status_code == 403
    estado["user"] = db.query(User).get(16)
    assert cliente.get("/api/v1/localizacao/sos/sem-destinatario").status_code == 403

    # Repetir o toque não diz que alguém foi avisado.
    de_novo = cliente.post("/api/v1/localizacao/dispositivos/sos", json={}, headers={"X-Device-Token": token}).json()
    assert de_novo["repetido"] is True and de_novo["avisados"] == 0 and de_novo["motivo"] == "sem destinatário elegível"
