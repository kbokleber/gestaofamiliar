"""Importação e listagem de apontamentos do e-class."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.estudo import Apontamento
from app.models.user import User
from app.schemas.apontamento import ApontamentoImportacao, ApontamentoItemIn
from app.services.provas import aluno_leitura, erro, exigir_adulto, familia_do, filhos_da_familia


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
    bim = bimestre or item.bimestre or 0
    trecho = hashlib.sha256(
        f"{item.tipo}|{item.titulo}|{item.descricao}".encode("utf-8")
    ).hexdigest()[:8]
    return (
        f"eclass-{aluno_id}-apont-B{bim}-{ano_letivo}"
        f"-{_slug(item.disciplina)}-{data_txt}-{trecho}"
    )[:160]


def _pacote(item: ApontamentoItemIn, bimestre: Optional[int], ano_letivo: int) -> dict:
    return {
        "data": item.data.isoformat() if item.data else None,
        "disciplina": item.disciplina,
        "professor": item.professor,
        "tipo": item.tipo,
        "titulo": item.titulo,
        "descricao": item.descricao,
        "bimestre": item.bimestre if item.bimestre is not None else bimestre,
        "ano_letivo": ano_letivo,
    }


def serial_apontamento(item: Apontamento) -> dict:
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
        "bimestre": item.bimestre,
        "ano_letivo": item.ano_letivo,
        "fonte": item.fonte,
        "scraped_at": item.scraped_at,
    }


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
) -> list[Apontamento]:
    family_id = familia_do(usuario)
    consulta = db.query(Apontamento).filter(Apontamento.family_id == family_id)
    escopo = aluno_leitura(usuario, aluno_id)
    if escopo is not None:
        if not usuario.is_child:
            filhos_da_familia(db, [escopo], family_id, ["aluno_id"])
        consulta = consulta.filter(Apontamento.aluno_id == escopo)
    if bimestre is not None:
        consulta = consulta.filter(Apontamento.bimestre == bimestre)
    if ano_letivo is not None:
        consulta = consulta.filter(Apontamento.ano_letivo == ano_letivo)
    if disciplina and disciplina.strip():
        consulta = consulta.filter(Apontamento.disciplina == disciplina.strip())
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
