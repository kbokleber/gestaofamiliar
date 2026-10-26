from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

CategoriaAvaliacao = Literal[
    "AV1", "AV2", "REDACAO", "PRODUTIVIDADE", "RECUPERACAO", "SUBSTITUTIVA", "OUTRO",
]
TipoEvento = Literal[
    "INICIO_BIMESTRE", "TERMINO_BIMESTRE", "RECESSO", "SEMANA_AV1", "SEMANA_AV2",
    "SEMANA_RECUPERACAO", "DIVULGACAO_RESULTADO", "PROVAS_SUBSTITUTIVAS", "OUTRO",
]


def _ponta(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    return valor.strip()


class OcorrenciaIn(BaseModel):
    data_inicio: date
    data_fim: date
    turma: Optional[str] = Field(None, max_length=20)

    @model_validator(mode="after")
    def periodo_valido(self):
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim não pode ser anterior a data_inicio")
        self.turma = _ponta(self.turma) or None
        return self


class ItemIn(BaseModel):
    ordem: int = Field(..., ge=1)
    descricao: str
    pontos: Optional[float] = None
    por_unidade: bool = False
    quantidade: Optional[int] = None

    @model_validator(mode="after")
    def limpar(self):
        self.descricao = _ponta(self.descricao) or ""
        return self


class EventoIn(BaseModel):
    tipo: TipoEvento
    legenda: str = Field(..., max_length=150)
    data_inicio: date
    data_fim: date

    @model_validator(mode="after")
    def periodo_valido(self):
        if self.data_fim < self.data_inicio:
            raise ValueError("data_fim não pode ser anterior a data_inicio")
        self.legenda = _ponta(self.legenda) or ""
        return self


class OrientacaoIn(BaseModel):
    titulo: str
    texto: str

    @model_validator(mode="after")
    def limpar(self):
        self.titulo = _ponta(self.titulo) or ""
        self.texto = _ponta(self.texto) or ""
        return self


class ResumoOrganizacional(BaseModel):
    categoria: str
    disciplina: str
    data_texto: str = ""
    ocorrencias: list[OcorrenciaIn] = []


class DocumentoIn(BaseModel):
    chave_origem: str = Field(..., max_length=120, examples=["2026-B4-EFUND09MA_MB"])
    aluno_ids: list[int] = Field(..., min_length=1)
    comunicado_id: Optional[int] = None
    anexo_idx: Optional[int] = None
    anexo_nome: Optional[str] = Field(None, max_length=255)
    titulo: str = ""
    subtitulo: str = ""
    turma: str = Field("", max_length=60)
    turmas: list[str] = []
    serie: Optional[str] = Field(None, max_length=40)
    bimestre: int = Field(..., ge=1, le=4)
    ano_letivo: int
    escola: Optional[str] = Field(None, max_length=150)
    data_publicacao: Optional[date] = None
    autor: Optional[str] = Field(None, max_length=150)
    aviso: str = ""
    introducao: str = ""
    orientacoes: list[OrientacaoIn] = []
    eventos_escolares: list[EventoIn] = []
    calendario_organizacional: list[ResumoOrganizacional] = []

    @model_validator(mode="after")
    def limpar(self):
        self.chave_origem = _ponta(self.chave_origem) or ""
        self.titulo = _ponta(self.titulo) or ""
        self.subtitulo = _ponta(self.subtitulo) or ""
        self.turma = _ponta(self.turma) or ""
        self.turmas = [item.strip() for item in self.turmas if item and item.strip()]
        self.serie = _ponta(self.serie) or None
        self.escola = _ponta(self.escola) or None
        self.autor = _ponta(self.autor) or None
        self.aviso = _ponta(self.aviso) or ""
        self.introducao = _ponta(self.introducao) or ""
        self.anexo_nome = _ponta(self.anexo_nome) or None
        return self


class AvaliacaoIn(BaseModel):
    chave_origem: str = Field(..., max_length=160)
    disciplina: str = Field(..., max_length=120)
    categoria: CategoriaAvaliacao
    categoria_rotulo: Optional[str] = Field(None, max_length=40)
    sequencia: int = Field(1, ge=1)
    titulo: str = Field(..., max_length=200)
    data_texto: str = Field("", max_length=120)
    ocorrencias: list[OcorrenciaIn] = []
    valor: Optional[float] = None
    valor_texto: Optional[str] = Field(None, max_length=20)
    objeto_conhecimento: str = ""
    criterio_correcao: str = ""
    itens_criterio: list[ItemIn] = []
    material_necessario: Optional[str] = None
    observacoes: Optional[str] = None
    ambiguidades: list[str] = []

    @model_validator(mode="after")
    def limpar(self):
        self.chave_origem = _ponta(self.chave_origem) or ""
        self.disciplina = _ponta(self.disciplina) or ""
        self.categoria_rotulo = _ponta(self.categoria_rotulo) or None
        self.titulo = _ponta(self.titulo) or ""
        self.data_texto = _ponta(self.data_texto) or ""
        self.valor_texto = _ponta(self.valor_texto) or None
        self.objeto_conhecimento = _ponta(self.objeto_conhecimento) or ""
        self.criterio_correcao = _ponta(self.criterio_correcao) or ""
        self.material_necessario = _ponta(self.material_necessario) or None
        self.observacoes = _ponta(self.observacoes) or None
        self.ambiguidades = [_ponta(item) or "" for item in self.ambiguidades]
        return self


class Importacao(BaseModel):
    documento: DocumentoIn
    avaliacoes: list[AvaliacaoIn]


class AvaliacaoCreate(AvaliacaoIn):
    cronograma_id: int
    aluno_ids: Optional[list[int]] = None


class AvaliacaoPut(AvaliacaoIn):
    pass


class AvaliacaoPatch(BaseModel):
    disciplina: Optional[str] = None
    categoria: Optional[CategoriaAvaliacao] = None
    categoria_rotulo: Optional[str] = None
    titulo: Optional[str] = None
    data_texto: Optional[str] = None
    ocorrencias: Optional[list[OcorrenciaIn]] = None
    valor: Optional[float] = None
    valor_texto: Optional[str] = None
    objeto_conhecimento: Optional[str] = None
    criterio_correcao: Optional[str] = None
    itens_criterio: Optional[list[ItemIn]] = None
    material_necessario: Optional[str] = None
    observacoes: Optional[str] = None
    ambiguidades: Optional[list[str]] = None
    alteracao_motivo: Optional[str] = None
    alteracao_comunicado_id: Optional[int] = None


class CronogramaCreate(BaseModel):
    chave_origem: str = Field(..., max_length=120)
    aluno_ids: list[int] = Field(..., min_length=1)
    titulo: str = ""
    subtitulo: str = ""
    turma: str = ""
    turmas: list[str] = []
    serie: Optional[str] = None
    bimestre: int = Field(..., ge=1, le=4)
    ano_letivo: int
    escola: Optional[str] = None
    aviso: str = ""
    introducao: str = ""
