from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

TipoEstudo = Literal["atividade", "comunicado"]


class AtividadeBase(BaseModel):
    titulo: str = Field(..., max_length=200, examples=["LIÇÃO DE CASA"])
    descricao: str = ""
    disciplina: Optional[str] = Field(None, max_length=120, examples=["Língua Portuguesa"])
    professor: str = Field("", max_length=150)
    data: date
    prazo_entrega: Optional[datetime] = None
    tipo: TipoEstudo = "atividade"
    autor: Optional[str] = Field(None, max_length=150, examples=["Secretaria CAdG"])
    numero: Optional[str] = Field(None, max_length=40, examples=["2626"])


class AtividadeCreate(AtividadeBase):
    aluno_id: Optional[int] = None
    aluno_ids: Optional[list[int]] = None


class AtividadeUpdate(AtividadeBase):
    aluno_id: int


class Anexo(BaseModel):
    name: str
    type: str
    size: int


class Atividade(AtividadeBase):
    id: int
    aluno_id: int
    family_id: int
    aluno_nome: str
    status: Optional[str] = None
    lido: bool = False
    criado_pelo_app: bool = False
    anexos: list[Anexo] = []
    concluida_em: Optional[datetime] = None
    created_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
