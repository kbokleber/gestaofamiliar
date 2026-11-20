"""Mapa da família: o adulto lê; o celular da criança envia; o adulto pode compartilhar a própria posição."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_menu
from app.core.config import settings
from app.models.location import LocationDevice
from app.models.user import User
from app.schemas.location import (
    ApelidoIn,
    ApelidoOut,
    CriancaOut,
    MembroOut,
    GeocodificarIn,
    GeocodificarOut,
    LugarIn,
    LugarOut,
    PareamentoIn,
    PareamentoOut,
    ParearDispositivoIn,
    ParearDispositivoOut,
    PosicaoIn,
    PosicaoOut,
    RevogacaoOut,
    SosDestinatariosIn,
    SosDestinatariosOut,
    SosEnviadoOut,
    SosIn,
    SosOut,
    SosSemDestinatarioOut,
    TrajetoOut,
)
from app.services.localizacao import (
    EnderecoNaoEncontrado,
    GeocodificacaoIndisponivel,
    atualizar_lugar,
    buscar_dispositivo,
    criar_lugar,
    definir_apelido,
    excluir_lugar,
    geocodificar_endereco,
    gerar_pareamento,
    hoje_sao_paulo,
    listar_criancas,
    listar_membros,
    parear_adulto_logado,
    listar_lugares,
    montar_trajeto,
    registrar_posicao,
    revogar_dispositivo,
    revogar_proprio,
    trocar_codigo,
    parear_crianca_logada,
)
from app.services.limite_tentativas import LimiteTentativas, ip_do_pedido
from app.services import sos as servico_sos

router = APIRouter()

# Pareamento sem login: 10 tentativas por IP e 100 no total a cada 15 minutos.
limite_pareamento_ip = LimiteTentativas(maximo=10, janela_segundos=15 * 60)
limite_pareamento_total = LimiteTentativas(maximo=100, janela_segundos=15 * 60)
device_token_header = APIKeyHeader(name="X-Device-Token", auto_error=False)


def adulto_localizacao(current_user: User = Depends(require_menu("localizacao"))) -> User:
    return current_user


def dispositivo_atual(
    token: Optional[str] = Security(device_token_header),
    db: Session = Depends(get_db),
) -> LocationDevice:
    aparelho = buscar_dispositivo(db, token or "")
    if aparelho is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Aparelho não pareado ou token revogado.",
        )
    return aparelho


@router.get("/criancas", response_model=list[CriancaOut])
def ler_criancas(
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    """Última posição, bateria e frase do lugar de cada criança da família."""
    return listar_criancas(db, adulto)


@router.get("/criancas/{child_id}/trajeto", response_model=TrajetoOut)
def ler_trajeto(
    child_id: int,
    dia: Optional[date] = Query(None, description="Dia em America/Sao_Paulo, AAAA-MM-DD"),
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return montar_trajeto(db, adulto, child_id, dia or hoje_sao_paulo())


@router.put("/criancas/{child_id}/apelido", response_model=ApelidoOut)
def salvar_apelido(
    child_id: int,
    dados: ApelidoIn,
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    """Apelido que aparece no marcador do mapa."""
    return definir_apelido(db, adulto, child_id, dados.apelido)


@router.get("/membros", response_model=list[MembroOut])
def ler_membros(
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    """Crianças e adultos que compartilham a posição. Só para adultos com o menu Localização."""
    return listar_membros(db, adulto)


@router.get("/membros/{membro_id}/trajeto", response_model=TrajetoOut)
def ler_trajeto_membro(
    membro_id: int,
    dia: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return montar_trajeto(db, adulto, membro_id, dia or hoje_sao_paulo(), com_adultos=True)


@router.put("/membros/{membro_id}/apelido", response_model=ApelidoOut)
def salvar_apelido_membro(
    membro_id: int,
    dados: ApelidoIn,
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return definir_apelido(db, adulto, membro_id, dados.apelido, com_adultos=True)


@router.post("/pareamentos", response_model=PareamentoOut)
def criar_pareamento(
    dados: PareamentoIn,
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return gerar_pareamento(db, adulto, dados.child_user_id)


@router.post("/dispositivos/{device_id}/revogar", response_model=RevogacaoOut)
def revogar(
    device_id: int,
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return revogar_dispositivo(db, adulto, device_id)


@router.get("/lugares", response_model=list[LugarOut])
def ler_lugares(
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return listar_lugares(db, adulto)


@router.post("/lugares", response_model=LugarOut, status_code=status.HTTP_201_CREATED)
def novo_lugar(
    dados: LugarIn,
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return criar_lugar(db, adulto, dados)


@router.post("/lugares/geocodificar", response_model=GeocodificarOut)
def buscar_endereco(
    dados: GeocodificarIn,
    _: User = Depends(adulto_localizacao),
):
    try:
        return geocodificar_endereco(dados.endereco)
    except EnderecoNaoEncontrado as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GeocodificacaoIndisponivel as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível consultar o mapa de endereços. Marque o ponto no mapa.",
        ) from exc


@router.put("/lugares/{lugar_id}", response_model=LugarOut)
def editar_lugar(
    lugar_id: int,
    dados: LugarIn,
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return atualizar_lugar(db, adulto, lugar_id, dados)


@router.delete("/lugares/{lugar_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_lugar(
    lugar_id: int,
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    excluir_lugar(db, adulto, lugar_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


class ParearMeIn(BaseModel):
    device_label: Optional[str] = Field(default=None, max_length=80)
    # Token antigo deste mesmo celular (ex.: estava ligado a outra criança): é revogado na troca.
    token_anterior: Optional[str] = Field(default=None, max_length=200)


@router.post("/dispositivos/parear-me", response_model=ParearDispositivoOut)
def parear_pelo_login(
    dados: ParearMeIn,
    db: Session = Depends(get_db),
    usuario: User = Depends(get_current_user),
):
    """O app da criança, já logado com a conta dela, conecta o celular sem código de pareamento."""
    return parear_crianca_logada(db, usuario, dados.device_label, dados.token_anterior)


@router.post("/dispositivos/parear-adulto", response_model=ParearDispositivoOut)
def parear_adulto(
    dados: ParearMeIn,
    db: Session = Depends(get_db),
    adulto: User = Depends(get_current_user),
):
    """O app do adulto, logado com a conta dele, passa a compartilhar a posição dele com os adultos da família.
    Vale para quem vê o mapa e para quem só é visto (avós); a regra fica em parear_adulto_logado."""
    return parear_adulto_logado(db, adulto, dados.device_label, dados.token_anterior)


@router.post("/dispositivos/parear", response_model=ParearDispositivoOut)
def parear_celular(dados: ParearDispositivoIn, request: Request, db: Session = Depends(get_db)):
    """O celular troca o código por um token que só serve para enviar localização."""
    ip = ip_do_pedido(request, settings.PROXIES_CONFIAVEIS)
    if limite_pareamento_ip.excedido(ip) or limite_pareamento_total.excedido("todos"):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de pareamento. Aguarde 15 minutos e tente de novo.",
        )
    limite_pareamento_ip.registrar(ip)
    limite_pareamento_total.registrar("todos")
    return trocar_codigo(db, dados.code, dados.device_label)


@router.post("/dispositivos/posicao", response_model=PosicaoOut)
def enviar_posicao(
    dados: PosicaoIn,
    aparelho: LocationDevice = Depends(dispositivo_atual),
    db: Session = Depends(get_db),
):
    return registrar_posicao(db, aparelho, dados)


@router.post("/dispositivos/revogar-me", response_model=RevogacaoOut)
def revogar_este_celular(
    aparelho: LocationDevice = Depends(dispositivo_atual),
    db: Session = Depends(get_db),
):
    return revogar_proprio(db, aparelho)


# ---------------------------------------------------------------- SOS

@router.post("/dispositivos/sos", response_model=SosEnviadoOut)
def pedir_socorro(
    dados: SosIn,
    aparelho: LocationDevice = Depends(dispositivo_atual),
    db: Session = Depends(get_db),
):
    """Botão SOS do app (criança ou adulto que compartilha). Avisa só os familiares escolhidos.
    Um SOS por celular a cada 2 minutos: repetir dentro desse tempo devolve o mesmo pedido."""
    return servico_sos.registrar_sos(db, aparelho, dados)


@router.get("/sos", response_model=list[SosOut])
def ler_sos(db: Session = Depends(get_db), adulto: User = Depends(adulto_localizacao)):
    return servico_sos.listar_sos(db, adulto)


@router.get("/sos/sem-destinatario", response_model=list[SosSemDestinatarioOut])
def ler_sos_sem_destinatario(db: Session = Depends(get_db), adulto: User = Depends(adulto_localizacao)):
    """Alerta só para o admin: SOS que não avisou ninguém nas últimas 24 h (sem posição)."""
    return servico_sos.sos_sem_destinatario(db, adulto)


@router.post("/sos/{sos_id}/visto", response_model=SosOut)
def marcar_sos_visto(sos_id: int, db: Session = Depends(get_db), adulto: User = Depends(adulto_localizacao)):
    return servico_sos.marcar_visto(db, adulto, sos_id)


@router.get("/sos/destinatarios", response_model=SosDestinatariosOut)
def ler_destinatarios_sos(
    family_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return servico_sos.ler_destinatarios(db, adulto, family_id)


@router.put("/sos/destinatarios", response_model=SosDestinatariosOut)
def salvar_destinatarios_sos(
    dados: SosDestinatariosIn,
    db: Session = Depends(get_db),
    adulto: User = Depends(adulto_localizacao),
):
    return servico_sos.salvar_destinatarios(db, adulto, dados.family_id, dados.user_ids)
