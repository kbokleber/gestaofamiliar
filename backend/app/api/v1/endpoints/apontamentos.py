from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_menu
from app.db.base import get_db
from app.models.user import User
from app.schemas.apontamento import ApontamentoImportacao
from app.services.apontamentos import (
    carregar_apontamento,
    desmarcar_apontamento_lido,
    ids_apontamentos_lidos,
    importar_apontamentos,
    listar_apontamentos,
    marcar_apontamento_lido,
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
    lidos: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista apontamentos do e-class.

    Para pais/adultos a lista padrão esconde os já lidos por aquela pessoa.
    Com lidos=1, mostra só os lidos. Filho vê todos, sempre com lido=false.
    """
    itens = listar_apontamentos(
        db, current_user,
        aluno_id=aluno_id,
        bimestre=bimestre,
        ano_letivo=ano_letivo,
        disciplina=disciplina,
        limite=limite,
        lidos=bool(lidos) and not current_user.is_child,
    )
    lidos_ids = ids_apontamentos_lidos(db, current_user, [item.id for item in itens])
    return [serial_apontamento(item, lido=item.id in lidos_ids) for item in itens]


@router.post("/apontamentos/{apontamento_id}/lido")
def marcar_lido(
    apontamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca o apontamento como lido para a pessoa atual. Filho recebe 403."""
    marcar_apontamento_lido(db, current_user, apontamento_id)
    db.commit()
    return {"lido": True}


@router.delete("/apontamentos/{apontamento_id}/lido")
def desmarcar_lido(
    apontamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desmarca o apontamento como lido para a pessoa atual. Filho recebe 403."""
    desmarcar_apontamento_lido(db, current_user, apontamento_id)
    db.commit()
    return {"lido": False}


@router.get("/apontamentos/{apontamento_id}")
def detalhe(
    apontamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalhe de um apontamento."""
    item = carregar_apontamento(db, apontamento_id, current_user)
    lido = bool(ids_apontamentos_lidos(db, current_user, [item.id]))
    return serial_apontamento(item, lido=lido)
