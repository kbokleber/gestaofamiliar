from datetime import date, datetime
from typing import Any, Literal, Optional

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


class ChecklistIn(BaseModel):
    """Estado do celular que o app 2.0.7+ manda junto com a posição (checklist de envio).
    Só ajustes do Android: nenhum dado pessoal novo. Campos desconhecidos são ignorados."""
    gps: Optional[bool] = None  # localização do aparelho ligada
    sempre: Optional[bool] = None  # "Permitir o tempo todo"
    precisa: Optional[bool] = None  # localização precisa e GPS (alta precisão)
    bateria_livre: Optional[bool] = None  # bateria do app "Sem restrições"
    # O Android não deixa o app conferir o início automático (Xiaomi, Redmi etc.): só o que a pessoa confirmou.
    inicio_automatico: Optional[Literal["confirmado", "pendente", "nao_se_aplica"]] = None
    inicio_automatico_em: Optional[date] = None


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
    # Validado à parte (anotar_checklist): checklist inválido é ignorado e nunca derruba a posição.
    checklist: Optional[Any] = None


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


class ChecklistOut(BaseModel):
    gps: Optional[bool] = None
    sempre: Optional[bool] = None
    precisa: Optional[bool] = None
    bateria_livre: Optional[bool] = None
    inicio_automatico: Optional[str] = None
    inicio_automatico_em: Optional[date] = None


class AparelhoMembroOut(AparelhoOut):
    """Celular no /membros: o de /criancas mais o checklist que o app informou (null no app antigo)."""
    checklist: Optional[ChecklistOut] = None
    checklist_em: Optional[datetime] = None
    app_versao: Optional[int] = None


class MembroOut(CriancaOut):
    """Item de /membros: o mesmo de /criancas mais o campo "adulto". /criancas fica igual ao do app 2.0.4."""
    adulto: bool = False
    # Membro da família (Saúde) escolhido como "quem é" esta pessoa; a foto vem por /fotos.
    family_member_id: Optional[int] = None
    aparelhos: list[AparelhoMembroOut]


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


class VinculoFotoIn(BaseModel):
    """Membro da família (Saúde) que é esta pessoa. null tira o vínculo."""
    family_member_id: Optional[int] = Field(ge=1)


class VinculoFotoOut(BaseModel):
    pessoa_id: int
    family_member_id: Optional[int] = None


class MembroDaFamiliaOut(BaseModel):
    """Opção da lista "Quem é na família": só o necessário para escolher."""
    id: int
    nome: str
    family_id: int
    tem_foto: bool


class FotoNoMapaOut(BaseModel):
    """Miniatura JPEG em base64, sem o prefixo data:."""
    pessoa_id: int
    foto: str


class RevogacaoOut(BaseModel):
    revogado: bool = True


class SosIn(BaseModel):
    """Posição do momento, se o celular conseguiu; sem ela, vale a última conhecida."""
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    accuracy_m: Optional[float] = None
    battery_level: Optional[int] = Field(default=None, ge=0, le=100)
    recorded_at: Optional[datetime] = None


class SosEnviadoOut(BaseModel):
    id: int
    repetido: bool = False
    avisados: int = 0
    motivo: Optional[str] = None


class SosOut(BaseModel):
    id: int
    pessoa_id: int
    nome: str
    adulto: bool = False
    criado_em: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_m: Optional[float] = None
    bateria: Optional[int] = None
    posicao_em: Optional[datetime] = None
    visto_em: Optional[datetime] = None
    visto_por: Optional[str] = None
    motivo: Optional[str] = None


class SosSemDestinatarioOut(BaseModel):
    """Alerta para o admin: SOS que não avisou ninguém. Sem posição (o admin pode não ter sido avisado)."""
    id: int
    nome: str
    criado_em: datetime
    motivo: str


class SosPessoaOut(BaseModel):
    id: int
    nome: str


class SosDestinatariosOut(BaseModel):
    family_id: int
    opcoes: list[SosPessoaOut]
    escolhidos: list[int]
    # Escolhidos que perderam o acesso (sem Localização, inativos ou fora da família): continuam na lista,
    # mas não recebem até voltar a ter acesso. O site avisa.
    sem_acesso: list[SosPessoaOut] = []


class SosDestinatariosIn(BaseModel):
    family_id: Optional[int] = None
    user_ids: list[int] = Field(default_factory=list, max_length=50)
