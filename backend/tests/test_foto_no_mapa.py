"""Foto no marcador: vínculo manual da pessoa do mapa com o membro da família (Saúde)."""
import base64
from datetime import date, datetime, timezone
from io import BytesIO

import pytest
from PIL import Image

from app.models.healthcare import FamilyMember
from app.models.location import LocationChildSettings
from app.models.user import User
from tests.test_localizacao import _adulto_outra_familia, _parear_adulto, ambiente  # noqa: F401

BASE = "/api/v1/localizacao"


def _imagem(cor="red", tamanho=(1200, 900), formato="JPEG"):
    saida = BytesIO()
    Image.new("RGB", tamanho, cor).save(saida, format=formato)
    return base64.b64encode(saida.getvalue()).decode()


def _membro(db, id_, nome, family_id=1, photo=None, order=0):
    agora = datetime.now(timezone.utc)
    db.add(FamilyMember(id=id_, name=nome, family_id=family_id, photo=photo, birth_date=date(2012, 1, 2), gender="M",
                        relationship_type="filho", allergies="alergia-segredo", notes="nota-segredo", order=order,
                        created_at=agora, updated_at=agora))
    db.commit()


@pytest.fixture()
def familia(ambiente):  # noqa: F811
    cliente, db, estado = ambiente
    _membro(db, 101, "Guilherme Bueno de Oliveira", photo=_imagem(), order=1)
    _membro(db, 102, "Giovana Bueno", photo=None, order=2)
    _membro(db, 103, "Mãe", photo="data:image/png;base64," + _imagem("blue", formato="PNG"), order=3)
    _membro(db, 201, "Primo", family_id=2, photo=_imagem("green"))
    return cliente, db, estado


def _ligar(cliente, pessoa, membro):
    return cliente.put(f"{BASE}/membros/{pessoa}/foto", json={"family_member_id": membro})


def _fotos(cliente):
    return {f["pessoa_id"]: f["foto"] for f in cliente.get(f"{BASE}/fotos").json()}


def _vinculos(cliente):
    return {m["id"]: m["family_member_id"] for m in cliente.get(f"{BASE}/membros").json()}


def test_sem_vinculo_nao_ha_foto_nem_com_nome_igual(familia):
    cliente, db, _ = familia
    _membro(db, 104, "Guilherme", photo=_imagem())  # nome igual ao do mapa: mesmo assim, só com vínculo
    assert _fotos(cliente) == {}
    assert _vinculos(cliente) == {16: None, 17: None}


def test_vincular_mostra_a_miniatura_e_desvincular_tira(familia):
    cliente, db, _ = familia
    r = _ligar(cliente, 16, 101)
    assert (r.status_code, r.json()) == (200, {"pessoa_id": 16, "family_member_id": 101})
    assert _vinculos(cliente) == {16: 101, 17: None}
    fotos = _fotos(cliente)
    assert list(fotos) == [16]
    imagem = Image.open(BytesIO(base64.b64decode(fotos[16])))
    assert imagem.format == "JPEG" and max(imagem.size) == 144
    assert len(fotos[16]) < 20_000
    assert _ligar(cliente, 16, None).status_code == 200
    assert _fotos(cliente) == {} and _vinculos(cliente)[16] is None


def test_membro_sem_foto_ou_com_foto_que_nao_abre_fica_sem_foto(familia):
    cliente, db, _ = familia
    assert _ligar(cliente, 17, 102).status_code == 200
    assert _fotos(cliente) == {}
    inteira = base64.b64decode(_imagem())
    for ruim in ("", "   ", "isto nao e imagem", "javascript:alert(1)", "data:image/svg+xml;base64,PHN2Zz4=",
                 base64.b64encode(b"GIF89a-quebrado").decode(), "/9j/AAAA", base64.b64encode(inteira[:200]).decode()):
        db.query(FamilyMember).filter(FamilyMember.id == 102).update({"photo": ruim})
        db.commit()
        r = cliente.get(f"{BASE}/fotos")
        assert (r.status_code, r.json()) == (200, []), ruim[:30]
    # Uma foto ruim não derruba a boa.
    assert _ligar(cliente, 16, 101).status_code == 200
    assert list(_fotos(cliente)) == [16]


def test_foto_com_prefixo_e_png_viram_jpeg(familia):
    cliente, db, estado = familia
    assert _parear_adulto(cliente, estado, db, 3, device_label="Celular").status_code == 200
    estado["user"] = db.get(User, 1)
    assert _ligar(cliente, 3, 103).status_code == 200
    assert _fotos(cliente)[3].startswith("/9j/")


def test_trocar_de_membro_vale_na_hora(familia):
    cliente, db, _ = familia
    _ligar(cliente, 16, 101)
    antes = _fotos(cliente)[16]
    _membro(db, 105, "Outro", photo=_imagem("yellow"))
    assert _ligar(cliente, 16, 105).status_code == 200
    assert _fotos(cliente)[16] != antes


def test_mesmo_membro_em_duas_pessoas_e_recusado(familia):
    cliente, db, _ = familia
    assert _ligar(cliente, 16, 101).status_code == 200
    r = _ligar(cliente, 17, 101)
    assert r.status_code == 409 and "Guilherme" in r.json()["detail"]
    assert _vinculos(cliente) == {16: 101, 17: None}
    assert _ligar(cliente, 16, 101).status_code == 200  # repetir o próprio vínculo pode
    _ligar(cliente, 16, None)
    assert _ligar(cliente, 17, 101).status_code == 200


def test_outra_familia_nao_e_alcancada(familia):
    cliente, db, estado = familia
    assert _ligar(cliente, 16, 201).status_code == 404  # membro de outra família
    assert _ligar(cliente, 18, 101).status_code == 404  # criança de outra família
    assert _ligar(cliente, 16, 999).status_code == 404
    assert _ligar(cliente, 999, 101).status_code == 404
    assert _ligar(cliente, 16, 101).status_code == 200
    estado["user"] = _adulto_outra_familia(db)
    assert _fotos(cliente) == {}
    assert [m["id"] for m in cliente.get(f"{BASE}/membros-da-familia").json()] == [201]
    assert _ligar(cliente, 16, 201).status_code == 404


def test_se_a_pessoa_muda_de_familia_a_foto_some(familia):
    cliente, db, _ = familia
    _ligar(cliente, 16, 101)
    db.get(User, 16).family_id = 2
    db.commit()
    assert _fotos(cliente) == {} and 16 not in _vinculos(cliente)
    # E se o membro é que mudou de família.
    db.get(User, 16).family_id = 1
    db.get(FamilyMember, 101).family_id = 2
    db.commit()
    assert _fotos(cliente) == {} and _vinculos(cliente)[16] is None


def test_membro_apagado_nao_quebra_o_mapa(familia):
    cliente, db, _ = familia
    _ligar(cliente, 16, 101)
    db.query(FamilyMember).filter(FamilyMember.id == 101).delete()
    db.commit()
    assert _fotos(cliente) == {} and _vinculos(cliente)[16] is None


@pytest.mark.parametrize("corpo", [{}, {"family_member_id": 0}, {"family_member_id": -1}, {"family_member_id": "x"}, {"family_member_id": []}])
def test_corpo_invalido(familia, corpo):
    cliente, _, _ = familia
    assert cliente.put(f"{BASE}/membros/16/foto", json=corpo).status_code == 422


def test_quem_nao_ve_o_mapa_nao_ve_nem_mexe(familia):
    cliente, db, estado = familia
    _ligar(cliente, 16, 101)
    for quem in (2, 16):  # adulto sem o menu Localização; a própria criança
        estado["user"] = db.get(User, quem)
        assert cliente.get(f"{BASE}/fotos").status_code == 403
        assert cliente.get(f"{BASE}/membros-da-familia").status_code == 403
        assert _ligar(cliente, 16, None).status_code == 403
    estado["anonimo"] = True
    assert cliente.get(f"{BASE}/fotos").status_code == 401
    estado["anonimo"] = False
    # Adulto com Localização e sem Saúde vê as fotos do mapa e as opções, sem nada de saúde.
    estado["user"] = db.get(User, 3)
    assert list(_fotos(cliente)) == [16]


def test_opcoes_trazem_so_o_necessario(familia):
    cliente, _, _ = familia
    r = cliente.get(f"{BASE}/membros-da-familia")
    assert r.json() == [
        {"id": 101, "nome": "Guilherme Bueno de Oliveira", "family_id": 1, "tem_foto": True},
        {"id": 102, "nome": "Giovana Bueno", "family_id": 1, "tem_foto": False},
        {"id": 103, "nome": "Mãe", "family_id": 1, "tem_foto": True},
    ]
    assert "segredo" not in r.text


def test_adulto_que_parou_de_compartilhar_perde_a_foto_no_mapa(familia):
    cliente, db, estado = familia
    assert _ligar(cliente, 3, 103).status_code == 404  # ainda não compartilha
    _parear_adulto(cliente, estado, db, 3, device_label="Celular")
    estado["user"] = db.get(User, 1)
    assert _ligar(cliente, 3, 103).status_code == 200 and 3 in _fotos(cliente)
    from app.models.location import LocationDevice
    db.query(LocationDevice).filter(LocationDevice.child_user_id == 3).update({"revoked_at": datetime.now(timezone.utc)})
    db.commit()
    assert 3 not in _fotos(cliente)


def test_apelido_e_vinculo_nao_se_apagam(familia):
    cliente, db, _ = familia
    assert cliente.put(f"{BASE}/membros/16/apelido", json={"apelido": "Kleber Bueno"}).json()["apelido"] == "Kleber Bueno"
    _ligar(cliente, 16, 101)
    assert cliente.put(f"{BASE}/membros/16/apelido", json={"apelido": "Gui"}).status_code == 200
    pref = db.get(LocationChildSettings, 16)
    assert (pref.apelido, pref.family_member_id) == ("Gui", 101)
    _ligar(cliente, 16, None)
    assert db.get(LocationChildSettings, 16).apelido == "Gui"


def test_rota_antiga_das_criancas_e_o_membros_nao_carregam_foto(familia):
    cliente, _, _ = familia
    _ligar(cliente, 16, 101)
    assert all("family_member_id" not in c for c in cliente.get(f"{BASE}/criancas").json())
    assert "/9j/" not in cliente.get(f"{BASE}/membros").text
