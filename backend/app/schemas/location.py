from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


Preposicao = Literal["em", "na", "no"]


class PareamentoIn(BaseModel):
    child_user_id: int


class PareamentoOut(BaseModel):
    codigo: str
    expira_em: datetime
    crianca_id: int
    crianca_nome: str
    validade_minutos: int


class ParearDispositivoIn(BaseModel):
    code: str = Field(min_length=4, max_length=32)
    device_label: Optional[str] = Field(default=None, max_length=80)


class ParearDispositivoOut(BaseModel):
    device_token: str
    device_id: int
    crianca_id: int
    crianca_nome: str
    mensagem: str


class PosicaoIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: Optional[float] = None
    speed_mps: Optional[float] = None
    battery_level: Optional[int] = Field(default=None, ge=0, le=100)
    recorded_at: Optional[datetime] = None
    # Enviados pelo app 1.0.2+: versão, notificações liberadas e avisos que ele já mostrou.
    app_versao: Optional[int] = Field(default=None, ge=0)
    notificacoes: Optional[bool] = None
    avisos_recebidos: list[int] = Field(default_factory=list, max_length=50)


class AvisoOut(BaseModel):
    id: int
    tipo: str = "lembrete"
    titulo: str
    texto: str
    url: Optional[str] = None


class PosicaoOut(BaseModel):
    id: int
    recebido: bool = True
    repetido: bool = False
    # Avisos pendentes para a criança (ex.: lembrete de atividades), mostrados pelo app.
    avisos: list[AvisoOut] = []


class StatusLugar(BaseModel):
    codigo: Literal["dentro", "fora", "sem_posicao", "sem_lugares"]
    frase: str
    lugar_id: Optional[int] = None
    lugar_nome: Optional[str] = None


class AparelhoOut(BaseModel):
    id: int
    nome: str
    revogado: bool
    bateria: Optional[int] = None
    atualizado_em: Optional[datetime] = None
    visto_em: Optional[datetime] = None


class CriancaOut(BaseModel):
    id: int
    nome: str
    apelido: Optional[str] = None
    family_id: int
    bateria: Optional[int] = None
    atualizado_em: Optional[datetime] = None
    ha_segundos: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    status: StatusLugar
    aparelhos: list[AparelhoOut]


class MembroOut(CriancaOut):
    """Item de /membros: o mesmo de /criancas mais o campo "adulto". /criancas fica igual ao do app 2.0.4."""
    adulto: bool = False


class PontoTrajeto(BaseModel):
    id: int
    latitude: float
    longitude: float
    accuracy_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    battery_level: Optional[int] = None
    recorded_at: datetime
    device_id: int
    lacuna_antes: bool = False


class ParadaOut(BaseModel):
    inicio: datetime
    fim: datetime
    duracao_segundos: int
    latitude: float
    longitude: float


class EventoLugarOut(BaseModel):
    id: int
    tipo: Literal["chegada", "saida"]
    frase: str
    lugar_nome: str
    lugar_id: Optional[int] = None
    em: datetime
    latitude: float
    longitude: float


class TrajetoOut(BaseModel):
    crianca_id: int
    crianca_nome: str
    dia: str
    fuso: str
    inicio: Optional[datetime] = None
    fim: Optional[datetime] = None
    distancia_m: float
    distancia_km: float
    velocidade_media_kmh: float
    velocidade_maxima_kmh: float
    fonte_velocidade: Literal["pontos", "gps", "mista", "sem_dados"]
    paradas: list[ParadaOut]
    pontos: list[PontoTrajeto]
    eventos: list[EventoLugarOut]


class LugarIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    preposicao: Preposicao = "em"
    endereco: Optional[str] = Field(default=None, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    raio_m: int = Field(default=150, ge=30, le=2000)
    family_id: Optional[int] = None


class LugarOut(BaseModel):
    id: int
    family_id: int
    nome: str
    preposicao: Preposicao
    endereco: Optional[str] = None
    latitude: float
    longitude: float
    raio_m: int


class GeocodificarIn(BaseModel):
    endereco: str = Field(min_length=3, max_length=200)


class GeocodificarOut(BaseModel):
    latitude: float
    longitude: float
    endereco_formatado: str


class ApelidoIn(BaseModel):
    apelido: Optional[str] = Field(default=None, max_length=12)


class ApelidoOut(BaseModel):
    crianca_id: int
    apelido: Optional[str] = None


class RevogacaoOut(BaseModel):
    revogado: bool = True
