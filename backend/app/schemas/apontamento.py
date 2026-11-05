from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


def _ponta(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    return valor.strip()


class ApontamentoAlunoIn(BaseModel):
    aluno_id: int
    profile: Optional[str] = None
    turma_portal: Optional[str] = None
    nome: Optional[str] = None


class ApontamentoItemIn(BaseModel):
    chave_origem: Optional[str] = Field(None, max_length=160)
    data: Optional[date] = None
    disciplina: str = Field("", max_length=120)
    professor: str = Field("", max_length=150)
    tipo: str = Field("", max_length=80)
    titulo: str = Field("", max_length=200)
    descricao: str = ""
    bimestre: Optional[int] = Field(None, ge=1, le=4)

    @model_validator(mode="after")
    def limpar(self):
        self.chave_origem = _ponta(self.chave_origem) or None
        self.disciplina = _ponta(self.disciplina) or ""
        self.professor = _ponta(self.professor) or ""
        self.tipo = _ponta(self.tipo) or ""
        self.titulo = _ponta(self.titulo) or ""
        self.descricao = _ponta(self.descricao) or ""
        return self


class ApontamentoImportacao(BaseModel):
    fonte: str = "e-class"
    scraped_at: Optional[datetime] = None
    aluno: ApontamentoAlunoIn
    bimestre: Optional[int] = Field(None, ge=1, le=4)
    ano_letivo: int
    itens: list[ApontamentoItemIn] = []
