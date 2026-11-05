from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_menu
from app.db.base import get_db
from app.models.user import User
from app.schemas.apontamento import ApontamentoImportacao
from app.services.apontamentos import (
    carregar_apontamento,
    importar_apontamentos,
    listar_apontamentos,
    serial_apontamento,
)
from app.services.provas import exigir_adulto

router = APIRouter(dependencies=[Depends(require_menu("estudos"))])


@router.post("/apontamentos/importar")
def importar(
    payload: ApontamentoImportacao,
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Importa apontamentos do e-class com dedup por chave_origem."""
    exigir_adulto(current_user)
    if dry_run:
        relatorio = importar_apontamentos(db, current_user, payload)
        db.rollback()
        return {"dry_run": True, **relatorio}
    relatorio = importar_apontamentos(db, current_user, payload)
    db.commit()
    return {"dry_run": False, **relatorio}


@router.get("/apontamentos")
def listar(
    aluno_id: Optional[int] = None,
    bimestre: Optional[int] = None,
    ano_letivo: Optional[int] = None,
    disciplina: Optional[str] = None,
    limite: int = Query(200, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista apontamentos sincronizados do e-class."""
    itens = listar_apontamentos(
        db, current_user,
        aluno_id=aluno_id,
        bimestre=bimestre,
        ano_letivo=ano_letivo,
        disciplina=disciplina,
        limite=limite,
    )
    return [serial_apontamento(item) for item in itens]


@router.get("/apontamentos/{apontamento_id}")
def detalhe(
    apontamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalhe de um apontamento."""
    return serial_apontamento(carregar_apontamento(db, apontamento_id, current_user))
