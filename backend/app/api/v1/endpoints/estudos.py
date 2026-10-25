from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin, get_current_user
from app.db.base import get_db
from app.models.estudo import Atividade
from app.models.user import User
from app.schemas.estudo import Atividade as AtividadeSchema
from app.schemas.estudo import AtividadeCreate, AtividadeUpdate

router = APIRouter()


def _aluno_nome(user: User) -> str:
    nome = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return nome or user.username


def _to_schema(atividade: Atividade) -> AtividadeSchema:
    return AtividadeSchema(
        id=atividade.id,
        aluno_id=atividade.aluno_id,
        family_id=atividade.family_id,
        aluno_nome=_aluno_nome(atividade.aluno) if atividade.aluno else "",
        titulo=atividade.titulo,
        descricao=atividade.descricao or "",
        disciplina=atividade.disciplina or "",
        professor=atividade.professor or "",
        data=atividade.data,
        prazo_entrega=atividade.prazo_entrega,
        status=atividade.status or "pendente",
        concluida_em=atividade.concluida_em,
        created_by_id=atividade.created_by_id,
        created_at=atividade.created_at,
    )


def _filho_ativo(db: Session, aluno_id: int) -> User:
    aluno = db.query(User).filter(User.id == aluno_id).first()
    if aluno is None or not aluno.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filho não encontrado ou inativo.",
        )
    if aluno.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A atividade precisa ser de um filho, não de um administrador.",
        )
    if not aluno.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O filho não tem família associada.",
        )
    return aluno


def _get_or_404(db: Session, atividade_id: int) -> Atividade:
    atividade = (
        db.query(Atividade)
        .options(joinedload(Atividade.aluno))
        .filter(Atividade.id == atividade_id)
        .first()
    )
    if atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")
    return atividade


@router.get("/atividades", response_model=List[AtividadeSchema])
async def list_atividades(
    aluno_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista atividades. Aceita Bearer ou header X-API-Token.

    O filho recebe somente as próprias. O administrador recebe todas
    e pode filtrar com o parâmetro aluno_id.
    """
    query = db.query(Atividade).options(joinedload(Atividade.aluno))
    if current_user.is_superuser:
        if aluno_id is not None:
            query = query.filter(Atividade.aluno_id == aluno_id)
    else:
        query = query.filter(Atividade.aluno_id == current_user.id)
    atividades = query.order_by(Atividade.prazo_entrega.asc(), Atividade.id.asc()).all()
    return [_to_schema(item) for item in atividades]


@router.get("/atividades/{atividade_id}", response_model=AtividadeSchema)
async def read_atividade(
    atividade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalhe de uma atividade. O filho só abre a própria."""
    atividade = _get_or_404(db, atividade_id)
    if not current_user.is_superuser and atividade.aluno_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")
    return _to_schema(atividade)


@router.post("/atividades", response_model=AtividadeSchema, status_code=status.HTTP_201_CREATED)
async def create_atividade(
    payload: AtividadeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Cria uma atividade para um filho. Somente administrador, via Bearer ou X-API-Token."""
    if not payload.titulo.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Título é obrigatório.")
    aluno = _filho_ativo(db, payload.aluno_id)
    atividade = Atividade(
        aluno_id=aluno.id,
        family_id=aluno.family_id,
        titulo=payload.titulo.strip(),
        descricao=payload.descricao or "",
        disciplina=payload.disciplina or "",
        professor=payload.professor or "",
        data=payload.data,
        prazo_entrega=payload.prazo_entrega,
        status="pendente",
        created_by_id=current_user.id,
    )
    db.add(atividade)
    db.commit()
    db.refresh(atividade)
    atividade.aluno = aluno
    return _to_schema(atividade)


@router.put("/atividades/{atividade_id}", response_model=AtividadeSchema)
async def update_atividade(
    atividade_id: int,
    payload: AtividadeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Altera uma atividade. Somente administrador."""
    if not payload.titulo.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Título é obrigatório.")
    atividade = _get_or_404(db, atividade_id)
    aluno = _filho_ativo(db, payload.aluno_id)
    atividade.aluno_id = aluno.id
    atividade.family_id = aluno.family_id
    atividade.titulo = payload.titulo.strip()
    atividade.descricao = payload.descricao or ""
    atividade.disciplina = payload.disciplina or ""
    atividade.professor = payload.professor or ""
    atividade.data = payload.data
    atividade.prazo_entrega = payload.prazo_entrega
    atividade.aluno = aluno
    db.commit()
    db.refresh(atividade)
    return _to_schema(atividade)


@router.post("/atividades/{atividade_id}/concluir", response_model=AtividadeSchema)
async def concluir_atividade(
    atividade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """O filho marca a própria atividade como concluída. Aceita Bearer ou X-API-Token."""
    atividade = _get_or_404(db, atividade_id)
    if not current_user.is_superuser and atividade.aluno_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")
    if current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Só o filho pode marcar a atividade como concluída.",
        )
    if atividade.status == "concluida":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta atividade já está concluída.")
    atividade.status = "concluida"
    atividade.concluida_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(atividade)
    return _to_schema(atividade)


@router.post("/atividades/{atividade_id}/reabrir", response_model=AtividadeSchema)
async def reabrir_atividade(
    atividade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """O administrador devolve a atividade para pendente. Aceita Bearer ou X-API-Token."""
    atividade = _get_or_404(db, atividade_id)
    if atividade.status != "concluida":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Esta atividade já está pendente.")
    atividade.status = "pendente"
    atividade.concluida_em = None
    db.commit()
    db.refresh(atividade)
    return _to_schema(atividade)


@router.delete("/atividades/{atividade_id}")
async def delete_atividade(
    atividade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Exclui uma atividade. Somente administrador."""
    atividade = _get_or_404(db, atividade_id)
    db.delete(atividade)
    db.commit()
    return {"message": "Atividade excluída com sucesso"}
