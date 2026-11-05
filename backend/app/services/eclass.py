"""Sincronização de Avaliações / Notas e Faltas / PAAEB vindos do e-class."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.prova import Avaliacao, Boletim, BoletimLinha, Cronograma
from app.models.user import User
from app.schemas.prova import (
    AvaliacaoIn,
    EclassSyncIn,
    OcorrenciaIn,
)
from app.services.provas import (
    _aplicar_avaliacao,
    _gravar_itens,
    _gravar_ocorrencias,
    _pacote_avaliacao,
    _vincular,
    aluno_leitura,
    erro,
    exigir_adulto,
    familia_do,
    filhos_da_familia,
    pode_ver_cronograma,
)


def slug_disciplina(nome: str) -> str:
    nfkd = unicodedata.normalize("NFKD", nome or "")
    ascii_txt = "".join(c for c in nfkd if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_txt.lower()).strip("-")
    return slug or "disciplina"


def hash_curto(titulo: str) -> str:
    return hashlib.sha256((titulo or "").encode("utf-8")).hexdigest()[:4]


def mapear_categoria(tipo_codigo: str) -> tuple[str, str]:
    """Retorna (categoria GF, categoria_rotulo sugerido) a partir do código e-class."""
    codigo = (tipo_codigo or "").strip().upper()
    if not codigo:
        return "OUTRO", "OUTRO"
    if codigo in ("AV1", "AV2"):
        return codigo, codigo
    if codigo.startswith("RD"):
        return "REDACAO", codigo
    if codigo.startswith("RC"):
        return "RECUPERACAO", codigo
    if codigo.startswith(("TB", "TD", "TA", "AT", "AP")):
        return "PRODUTIVIDADE", codigo
    if codigo.startswith("SI"):
        return "OUTRO", codigo
    if codigo in ("PAAEB", "CPB"):
        return "OUTRO", codigo
    return "OUTRO", codigo


def chave_item_eclass(
    aluno_id: int,
    bimestre: int,
    disciplina: str,
    tipo_codigo: str,
    data_item: Optional[date],
    titulo: str,
) -> str:
    data_txt = data_item.isoformat() if data_item else "sem-data"
    return (
        f"eclass-{aluno_id}-B{bimestre}-{slug_disciplina(disciplina)}"
        f"-{(tipo_codigo or 'X').upper()}-{data_txt}-{hash_curto(titulo)}"
    )[:160]


def chave_paaeb(aluno_id: int, codigo: Optional[str], titulo: str) -> str:
    ref = (codigo or hash_curto(titulo)).lstrip("#")
    return f"eclass-{aluno_id}-PAAEB-{ref}"[:160]


def _parse_scraped_at(valor) -> Optional[datetime]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    return None


def _data_texto(data_item: Optional[date]) -> str:
    if data_item is None:
        return ""
    return data_item.strftime("%d/%m/%Y")


def _garantir_cronograma(
    db: Session,
    usuario: User,
    family_id: int,
    aluno: User,
    payload: EclassSyncIn,
) -> Cronograma:
    if payload.cronograma_id_sugerido is not None:
        cronograma = (
            db.query(Cronograma)
            .options(selectinload(Cronograma.vinculos))
            .filter(Cronograma.id == payload.cronograma_id_sugerido)
            .first()
        )
        if cronograma is None:
            erro(["cronograma_id_sugerido"], "Cronograma sugerido não encontrado.")
        pode_ver_cronograma(cronograma, usuario)
        _vincular(db, cronograma, [aluno], usuario, substituir=False)
        return cronograma

    chave = f"eclass-{aluno.id}-{payload.ano_letivo}-B{payload.bimestre}"
    cronograma = (
        db.query(Cronograma)
        .options(selectinload(Cronograma.vinculos))
        .filter(Cronograma.family_id == family_id, Cronograma.chave_origem == chave)
        .first()
    )
    if cronograma is None:
        turma = (payload.aluno.turma_portal or "").strip()
        cronograma = Cronograma(
            family_id=family_id,
            chave_origem=chave,
            titulo=f"Notas e-class · {payload.bimestre}º bim/{payload.ano_letivo}",
            subtitulo=payload.aluno.nome or "",
            turma=turma,
            turmas=[turma] if turma else [],
            bimestre=payload.bimestre,
            ano_letivo=payload.ano_letivo,
            aviso="",
            introducao="Sincronizado automaticamente a partir do portal e-class.",
            orientacoes=[],
            hash_conteudo="",
            status="ativo",
            created_by_id=usuario.id,
        )
        db.add(cronograma)
        db.flush()
    _vincular(db, cronograma, [aluno], usuario, substituir=False)
    return cronograma


def _upsert_avaliacao(
    db: Session,
    family_id: int,
    cronograma: Cronograma,
    usuario: User,
    dados: AvaliacaoIn,
    ordem: int,
) -> str:
    from app.services.provas import _hash
    pacote = _pacote_avaliacao(dados, ordem)
    assinatura_hash = _hash(pacote)

    atual = (
        db.query(Avaliacao)
        .options(selectinload(Avaliacao.ocorrencias), selectinload(Avaliacao.itens))
        .filter(Avaliacao.family_id == family_id, Avaliacao.chave_origem == dados.chave_origem)
        .first()
    )
    if atual is None:
        avaliacao = Avaliacao(
            family_id=family_id,
            cronograma=cronograma,
            chave_origem=dados.chave_origem,
            disciplina=dados.disciplina,
            categoria=dados.categoria,
            titulo=dados.titulo,
            fonte=dados.fonte or "eclass",
            created_by_id=usuario.id,
        )
        db.add(avaliacao)
        db.flush()
        _aplicar_avaliacao(avaliacao, dados, ordem, pacote)
        _gravar_ocorrencias(db, avaliacao, dados.ocorrencias, usuario)
        _gravar_itens(db, avaliacao, dados.itens_criterio, usuario)
        return "criada"

    if atual.cronograma_id != cronograma.id and not (atual.chave_origem or "").startswith("eclass-"):
        erro(
            ["disciplinas"],
            f"chave_origem {dados.chave_origem} já pertence a avaliação do PDF; use prefixo eclass-.",
        )

    if atual.hash_conteudo == assinatura_hash:
        return "inalterada"

    if atual.cronograma_id != cronograma.id:
        atual.cronograma = cronograma
    _aplicar_avaliacao(atual, dados, ordem, pacote)
    _gravar_ocorrencias(db, atual, dados.ocorrencias, usuario)
    _gravar_itens(db, atual, dados.itens_criterio, usuario)
    return "atualizada"


def _gravar_boletim(
    db: Session,
    family_id: int,
    aluno: User,
    usuario: User,
    payload: EclassSyncIn,
) -> Optional[dict]:
    if payload.boletim is None and not payload.disciplinas:
        return None

    boletim = (
        db.query(Boletim)
        .options(selectinload(Boletim.linhas))
        .filter(
            Boletim.family_id == family_id,
            Boletim.aluno_id == aluno.id,
            Boletim.ano_letivo == payload.ano_letivo,
        )
        .first()
    )
    if boletim is None:
        boletim = Boletim(
            family_id=family_id,
            aluno_id=aluno.id,
            ano_letivo=payload.ano_letivo,
            fonte=payload.fonte or "e-class",
            created_by_id=usuario.id,
        )
        db.add(boletim)
        db.flush()
        acao = "criado"
    else:
        acao = "atualizado"

    boletim.scraped_at = _parse_scraped_at(payload.scraped_at) or datetime.now(timezone.utc)
    boletim.fonte = payload.fonte or boletim.fonte or "e-class"
    if payload.boletim is not None:
        boletim.total_faltas_por_bimestre = payload.boletim.total_faltas_por_bimestre

    por_disciplina = {linha.disciplina: linha for linha in boletim.linhas}

    if payload.boletim is not None:
        vistas = set()
        for linha_in in payload.boletim.linhas:
            disciplina = (linha_in.disciplina or "").strip()
            if not disciplina:
                continue
            vistas.add(disciplina)
            linha = por_disciplina.get(disciplina)
            if linha is None:
                linha = BoletimLinha(
                    family_id=family_id,
                    boletim=boletim,
                    disciplina=disciplina,
                    created_by_id=usuario.id,
                )
                db.add(linha)
                por_disciplina[disciplina] = linha
            for campo in (
                "b1_nota", "b1_faltas", "b2_nota", "b2_faltas",
                "b3_nota", "b3_faltas", "b4_nota", "b4_faltas",
            ):
                setattr(linha, campo, getattr(linha_in, campo))

    for disc in payload.disciplinas:
        disciplina = (disc.disciplina or "").strip()
        if not disciplina:
            continue
        linha = por_disciplina.get(disciplina)
        if linha is None:
            linha = BoletimLinha(
                family_id=family_id,
                boletim=boletim,
                disciplina=disciplina,
                created_by_id=usuario.id,
            )
            db.add(linha)
            por_disciplina[disciplina] = linha
        if disc.professor:
            linha.professor = disc.professor
        if disc.nota_parcial is not None:
            linha.nota_parcial = disc.nota_parcial
            linha.bimestre_nota_parcial = payload.bimestre

    db.flush()
    return {"id": boletim.id, "acao": acao, "linhas": len(por_disciplina)}


def sincronizar_eclass(db: Session, usuario: User, payload: EclassSyncIn) -> dict:
    exigir_adulto(usuario)
    family_id = familia_do(usuario)
    alunos = filhos_da_familia(db, [payload.aluno.aluno_id], family_id, ["aluno", "aluno_id"])
    aluno = alunos[0]
    cronograma = _garantir_cronograma(db, usuario, family_id, aluno, payload)

    relatorio = {"criadas": 0, "atualizadas": 0, "inalteradas": 0}
    detalhes = []
    ordem = 0
    chaves_vistas = set()

    for disc in payload.disciplinas:
        disciplina = (disc.disciplina or "").strip()
        if not disciplina:
            continue
        for item in disc.itens:
            ordem += 1
            tipo = (item.tipo_codigo or "").strip().upper()
            titulo = (item.atividade or "").strip()
            if not tipo or not titulo:
                continue
            chave = (item.chave_origem or "").strip() or chave_item_eclass(
                aluno.id, payload.bimestre, disciplina, tipo, item.data, titulo,
            )
            if chave in chaves_vistas:
                erro(["disciplinas"], f"chave_origem duplicada no payload: {chave}")
            chaves_vistas.add(chave)

            categoria, rotulo = mapear_categoria(tipo)
            ocorrencias = []
            if item.data is not None:
                ocorrencias = [OcorrenciaIn(data_inicio=item.data, data_fim=item.data, turma=None)]

            composicao = None
            if item.detalhe and item.detalhe.composicao:
                composicao = item.detalhe.composicao

            dados = AvaliacaoIn(
                chave_origem=chave,
                disciplina=disciplina,
                categoria=categoria,  # type: ignore[arg-type]
                categoria_rotulo=rotulo,
                tipo_codigo_eclass=tipo,
                sequencia=ordem,
                titulo=titulo[:200],
                data_texto=_data_texto(item.data),
                ocorrencias=ocorrencias,
                valor=item.valor,
                nota_alcancada=item.alcancado,
                professor=disc.professor,
                composicao=composicao,
                fonte="eclass",
                objeto_conhecimento=(item.detalhe.descricao if item.detalhe and item.detalhe.descricao else ""),
                criterio_correcao="",
                observacoes=None,
                ambiguidades=[],
            )
            acao = _upsert_avaliacao(db, family_id, cronograma, usuario, dados, ordem)
            relatorio[{"criada": "criadas", "atualizada": "atualizadas", "inalterada": "inalteradas"}[acao]] += 1
            detalhes.append({"chave_origem": chave, "acao": acao})

    for prova in payload.provas_agenda:
        ordem += 1
        titulo = (prova.titulo or "").strip()
        if not titulo:
            continue
        chave = chave_paaeb(aluno.id, prova.codigo, titulo)
        if chave in chaves_vistas:
            continue
        chaves_vistas.add(chave)
        ocorrencias = []
        if prova.prazo is not None:
            ocorrencias = [OcorrenciaIn(data_inicio=prova.prazo, data_fim=prova.prazo, turma=None)]
        observacoes_partes = []
        if prova.modalidade:
            observacoes_partes.append(f"Modalidade: {prova.modalidade}")
        if prova.codigo:
            observacoes_partes.append(f"Código: #{prova.codigo.lstrip('#')}")
        if prova.questoes is not None:
            observacoes_partes.append(f"Questões: {prova.questoes}")
        if prova.tipo_badge:
            observacoes_partes.append(f"Badge: {prova.tipo_badge}")
        dados = AvaliacaoIn(
            chave_origem=chave,
            disciplina="PAAEB",
            categoria="OUTRO",
            categoria_rotulo="PAAEB",
            tipo_codigo_eclass="PAAEB",
            sequencia=ordem,
            titulo=titulo[:200],
            data_texto=_data_texto(prova.prazo),
            ocorrencias=ocorrencias,
            fonte="eclass",
            observacoes="; ".join(observacoes_partes) or None,
        )
        acao = _upsert_avaliacao(db, family_id, cronograma, usuario, dados, ordem)
        relatorio[{"criada": "criadas", "atualizada": "atualizadas", "inalterada": "inalteradas"}[acao]] += 1
        detalhes.append({"chave_origem": chave, "acao": acao, "tipo": "paaeb"})

    boletim_info = _gravar_boletim(db, family_id, aluno, usuario, payload)
    db.flush()
    return {
        "cronograma_id": cronograma.id,
        "aluno_id": aluno.id,
        "bimestre": payload.bimestre,
        "ano_letivo": payload.ano_letivo,
        "avaliacoes": relatorio,
        "detalhes": detalhes,
        "boletim": boletim_info,
    }


def serial_boletim(boletim: Boletim) -> dict:
    return {
        "id": boletim.id,
        "aluno_id": boletim.aluno_id,
        "ano_letivo": boletim.ano_letivo,
        "scraped_at": boletim.scraped_at,
        "fonte": boletim.fonte,
        "total_faltas_por_bimestre": boletim.total_faltas_por_bimestre,
        "linhas": [
            {
                "id": linha.id,
                "disciplina": linha.disciplina,
                "professor": linha.professor,
                "b1_nota": float(linha.b1_nota) if linha.b1_nota is not None else None,
                "b1_faltas": linha.b1_faltas,
                "b2_nota": float(linha.b2_nota) if linha.b2_nota is not None else None,
                "b2_faltas": linha.b2_faltas,
                "b3_nota": float(linha.b3_nota) if linha.b3_nota is not None else None,
                "b3_faltas": linha.b3_faltas,
                "b4_nota": float(linha.b4_nota) if linha.b4_nota is not None else None,
                "b4_faltas": linha.b4_faltas,
                "nota_parcial": float(linha.nota_parcial) if linha.nota_parcial is not None else None,
                "bimestre_nota_parcial": linha.bimestre_nota_parcial,
            }
            for linha in sorted(boletim.linhas, key=lambda item: item.disciplina.lower())
        ],
    }


def obter_boletim(
    db: Session,
    usuario: User,
    aluno_id: int,
    ano_letivo: int,
) -> Boletim:
    family_id = familia_do(usuario)
    # Filho: sempre o próprio id (ignora pedido do irmão).
    alvo = aluno_leitura(usuario, aluno_id)
    if alvo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Boletim não encontrado.")
    if not usuario.is_child:
        filhos_da_familia(db, [alvo], family_id, ["aluno_id"])

    boletim = (
        db.query(Boletim)
        .options(selectinload(Boletim.linhas))
        .filter(
            Boletim.family_id == family_id,
            Boletim.aluno_id == alvo,
            Boletim.ano_letivo == ano_letivo,
        )
        .first()
    )
    if boletim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Boletim não encontrado.")
    return boletim
