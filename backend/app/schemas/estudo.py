from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class AtividadeBase(BaseModel):
    titulo: str = Field(..., max_length=200, examples=["LIÇÃO DE CASA"])
    descricao: str = ""
    disciplina: str = Field("", max_length=120, examples=["Língua Portuguesa"])
    professor: str = Field("", max_length=150)
    data: date
    prazo_entrega: datetime


class AtividadeCreate(AtividadeBase):
    aluno_id: int


class AtividadeUpdate(AtividadeBase):
    aluno_id: int


class Atividade(AtividadeBase):
    id: int
    aluno_id: int
    family_id: int
    aluno_nome: str
    status: str
    concluida_em: Optional[datetime] = None
    created_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
