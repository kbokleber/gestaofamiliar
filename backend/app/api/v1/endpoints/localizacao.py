"""Mapa da família: o adulto lê, o celular da criança só envia."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_menu
from app.core.config import settings
from app.models.location import LocationDevice
from app.models.user import User
from app.schemas.location import (
    ApelidoIn,
    ApelidoOut,
    CriancaOut,
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
    listar_lugares,
    montar_trajeto,
    registrar_posicao,
    revogar_dispositivo,
    revogar_proprio,
    trocar_codigo,
)
from app.services.limite_tentativas import LimiteTentativas, ip_do_pedido

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
