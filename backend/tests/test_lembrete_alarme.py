"""Alarme do lembrete (app 2.0.9): som/volume da família e teste só no celular do adulto logado."""
import inspect
from datetime import datetime, timedelta, timezone

from app.api.deps import get_current_admin
from app.api.v1.endpoints import notificacoes
from app.models.lembrete import AvisoApp, FamilyLembreteConfig
from app.models.user import User
from app.services import avisos_app, lembrete

from test_localizacao import _app_adulto, _atividade_de_hoje, _enviar, _parear, ambiente  # noqa: F401


def _preparar(cliente, db, estado):
    """Monta as rotas de lembrete e deixa os dois filhos com app ativo e tarefa de hoje."""
    if not getattr(cliente.app.state, "com_notificacoes", False):
        cliente.app.include_router(notificacoes.router, prefix="/api/v1")
        cliente.app.dependency_overrides[get_current_admin] = lambda: estado["user"]
        cliente.app.state.com_notificacoes = True
    agora = datetime.now(timezone.utc)
    tokens = {}
    for filho in (16, 17):
        tokens[filho] = _parear(cliente, filho, f"Celular {filho}")["device_token"]
        assert _enviar(cliente, tokens[filho], latitude=-23.55, longitude=-46.63,
                       recorded_at=(agora - timedelta(minutes=1)).isoformat(),
                       app_versao=avisos_app.VERSAO_MINIMA_ALARME, notificacoes=True).status_code == 200
        _atividade_de_hoje(db, filho, f"Tarefa {filho}")
    return tokens


def _avisos(db, user_id):
    return db.query(AvisoApp).filter(AvisoApp.child_user_id == user_id).all()


def test_teste_do_alarme_vai_so_para_o_celular_do_adulto_logado(ambiente):
    cliente, db, estado = ambiente
    tokens = _preparar(cliente, db, estado)
    _app_adulto(db, 1)
    estado["user"] = db.query(User).get(1)

    r = cliente.post("/api/v1/notificacoes/lembretes/testar-alarme", json={"som": "padrao", "volume": "alto"})
    assert r.status_code == 200, r.text
    assert r.json()["aparelhos"] == 1

    # Um único aviso, para o adulto logado, com o alarme pedido.
    todos = db.query(AvisoApp).all()
    assert [(a.child_user_id, a.tipo, a.som, a.volume) for a in todos] == [(1, "teste_alarme", "padrao", "alto")]
    assert _avisos(db, 16) == [] and _avisos(db, 17) == []

    # Os celulares das crianças não recebem nada no próximo envio.
    for token in tokens.values():
        resposta = _enviar(cliente, token, latitude=-23.55, longitude=-46.63)
        assert resposta.status_code == 200
        assert resposta.json().get("avisos", []) == []

    # O celular do adulto recebe o aviso com som e volume.
    from app.models.app_android import AppDispositivoAdulto
    aparelho = db.query(AppDispositivoAdulto).filter(AppDispositivoAdulto.user_id == 1).one()
    aparelho.app_versao = avisos_app.VERSAO_MINIMA_ALARME
    entregues = avisos_app.pendentes(db, aparelho)
    assert [(a["tipo"], a["som"], a["volume"]) for a in entregues] == [("teste_alarme", "padrao", "alto")]


def test_teste_do_alarme_sem_celular_de_adulto_nao_envia_nada(ambiente):
    cliente, db, estado = ambiente
    _preparar(cliente, db, estado)
    # Adulto admin sem celular de adulto registrado.
    estado["user"] = db.query(User).get(1)
    r = cliente.post("/api/v1/notificacoes/lembretes/testar-alarme", json={})
    assert r.status_code == 409
    assert "Nenhum celular seu" in r.json()["detail"]
    # Criança nunca dispara o teste, mesmo se a checagem de admin falhar.
    with_child = db.query(User).get(16)
    try:
        avisos_app.testar_alarme_no_adulto(db, with_child, "padrao", "alto")
        assert False, "criança não pode testar"
    except avisos_app.SemCelularDeAdulto:
        pass
    assert db.query(AvisoApp).count() == 0


def test_teste_do_alarme_nao_consulta_filhos_nem_celulares_de_crianca():
    """Prova no código: a função do teste não usa a lista de filhos nem celulares de criança."""
    fonte = inspect.getsource(avisos_app.testar_alarme_no_adulto) + inspect.getsource(notificacoes.testar_alarme)
    for proibido in ("LocationDevice", "disparar_familia", "is_child.is_(True)", "is_child ==", "enviar_para_usuario", "tem_app"):
        assert proibido not in fonte, proibido


def test_som_e_volume_da_familia_comecam_desligados_e_vao_no_lembrete(ambiente):
    cliente, db, estado = ambiente
    tokens = _preparar(cliente, db, estado)
    estado["user"] = db.query(User).get(1)

    padrao = cliente.get("/api/v1/lembretes/1").json()
    assert (padrao["som"], padrao["volume"]) == ("desligado", "medio")

    # Site antigo (sem os campos) não muda o alarme.
    assert cliente.put("/api/v1/lembretes/1", json={"enabled": True, "intervalo": 2, "unidade": "horas"}).status_code == 200
    assert cliente.get("/api/v1/lembretes/1").json()["som"] == "desligado"

    # Desligado: o lembrete sai sem os campos de alarme.
    lembrete.disparar_familia(db, 1)
    r = _enviar(cliente, tokens[16], latitude=-23.55, longitude=-46.63).json()["avisos"]
    assert len(r) == 1 and r[0].get("som") is None

    r = cliente.put("/api/v1/lembretes/1", json={"enabled": True, "intervalo": 2, "unidade": "horas", "som": "MP3", "volume": "alto"})
    assert r.status_code == 200 and (r.json()["som"], r.json()["volume"]) == ("mp3", "alto")
    assert cliente.put("/api/v1/lembretes/1", json={"som": "sirene"}).status_code == 422
    assert cliente.put("/api/v1/lembretes/1", json={"volume": "maximo"}).status_code == 422

    lembrete.disparar_familia(db, 1)
    r = _enviar(cliente, tokens[17], latitude=-23.55, longitude=-46.63).json()["avisos"]
    assert [(a["som"], a["volume"]) for a in r] == [("mp3", "alto")], r
    config = db.query(FamilyLembreteConfig).filter(FamilyLembreteConfig.family_id == 1).one()
    assert config.som == "mp3"


def test_teste_com_mp3_pede_app_2_0_10(ambiente):
    cliente, db, estado = ambiente
    _preparar(cliente, db, estado)
    _app_adulto(db, 1)
    from app.models.app_android import AppDispositivoAdulto
    aparelho = db.query(AppDispositivoAdulto).filter(AppDispositivoAdulto.user_id == 1).one()
    estado["user"] = db.query(User).get(1)
    aparelho.app_versao = avisos_app.VERSAO_MINIMA_ALARME
    db.commit()
    r = cliente.post("/api/v1/notificacoes/lembretes/testar-alarme", json={"som": "mp3", "volume": "alto"})
    assert r.status_code == 200 and r.json()["precisa_atualizar"] is True
    aparelho.app_versao = avisos_app.VERSAO_MINIMA_MP3
    db.commit()
    r = cliente.post("/api/v1/notificacoes/lembretes/testar-alarme", json={"som": "mp3", "volume": "alto"})
    assert r.status_code == 200 and r.json()["precisa_atualizar"] is False
    assert {a.child_user_id for a in db.query(AvisoApp).all()} == {1}
