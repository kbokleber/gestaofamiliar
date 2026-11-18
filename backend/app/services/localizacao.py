"""Regras de pareamento, pontos, trajetos e lugares da família."""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import date, datetime, time, timedelta, timezone
from math import asin, cos, radians, sin, sqrt
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_user_family_ids
from app.core.config import settings
from app.models.location import (
    LocationDevice,
    LocationPairingCode,
    LocationPlace,
    LocationPlaceEvent,
    LocationPlaceState,
    LocationPoint,
)
from app.models.user import User
from app.schemas.location import LugarIn, PosicaoIn

logger = logging.getLogger(__name__)

FUSO = ZoneInfo("America/Sao_Paulo")
CODIGO_MINUTOS = 15
ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
VELOCIDADE_MAX_MPS = 70.0
LACUNA_MAX = timedelta(minutes=30)
PARADA_RAIO_M = 80.0
PARADA_MIN = timedelta(minutes=5)
PONTO_ANTIGO_MAX = timedelta(days=7)
FUTURO_MAX = timedelta(minutes=5)
PREPOSICOES = ("em", "na", "no")
SAIDA = {"em": "de", "na": "da", "no": "do"}


class EnderecoNaoEncontrado(Exception):
    pass


class GeocodificacaoIndisponivel(Exception):
    pass


def nome_de(usuario: User) -> str:
    nome = f"{usuario.first_name or ''} {usuario.last_name or ''}".strip()
    return nome or usuario.username


def como_utc(momento: datetime) -> datetime:
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def hash_segredo(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


def normalizar_codigo(codigo: str) -> str:
    return "".join(caractere for caractere in codigo.upper() if caractere.isalnum())


def gerar_codigo() -> str:
    bruto = "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(8))
    return f"{bruto[:4]}-{bruto[4:]}"


def distancia_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    raio = 6_371_000.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * raio * asin(sqrt(a))


def sugerir_preposicao(nome: str) -> str:
    texto = nome.strip().lower()
    if texto.startswith(("escola", "praça", "praca", "faculdade", "igreja", "academia")):
        return "na"
    if texto.startswith(("colégio", "colegio", "parque", "clube", "curso")):
        return "no"
    return "em"


def frase_evento(tipo: str, preposicao: str, lugar_nome: str) -> str:
    if tipo == "chegada":
        return f"Chegou {preposicao} {lugar_nome}"
    return f"Saiu {SAIDA.get(preposicao, 'de')} {lugar_nome}"


def limites_do_dia(dia: date) -> tuple[datetime, datetime]:
    inicio = datetime.combine(dia, time.min, tzinfo=FUSO)
    return inicio, inicio + timedelta(days=1)


def hoje_sao_paulo() -> date:
    return datetime.now(FUSO).date()


def familias_do_adulto(adulto: User, db: Session) -> list[int]:
    ids = list(get_user_family_ids(adulto, db))
    if not ids and adulto.family_id:
        ids = [adulto.family_id]
    vistas: list[int] = []
    for family_id in ids:
        if family_id not in vistas:
            vistas.append(family_id)
    if not vistas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário não possui uma família associada.",
        )
    return vistas


def obter_crianca(db: Session, familias: list[int], child_id: int) -> User:
    crianca = (
        db.query(User)
        .filter(User.id == child_id, User.family_id.in_(familias), User.is_child.is_(True))
        .first()
    )
    if crianca is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Criança não encontrada nesta família.",
        )
    return crianca


def familia_do_cadastro(adulto: User, db: Session, family_id: Optional[int]) -> int:
    familias = familias_do_adulto(adulto, db)
    if family_id is not None:
        if family_id not in familias:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a esta família.",
            )
        return family_id
    if len(familias) == 1:
        return familias[0]
    if adulto.family_id in familias:
        return adulto.family_id
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Escolha a família do lugar.",
    )


def escolher_lugar(latitude: float, longitude: float, lugares: list[LocationPlace]) -> Optional[LocationPlace]:
    dentro: list[tuple[int, float, int, LocationPlace]] = []
    for lugar in lugares:
        distancia = distancia_m(latitude, longitude, lugar.latitude, lugar.longitude)
        if distancia <= lugar.raio_m:
            dentro.append((lugar.raio_m, distancia, lugar.id, lugar))
    if not dentro:
        return None
    dentro.sort()
    return dentro[0][3]


def status_da_crianca(crianca: User, ponto: Optional[LocationPoint], lugares: list[LocationPlace]) -> dict:
    nome = nome_de(crianca)
    if not lugares:
        return {"codigo": "sem_lugares", "frase": "Nenhum lugar cadastrado", "lugar_id": None, "lugar_nome": None}
    if ponto is None:
        return {
            "codigo": "sem_posicao",
            "frase": f"{nome} ainda não enviou localização",
            "lugar_id": None,
            "lugar_nome": None,
        }
    lugar = escolher_lugar(ponto.latitude, ponto.longitude, lugares)
    if lugar is None:
        return {
            "codigo": "fora",
            "frase": f"{nome} está fora dos lugares cadastrados",
            "lugar_id": None,
            "lugar_nome": None,
        }
    return {
        "codigo": "dentro",
        "frase": f"{nome} está {lugar.preposicao} {lugar.nome}",
        "lugar_id": lugar.id,
        "lugar_nome": lugar.nome,
    }


def ultimo_ponto(db: Session, child_id: int, device_id: Optional[int] = None) -> Optional[LocationPoint]:
    consulta = db.query(LocationPoint).filter(LocationPoint.child_user_id == child_id)
    if device_id is not None:
        consulta = consulta.filter(LocationPoint.device_id == device_id)
    return consulta.order_by(LocationPoint.recorded_at.desc(), LocationPoint.id.desc()).first()


def _velocidade_kmh(speed_mps: Optional[float]) -> Optional[float]:
    if speed_mps is None:
        return None
    return round(speed_mps * 3.6, 1)


def listar_criancas(db: Session, adulto: User) -> list[dict]:
    familias = familias_do_adulto(adulto, db)
    criancas = (
        db.query(User)
        .filter(User.is_child.is_(True), User.is_active.is_(True), User.family_id.in_(familias))
        .order_by(User.first_name, User.last_name, User.username)
        .all()
    )
    lugares = db.query(LocationPlace).filter(LocationPlace.family_id.in_(familias)).all()
    agora = datetime.now(timezone.utc)
    saida = []
    for crianca in criancas:
        ponto = ultimo_ponto(db, crianca.id)
        aparelhos_db = (
            db.query(LocationDevice)
            .filter(LocationDevice.child_user_id == crianca.id)
            .order_by(LocationDevice.id.asc())
            .all()
        )
        aparelhos = []
        for aparelho in aparelhos_db:
            ultimo = ultimo_ponto(db, crianca.id, aparelho.id)
            aparelhos.append({
                "id": aparelho.id,
                "nome": aparelho.label or "Celular",
                "revogado": aparelho.revoked_at is not None,
                "bateria": ultimo.battery_level if ultimo is not None else None,
                "atualizado_em": como_utc(ultimo.recorded_at) if ultimo is not None else None,
                "visto_em": como_utc(aparelho.last_seen_at) if aparelho.last_seen_at else None,
            })
        da_familia = [lugar for lugar in lugares if lugar.family_id == crianca.family_id]
        atualizado = como_utc(ponto.recorded_at) if ponto is not None else None
        saida.append({
            "id": crianca.id,
            "nome": nome_de(crianca),
            "family_id": crianca.family_id,
            "bateria": ponto.battery_level if ponto is not None else None,
            "atualizado_em": atualizado,
            "ha_segundos": int((agora - atualizado).total_seconds()) if atualizado else None,
            "latitude": ponto.latitude if ponto is not None else None,
            "longitude": ponto.longitude if ponto is not None else None,
            "accuracy_m": ponto.accuracy_m if ponto is not None else None,
            "speed_kmh": _velocidade_kmh(ponto.speed_mps) if ponto is not None else None,
            "status": status_da_crianca(crianca, ponto, da_familia),
            "aparelhos": aparelhos,
        })
    return saida


def detectar_paradas(pontos: list) -> list[dict]:
    paradas = []
    total = len(pontos)
    indice = 0
    while indice < total:
        fim = indice + 1
        ancora = pontos[indice]
        while fim < total:
            if distancia_m(ancora.latitude, ancora.longitude, pontos[fim].latitude, pontos[fim].longitude) <= PARADA_RAIO_M:
                fim += 1
            else:
                break
        if fim - indice >= 2:
            inicio_em = como_utc(pontos[indice].recorded_at)
            fim_em = como_utc(pontos[fim - 1].recorded_at)
            if fim_em - inicio_em >= PARADA_MIN:
                faixa = pontos[indice:fim]
                paradas.append({
                    "inicio": inicio_em,
                    "fim": fim_em,
                    "duracao_segundos": int((fim_em - inicio_em).total_seconds()),
                    "latitude": sum(ponto.latitude for ponto in faixa) / len(faixa),
                    "longitude": sum(ponto.longitude for ponto in faixa) / len(faixa),
                })
                indice = fim
                continue
        indice += 1
    return paradas


def _na_parada(momento: datetime, paradas: list[dict]) -> bool:
    for parada in paradas:
        if parada["inicio"] <= momento <= parada["fim"]:
            return True
    return False


def calcular_trajeto(pontos: list) -> dict:
    ordenados = sorted(pontos, key=lambda ponto: (como_utc(ponto.recorded_at), getattr(ponto, "id", 0)))
    paradas = detectar_paradas(ordenados)
    distancia = 0.0
    tempo_movimento = 0.0
    velocidade_max = 0.0
    segmentos = 0
    segmentos_gps = 0
    serializados = []

    for indice, ponto in enumerate(ordenados):
        lacuna = False
        if indice > 0:
            anterior = ordenados[indice - 1]
            t0 = como_utc(anterior.recorded_at)
            t1 = como_utc(ponto.recorded_at)
            dt_s = (t1 - t0).total_seconds()
            trecho = distancia_m(anterior.latitude, anterior.longitude, ponto.latitude, ponto.longitude)
            if dt_s <= 0 or dt_s > LACUNA_MAX.total_seconds():
                lacuna = True
            else:
                derivada = trecho / dt_s
                if derivada > VELOCIDADE_MAX_MPS:
                    lacuna = True
                else:
                    distancia += trecho
                    segmentos += 1
                    gps = ponto.speed_mps
                    if gps is not None and 0 <= gps <= VELOCIDADE_MAX_MPS:
                        segmentos_gps += 1
                        velocidade_max = max(velocidade_max, gps, derivada)
                    else:
                        velocidade_max = max(velocidade_max, derivada)
                    if not (_na_parada(t0, paradas) and _na_parada(t1, paradas)):
                        tempo_movimento += dt_s
        gps_kmh = _velocidade_kmh(ponto.speed_mps if ponto.speed_mps is not None and 0 <= ponto.speed_mps <= VELOCIDADE_MAX_MPS else None)
        serializados.append({
            "id": ponto.id,
            "latitude": ponto.latitude,
            "longitude": ponto.longitude,
            "accuracy_m": ponto.accuracy_m,
            "speed_kmh": gps_kmh,
            "battery_level": ponto.battery_level,
            "recorded_at": como_utc(ponto.recorded_at),
            "device_id": ponto.device_id,
            "lacuna_antes": lacuna,
        })

    if segmentos and segmentos_gps == segmentos:
        fonte = "gps"
    elif segmentos_gps:
        fonte = "mista"
    elif segmentos:
        fonte = "pontos"
    else:
        fonte = "sem_dados"

    media = (distancia / tempo_movimento) * 3.6 if tempo_movimento > 0 else 0.0
    return {
        "inicio": serializados[0]["recorded_at"] if serializados else None,
        "fim": serializados[-1]["recorded_at"] if serializados else None,
        "distancia_m": round(distancia, 1),
        "distancia_km": round(distancia / 1000, 2),
        "velocidade_media_kmh": round(media, 1),
        "velocidade_maxima_kmh": round(velocidade_max * 3.6, 1),
        "fonte_velocidade": fonte,
        "paradas": paradas,
        "pontos": serializados,
    }


def montar_trajeto(db: Session, adulto: User, child_id: int, dia: date) -> dict:
    familias = familias_do_adulto(adulto, db)
    crianca = obter_crianca(db, familias, child_id)
    inicio, fim = limites_do_dia(dia)
    margem = timedelta(hours=14)
    pontos = (
        db.query(LocationPoint)
        .filter(
            LocationPoint.child_user_id == crianca.id,
            LocationPoint.family_id == crianca.family_id,
            LocationPoint.recorded_at >= inicio - margem,
            LocationPoint.recorded_at < fim + margem,
        )
        .order_by(LocationPoint.recorded_at.asc(), LocationPoint.id.asc())
        .all()
    )
    do_dia = [ponto for ponto in pontos if inicio <= como_utc(ponto.recorded_at) < fim]
    eventos = (
        db.query(LocationPlaceEvent)
        .filter(
            LocationPlaceEvent.child_user_id == crianca.id,
            LocationPlaceEvent.family_id == crianca.family_id,
            LocationPlaceEvent.recorded_at >= inicio - margem,
            LocationPlaceEvent.recorded_at < fim + margem,
        )
        .order_by(LocationPlaceEvent.recorded_at.asc(), LocationPlaceEvent.id.asc())
        .all()
    )
    do_dia_eventos = [evento for evento in eventos if inicio <= como_utc(evento.recorded_at) < fim]
    calculado = calcular_trajeto(do_dia)
    calculado.update({
        "crianca_id": crianca.id,
        "crianca_nome": nome_de(crianca),
        "dia": dia.isoformat(),
        "fuso": "America/Sao_Paulo",
        "eventos": [_serializar_evento(evento) for evento in do_dia_eventos],
    })
    return calculado


def _serializar_evento(evento: LocationPlaceEvent) -> dict:
    return {
        "id": evento.id,
        "tipo": evento.tipo,
        "frase": frase_evento(evento.tipo, evento.preposicao, evento.lugar_nome),
        "lugar_nome": evento.lugar_nome,
        "lugar_id": evento.place_id,
        "em": como_utc(evento.recorded_at),
        "latitude": evento.latitude,
        "longitude": evento.longitude,
    }


def gerar_pareamento(db: Session, adulto: User, child_id: int) -> dict:
    crianca = obter_crianca(db, familias_do_adulto(adulto, db), child_id)
    if not crianca.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta criança está inativa.")
    codigo = gerar_codigo()
    agora = datetime.now(timezone.utc)
    expira = agora + timedelta(minutes=CODIGO_MINUTOS)
    db.add(LocationPairingCode(
        family_id=crianca.family_id,
        child_user_id=crianca.id,
        code_hash=hash_segredo(normalizar_codigo(codigo)),
        expires_at=expira,
        created_by_id=adulto.id,
        created_at=agora,
    ))
    db.commit()
    return {
        "codigo": codigo,
        "expira_em": expira,
        "crianca_id": crianca.id,
        "crianca_nome": nome_de(crianca),
        "validade_minutos": CODIGO_MINUTOS,
    }


def trocar_codigo(db: Session, codigo: str, rotulo: Optional[str]) -> dict:
    normalizado = normalizar_codigo(codigo)
    if len(normalizado) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código de pareamento inválido.")
    registro = (
        db.query(LocationPairingCode)
        .filter(LocationPairingCode.code_hash == hash_segredo(normalizado))
        .first()
    )
    agora = datetime.now(timezone.utc)
    if registro is None or registro.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido ou já usado.")
    if como_utc(registro.expires_at) < agora:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código expirado. Peça um novo no navegador.",
        )
    crianca = db.query(User).filter(User.id == registro.child_user_id).first()
    if crianca is None or not crianca.is_child or not crianca.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta criança não pode ser pareada.")
    token = secrets.token_urlsafe(32)
    nome = (rotulo or "").strip() or f"Celular de {nome_de(crianca)}"
    aparelho = LocationDevice(
        family_id=registro.family_id,
        child_user_id=crianca.id,
        token_hash=hash_segredo(token),
        label=nome[:80],
        created_by_id=registro.created_by_id,
        created_at=agora,
    )
    registro.used_at = agora
    db.add(aparelho)
    db.commit()
    db.refresh(aparelho)
    logger.info("celular pareado device_id=%s child_id=%s", aparelho.id, crianca.id)
    return {
        "device_token": token,
        "device_id": aparelho.id,
        "crianca_id": crianca.id,
        "crianca_nome": nome_de(crianca),
        "mensagem": "Celular pareado. O token fica só neste aparelho. Um adulto pode revogar o acesso no site.",
    }


def buscar_dispositivo(db: Session, token: str) -> Optional[LocationDevice]:
    if not token or len(token.strip()) < 20:
        return None
    aparelho = (
        db.query(LocationDevice)
        .filter(LocationDevice.token_hash == hash_segredo(token.strip()))
        .first()
    )
    if aparelho is None or aparelho.revoked_at is not None:
        return None
    crianca = db.query(User).filter(User.id == aparelho.child_user_id).first()
    if crianca is None or not crianca.is_active or not crianca.is_child:
        return None
    return aparelho


def _ponto_repetido(db: Session, device_id: int, recorded: datetime) -> Optional[LocationPoint]:
    recentes = (
        db.query(LocationPoint)
        .filter(LocationPoint.device_id == device_id)
        .order_by(LocationPoint.id.desc())
        .limit(8)
        .all()
    )
    for ponto in recentes:
        if abs((como_utc(ponto.recorded_at) - recorded).total_seconds()) < 1:
            return ponto
    return None


def _sanear_velocidade(valor: Optional[float]) -> Optional[float]:
    if valor is None:
        return None
    if valor < 0 or valor > VELOCIDADE_MAX_MPS:
        return None
    return valor


def _sanear_precisao(valor: Optional[float]) -> Optional[float]:
    if valor is None:
        return None
    if valor < 0 or valor > 100_000:
        return None
    return valor


def registrar_presenca(db: Session, ponto: LocationPoint, lugares: list[LocationPlace]) -> None:
    agora = datetime.now(timezone.utc)
    for lugar in lugares:
        if lugar.family_id != ponto.family_id:
            continue
        dentro = distancia_m(ponto.latitude, ponto.longitude, lugar.latitude, lugar.longitude) <= lugar.raio_m
        estado = (
            db.query(LocationPlaceState)
            .filter(
                LocationPlaceState.child_user_id == ponto.child_user_id,
                LocationPlaceState.place_id == lugar.id,
            )
            .first()
        )
        if estado is None:
            db.add(LocationPlaceState(
                child_user_id=ponto.child_user_id,
                place_id=lugar.id,
                inside=1 if dentro else 0,
                updated_at=agora,
            ))
            continue
        estava = bool(estado.inside)
        if estava == dentro:
            continue
        estado.inside = 1 if dentro else 0
        estado.updated_at = agora
        db.add(LocationPlaceEvent(
            family_id=ponto.family_id,
            child_user_id=ponto.child_user_id,
            device_id=ponto.device_id,
            place_id=lugar.id,
            lugar_nome=lugar.nome,
            preposicao=lugar.preposicao,
            tipo="chegada" if dentro else "saida",
            recorded_at=ponto.recorded_at,
            latitude=ponto.latitude,
            longitude=ponto.longitude,
        ))


def registrar_posicao(db: Session, aparelho: LocationDevice, dados: PosicaoIn) -> dict:
    agora = datetime.now(timezone.utc)
    recorded = como_utc(dados.recorded_at) if dados.recorded_at else agora
    if recorded > agora + FUTURO_MAX:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O horário da localização está no futuro.")
    if recorded < agora - PONTO_ANTIGO_MAX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A localização é antiga demais para registrar.",
        )
    repetido = _ponto_repetido(db, aparelho.id, recorded)
    if repetido is not None:
        return {"id": repetido.id, "recebido": True, "repetido": True}

    ponto = LocationPoint(
        device_id=aparelho.id,
        family_id=aparelho.family_id,
        child_user_id=aparelho.child_user_id,
        latitude=dados.latitude,
        longitude=dados.longitude,
        accuracy_m=_sanear_precisao(dados.accuracy_m),
        speed_mps=_sanear_velocidade(dados.speed_mps),
        battery_level=dados.battery_level,
        recorded_at=recorded,
        received_at=agora,
    )
    aparelho.last_seen_at = agora
    db.add(ponto)
    db.flush()
    lugares = db.query(LocationPlace).filter(LocationPlace.family_id == aparelho.family_id).all()
    registrar_presenca(db, ponto, lugares)
    db.commit()
    db.refresh(ponto)
    logger.info("posicao recebida device_id=%s ponto_id=%s", aparelho.id, ponto.id)
    return {"id": ponto.id, "recebido": True, "repetido": False}


def _aparelho_da_familia(db: Session, familias: list[int], device_id: int) -> LocationDevice:
    aparelho = (
        db.query(LocationDevice)
        .filter(LocationDevice.id == device_id, LocationDevice.family_id.in_(familias))
        .first()
    )
    if aparelho is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aparelho não encontrado nesta família.")
    return aparelho


def revogar_dispositivo(db: Session, adulto: User, device_id: int) -> dict:
    aparelho = _aparelho_da_familia(db, familias_do_adulto(adulto, db), device_id)
    if aparelho.revoked_at is None:
        aparelho.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return {"revogado": True}


def revogar_proprio(db: Session, aparelho: LocationDevice) -> dict:
    if aparelho.revoked_at is None:
        aparelho.revoked_at = datetime.now(timezone.utc)
        db.commit()
    return {"revogado": True}


def _limpar_endereco(endereco: Optional[str]) -> Optional[str]:
    if endereco is None:
        return None
    texto = " ".join(endereco.split())
    return texto or None


def _dados_lugar(dados: LugarIn) -> dict:
    nome = " ".join(dados.nome.split())
    if not nome:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Dê um nome ao lugar.")
    if dados.preposicao not in PREPOSICOES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use em, na ou no.")
    return {
        "nome": nome[:80],
        "preposicao": dados.preposicao,
        "endereco": _limpar_endereco(dados.endereco),
        "latitude": dados.latitude,
        "longitude": dados.longitude,
        "raio_m": dados.raio_m,
    }


def serializar_lugar(lugar: LocationPlace) -> dict:
    return {
        "id": lugar.id,
        "family_id": lugar.family_id,
        "nome": lugar.nome,
        "preposicao": lugar.preposicao,
        "endereco": lugar.endereco,
        "latitude": lugar.latitude,
        "longitude": lugar.longitude,
        "raio_m": lugar.raio_m,
    }


def listar_lugares(db: Session, adulto: User) -> list[dict]:
    familias = familias_do_adulto(adulto, db)
    lugares = (
        db.query(LocationPlace)
        .filter(LocationPlace.family_id.in_(familias))
        .order_by(LocationPlace.nome.asc())
        .all()
    )
    return [serializar_lugar(lugar) for lugar in lugares]


def criar_lugar(db: Session, adulto: User, dados: LugarIn) -> dict:
    family_id = familia_do_cadastro(adulto, db, dados.family_id)
    agora = datetime.now(timezone.utc)
    lugar = LocationPlace(
        family_id=family_id,
        created_by_id=adulto.id,
        created_at=agora,
        updated_at=agora,
        **_dados_lugar(dados),
    )
    db.add(lugar)
    db.commit()
    db.refresh(lugar)
    return serializar_lugar(lugar)


def _lugar_da_familia(db: Session, familias: list[int], lugar_id: int) -> LocationPlace:
    lugar = (
        db.query(LocationPlace)
        .filter(LocationPlace.id == lugar_id, LocationPlace.family_id.in_(familias))
        .first()
    )
    if lugar is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lugar não encontrado nesta família.")
    return lugar


def atualizar_lugar(db: Session, adulto: User, lugar_id: int, dados: LugarIn) -> dict:
    lugar = _lugar_da_familia(db, familias_do_adulto(adulto, db), lugar_id)
    for campo, valor in _dados_lugar(dados).items():
        setattr(lugar, campo, valor)
    lugar.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lugar)
    return serializar_lugar(lugar)


def excluir_lugar(db: Session, adulto: User, lugar_id: int) -> None:
    lugar = _lugar_da_familia(db, familias_do_adulto(adulto, db), lugar_id)
    db.query(LocationPlaceState).filter(LocationPlaceState.place_id == lugar.id).delete()
    db.delete(lugar)
    db.commit()


def consultar_nominatim(consulta: str, *, countrycodes: Optional[str]) -> Optional[dict]:
    params = {"q": consulta, "format": "jsonv2", "limit": "1"}
    if countrycodes:
        params["countrycodes"] = countrycodes
    url = settings.NOMINATIM_URL.rstrip("/") + "/search"
    try:
        with httpx.Client(timeout=8.0) as cliente:
            resposta = cliente.get(
                url,
                params=params,
                headers={
                    "User-Agent": settings.NOMINATIM_USER_AGENT,
                    "Accept-Language": "pt-BR",
                },
            )
            resposta.raise_for_status()
            dados = resposta.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("geocodificacao indisponivel: %s", type(exc).__name__)
        raise GeocodificacaoIndisponivel from exc
    if not isinstance(dados, list) or not dados:
        return None
    item = dados[0]
    try:
        latitude = float(item["lat"])
        longitude = float(item["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise GeocodificacaoIndisponivel from exc
    return {
        "latitude": latitude,
        "longitude": longitude,
        "endereco_formatado": item.get("display_name") or consulta,
    }


def geocodificar_endereco(endereco: str) -> dict:
    consulta = " ".join(endereco.split())
    if len(consulta) < 3:
        raise EnderecoNaoEncontrado("Informe um endereço mais completo.")
    achado = consultar_nominatim(consulta, countrycodes="br")
    if achado is None:
        achado = consultar_nominatim(consulta, countrycodes=None)
    if achado is None:
        raise EnderecoNaoEncontrado("Não encontrei esse endereço. Marque o ponto no mapa.")
    return achado
