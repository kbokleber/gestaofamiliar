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
    db = sessionmaker(bind=engine)()
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
