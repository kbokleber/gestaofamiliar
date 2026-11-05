"""Importação e listagem de apontamentos do e-class."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, extract, or_
from sqlalchemy.orm import Session

from app.models.estudo import Apontamento, ApontamentoLido
from app.models.user import User
from app.schemas.apontamento import ApontamentoImportacao, ApontamentoItemIn
from app.services.provas import aluno_leitura, erro, exigir_adulto, familia_do, filhos_da_familia

# Ano letivo típico BR (e-class não manda bimestre nos apontamentos).
# B1: jan–abr · B2: mai–jul · B3: ago–set · B4: out–dez
_MESES_POR_BIMESTRE: dict[int, tuple[int, ...]] = {
    1: (1, 2, 3, 4),
    2: (5, 6, 7),
    3: (8, 9),
    4: (10, 11, 12),
}


def bimestre_da_data(data: Optional[date]) -> Optional[int]:
    """Infere bimestre pela data do apontamento quando o e-class não envia o campo."""
    if data is None:
        return None
    mes = data.month
    for bimestre, meses in _MESES_POR_BIMESTRE.items():
        if mes in meses:
            return bimestre
    return None


def bimestre_efetivo(item: Apontamento) -> Optional[int]:
    if item.bimestre is not None:
        return item.bimestre
    return bimestre_da_data(item.data)


def _hash(dados: dict) -> str:
    bruto = json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _slug(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto or "")
    ascii_txt = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", ascii_txt.lower()).strip("-") or "x"


def chave_apontamento(
    aluno_id: int,
    ano_letivo: int,
    bimestre: Optional[int],
    item: ApontamentoItemIn,
) -> str:
    if item.chave_origem:
        return item.chave_origem[:160]
    data_txt = item.data.isoformat() if item.data else "sem-data"
    # Mantém B0 quando o scrape não manda bimestre — evita duplicar chave ao inferir pela data.
    bim = bimestre or item.bimestre or 0
    trecho = hashlib.sha256(
        f"{item.tipo}|{item.titulo}|{item.descricao}".encode("utf-8")
    ).hexdigest()[:8]
    return (
        f"eclass-{aluno_id}-apont-B{bim}-{ano_letivo}"
        f"-{_slug(item.disciplina)}-{data_txt}-{trecho}"
    )[:160]


def _resolver_bimestre(item: ApontamentoItemIn, bimestre: Optional[int]) -> Optional[int]:
    if item.bimestre is not None:
        return item.bimestre
    if bimestre is not None:
        return bimestre
    return bimestre_da_data(item.data)


def _pacote(item: ApontamentoItemIn, bimestre: Optional[int], ano_letivo: int) -> dict:
    return {
        "data": item.data.isoformat() if item.data else None,
        "disciplina": item.disciplina,
        "professor": item.professor,
        "tipo": item.tipo,
        "titulo": item.titulo,
        "descricao": item.descricao,
        "bimestre": _resolver_bimestre(item, bimestre),
        "ano_letivo": ano_letivo,
    }


def serial_apontamento(item: Apontamento, lido: bool = False) -> dict:
    return {
        "id": item.id,
        "chave_origem": item.chave_origem,
        "aluno_id": item.aluno_id,
        "data": item.data,
        "disciplina": item.disciplina,
        "professor": item.professor,
        "tipo": item.tipo,
        "titulo": item.titulo,
        "descricao": item.descricao,
        "bimestre": bimestre_efetivo(item),
        "ano_letivo": item.ano_letivo,
        "fonte": item.fonte,
        "scraped_at": item.scraped_at,
        "lido": lido,
    }


def ids_apontamentos_lidos(db: Session, usuario: User, apontamento_ids: list[int]) -> set[int]:
    if usuario.is_child or not apontamento_ids:
        return set()
    linhas = (
        db.query(ApontamentoLido.apontamento_id)
        .filter(
            ApontamentoLido.user_id == usuario.id,
            ApontamentoLido.apontamento_id.in_(apontamento_ids),
        )
        .all()
    )
    return {linha[0] for linha in linhas}


def exigir_leitor(usuario: User) -> None:
    if usuario.is_child:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Filhos não marcam apontamentos como lidos.",
        )


def importar_apontamentos(
    db: Session,
    usuario: User,
    payload: ApontamentoImportacao,
) -> dict:
    exigir_adulto(usuario)
    family_id = familia_do(usuario)
    alunos = filhos_da_familia(db, [payload.aluno.aluno_id], family_id, ["aluno", "aluno_id"])
    aluno = alunos[0]
    scraped_at = payload.scraped_at or datetime.now(timezone.utc)

    relatorio = {"criados": 0, "atualizados": 0, "inalterados": 0}
    detalhes = []
    vistas = set()

    for indice, item in enumerate(payload.itens):
        chave = chave_apontamento(aluno.id, payload.ano_letivo, payload.bimestre, item)
        if chave in vistas:
            erro(["itens", indice, "chave_origem"], "chave_origem duplicada no payload.")
        vistas.add(chave)
        pacote = _pacote(item, payload.bimestre, payload.ano_letivo)
        assinatura = _hash(pacote)

        atual = (
            db.query(Apontamento)
            .filter(Apontamento.family_id == family_id, Apontamento.chave_origem == chave)
            .first()
        )
        if atual is None:
            db.add(Apontamento(
                family_id=family_id,
                aluno_id=aluno.id,
                chave_origem=chave,
                data=item.data,
                disciplina=item.disciplina,
                professor=item.professor,
                tipo=item.tipo,
                titulo=item.titulo or item.tipo or item.disciplina or "Apontamento",
                descricao=item.descricao,
                bimestre=pacote["bimestre"],
                ano_letivo=payload.ano_letivo,
                fonte=payload.fonte or "e-class",
                scraped_at=scraped_at,
                hash_conteudo=assinatura,
                created_by_id=usuario.id,
            ))
            relatorio["criados"] += 1
            detalhes.append({"chave_origem": chave, "acao": "criado"})
            continue

        if atual.hash_conteudo == assinatura:
            relatorio["inalterados"] += 1
            detalhes.append({"chave_origem": chave, "acao": "inalterado", "id": atual.id})
            continue

        atual.data = item.data
        atual.disciplina = item.disciplina
        atual.professor = item.professor
        atual.tipo = item.tipo
        atual.titulo = item.titulo or item.tipo or item.disciplina or atual.titulo
        atual.descricao = item.descricao
        atual.bimestre = pacote["bimestre"]
        atual.ano_letivo = payload.ano_letivo
        atual.fonte = payload.fonte or atual.fonte or "e-class"
        atual.scraped_at = scraped_at
        atual.hash_conteudo = assinatura
        relatorio["atualizados"] += 1
        detalhes.append({"chave_origem": chave, "acao": "atualizado", "id": atual.id})

    db.flush()
    return {
        "aluno_id": aluno.id,
        "ano_letivo": payload.ano_letivo,
        "bimestre": payload.bimestre,
        "apontamentos": relatorio,
        "detalhes": detalhes,
    }


def listar_apontamentos(
    db: Session,
    usuario: User,
    aluno_id: Optional[int] = None,
    bimestre: Optional[int] = None,
    ano_letivo: Optional[int] = None,
    disciplina: Optional[str] = None,
    limite: int = 200,
    lidos: bool = False,
) -> list[Apontamento]:
    family_id = familia_do(usuario)
    consulta = db.query(Apontamento).filter(Apontamento.family_id == family_id)
    escopo = aluno_leitura(usuario, aluno_id)
    if escopo is not None:
        if not usuario.is_child:
            filhos_da_familia(db, [escopo], family_id, ["aluno_id"])
        consulta = consulta.filter(Apontamento.aluno_id == escopo)
    if bimestre is not None:
        meses = _MESES_POR_BIMESTRE.get(bimestre, ())
        # Inclui linhas com bimestre gravado OU (legado) null com data no intervalo do bimestre.
        consulta = consulta.filter(
            or_(
                Apontamento.bimestre == bimestre,
                and_(
                    Apontamento.bimestre.is_(None),
                    Apontamento.data.isnot(None),
                    extract("month", Apontamento.data).in_(meses),
                ),
            )
        )
    if ano_letivo is not None:
        consulta = consulta.filter(Apontamento.ano_letivo == ano_letivo)
    if disciplina and disciplina.strip():
        consulta = consulta.filter(Apontamento.disciplina == disciplina.strip())
    # Pais: lista principal esconde lidos; lidos=1 mostra só os da pessoa.
    # Filho vê tudo, sem marca de leitura.
    if not usuario.is_child:
        lidos_subq = (
            db.query(ApontamentoLido.apontamento_id)
            .filter(ApontamentoLido.user_id == usuario.id)
        )
        if lidos:
            consulta = consulta.filter(Apontamento.id.in_(lidos_subq))
        else:
            consulta = consulta.filter(~Apontamento.id.in_(lidos_subq))
    return (
        consulta
        .order_by(Apontamento.data.desc().nulls_last(), Apontamento.id.desc())
        .limit(limite)
        .all()
    )


def carregar_apontamento(db: Session, apontamento_id: int, usuario: User) -> Apontamento:
    family_id = familia_do(usuario)
    item = db.query(Apontamento).filter(Apontamento.id == apontamento_id).first()
    if item is None or item.family_id != family_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Apontamento não encontrado.")
    if usuario.is_child and item.aluno_id != usuario.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Apontamento não encontrado.")
    return item


def marcar_apontamento_lido(db: Session, usuario: User, apontamento_id: int) -> None:
    exigir_leitor(usuario)
    carregar_apontamento(db, apontamento_id, usuario)
    existe = (
        db.query(ApontamentoLido)
        .filter(
            ApontamentoLido.user_id == usuario.id,
            ApontamentoLido.apontamento_id == apontamento_id,
        )
        .first()
    )
    if existe is None:
        db.add(ApontamentoLido(user_id=usuario.id, apontamento_id=apontamento_id))
        db.flush()


def desmarcar_apontamento_lido(db: Session, usuario: User, apontamento_id: int) -> None:
    exigir_leitor(usuario)
    carregar_apontamento(db, apontamento_id, usuario)
    (
        db.query(ApontamentoLido)
        .filter(
            ApontamentoLido.user_id == usuario.id,
            ApontamentoLido.apontamento_id == apontamento_id,
        )
        .delete(synchronize_session=False)
    )
