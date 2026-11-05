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


class ComposicaoItemIn(BaseModel):
    realizado_em: Optional[date] = None
    avaliacao: Optional[str] = Field(None, max_length=40)
    nota_final: Optional[float] = None

    @model_validator(mode="after")
    def limpar(self):
        self.avaliacao = _ponta(self.avaliacao) or None
        return self


class AvaliacaoIn(BaseModel):
    chave_origem: str = Field(..., max_length=160)
    disciplina: str = Field(..., max_length=120)
    categoria: CategoriaAvaliacao
    categoria_rotulo: Optional[str] = Field(None, max_length=40)
    tipo_codigo_eclass: Optional[str] = Field(None, max_length=20)
    sequencia: int = Field(1, ge=1)
    titulo: str = Field(..., max_length=200)
    data_texto: str = Field("", max_length=120)
    ocorrencias: list[OcorrenciaIn] = []
    valor: Optional[float] = None
    valor_texto: Optional[str] = Field(None, max_length=20)
    nota_alcancada: Optional[float] = None
    professor: Optional[str] = Field(None, max_length=150)
    composicao: Optional[list[ComposicaoItemIn]] = None
    fonte: Optional[str] = Field(None, max_length=20)
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
        self.tipo_codigo_eclass = (_ponta(self.tipo_codigo_eclass) or None)
        if self.tipo_codigo_eclass:
            self.tipo_codigo_eclass = self.tipo_codigo_eclass.upper()
        self.titulo = _ponta(self.titulo) or ""
        self.data_texto = _ponta(self.data_texto) or ""
        self.valor_texto = _ponta(self.valor_texto) or None
        self.professor = _ponta(self.professor) or None
        self.fonte = (_ponta(self.fonte) or None)
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
    tipo_codigo_eclass: Optional[str] = None
    titulo: Optional[str] = None
    data_texto: Optional[str] = None
    ocorrencias: Optional[list[OcorrenciaIn]] = None
    valor: Optional[float] = None
    valor_texto: Optional[str] = None
    nota_alcancada: Optional[float] = None
    professor: Optional[str] = None
    composicao: Optional[list[ComposicaoItemIn]] = None
    fonte: Optional[str] = None
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


class EclassAlunoIn(BaseModel):
    profile: Optional[str] = None
    aluno_id: int
    turma_portal: Optional[str] = None
    nome: Optional[str] = None


class EclassDetalheIn(BaseModel):
    codigo: Optional[str] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    realizado_em: Optional[date] = None
    nota_final: Optional[float] = None
    composicao: list[ComposicaoItemIn] = []


class EclassItemIn(BaseModel):
    data: Optional[date] = None
    tipo_codigo: str = Field(..., max_length=20)
    atividade: str = Field(..., max_length=200)
    alcancado: Optional[float] = None
    valor: Optional[float] = None
    chave_origem: Optional[str] = Field(None, max_length=160)
    detalhe: Optional[EclassDetalheIn] = None


class EclassDisciplinaIn(BaseModel):
    disciplina: str = Field(..., max_length=120)
    professor: Optional[str] = Field(None, max_length=150)
    nota_parcial: Optional[float] = None
    itens: list[EclassItemIn] = []


class EclassBoletimLinhaIn(BaseModel):
    disciplina: str = Field(..., max_length=120)
    b1_nota: Optional[float] = None
    b1_faltas: Optional[int] = None
    b2_nota: Optional[float] = None
    b2_faltas: Optional[int] = None
    b3_nota: Optional[float] = None
    b3_faltas: Optional[int] = None
    b4_nota: Optional[float] = None
    b4_faltas: Optional[int] = None


class EclassBoletimIn(BaseModel):
    colunas: list[str] = []
    linhas: list[EclassBoletimLinhaIn] = []
    total_faltas_por_bimestre: Optional[dict] = None


class EclassProvaAgendaIn(BaseModel):
    titulo: str = Field(..., max_length=200)
    tipo_badge: Optional[str] = None
    prazo: Optional[date] = None
    modalidade: Optional[str] = None
    codigo: Optional[str] = Field(None, max_length=40)
    questoes: Optional[int] = None


class EclassSyncIn(BaseModel):
    fonte: str = "e-class"
    scraped_at: Optional[datetime] = None
    aluno: EclassAlunoIn
    bimestre: int = Field(..., ge=1, le=4)
    ano_letivo: int
    cronograma_id_sugerido: Optional[int] = None
    disciplinas: list[EclassDisciplinaIn] = []
    boletim: Optional[EclassBoletimIn] = None
    provas_agenda: list[EclassProvaAgendaIn] = []
