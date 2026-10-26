from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_menu
from app.core.config import settings
from app.db.base import get_db
from app.models.estudo import Atividade
from app.models.prova import Avaliacao, AvaliacaoOcorrencia, Cronograma, CronogramaAluno, EventoEscolar
from app.models.user import User
from app.schemas.prova import AvaliacaoCreate, AvaliacaoPatch, AvaliacaoPut, CronogramaCreate, Importacao
from app.services.provas import (
    ORDEM_CATEGORIA,
    CORES_CATEGORIA,
    CORES_EVENTO,
    _aplicar_avaliacao,
    _gravar_itens,
    _gravar_ocorrencias,
    _pacote_avaliacao,
    _vincular,
    alunos_do,
    aplicar_patch,
    carregar_avaliacao,
    exigir_adulto,
    familia_do,
    filhos_da_familia,
    hoje_local,
    importar_cronograma,
    pdf_do,
    pode_ver_cronograma,
    query_visivel,
    serial_avaliacao,
    titulo_evento,
)

router = APIRouter(dependencies=[Depends(require_menu("estudos"))])


def _cronograma_ou_404(db: Session, cronograma_id: int, usuario: User) -> Cronograma:
    cronograma = (
        db.query(Cronograma)
        .options(
            selectinload(Cronograma.vinculos).selectinload(CronogramaAluno.aluno),
            selectinload(Cronograma.eventos),
        )
        .filter(Cronograma.id == cronograma_id)
        .first()
    )
    if cronograma is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cronograma não encontrado.")
    pode_ver_cronograma(cronograma, usuario)
    return cronograma


def _opcoes_avaliacao():
    return (
        selectinload(Avaliacao.ocorrencias),
        selectinload(Avaliacao.itens),
        selectinload(Avaliacao.cronograma).selectinload(Cronograma.vinculos).selectinload(CronogramaAluno.aluno),
    )


@router.post("/cronogramas/importar")
def importar(
    payload: Importacao,
    dry_run: bool = Query(False),
    modo_remocao: str = Query("manter"),
    substituir_alunos: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Importa um PDF já extraído. Reenviar o mesmo JSON não duplica as avaliações."""
    exigir_adulto(current_user)
    if modo_remocao not in {"manter", "remover"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="modo_remocao deve ser manter ou remover.")
    try:
        relatorio = importar_cronograma(db, current_user, payload, modo_remocao, substituir_alunos)
        if dry_run:
            db.rollback()
        else:
            db.commit()
        return relatorio
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.get("/cronogramas")
def listar_cronogramas(
    aluno_id: Optional[int] = None,
    ano_letivo: Optional[int] = None,
    bimestre: Optional[int] = None,
    turma: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista os cronogramas da família. O filho só vê os que estão vinculados a ele."""
    consulta = query_visivel(db, current_user, None if current_user.is_child else aluno_id)
    consulta = consulta.options(selectinload(Cronograma.vinculos).selectinload(CronogramaAluno.aluno))
    if ano_letivo is not None:
        consulta = consulta.filter(Cronograma.ano_letivo == ano_letivo)
    if bimestre is not None:
        consulta = consulta.filter(Cronograma.bimestre == bimestre)
    if turma:
        consulta = consulta.filter(Cronograma.turma == turma)
    return [
        {
            "id": item.id,
            "chave_origem": item.chave_origem,
            "titulo": item.titulo,
            "subtitulo": item.subtitulo,
            "turma": item.turma,
            "bimestre": item.bimestre,
            "ano_letivo": item.ano_letivo,
            "alunos": alunos_do(item),
        }
        for item in consulta.order_by(Cronograma.ano_letivo.desc(), Cronograma.bimestre.desc(), Cronograma.id.desc())
    ]


@router.post("/cronogramas", status_code=status.HTTP_201_CREATED)
def criar_cronograma(
    payload: CronogramaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria um cronograma vazio, para completar as avaliações depois."""
    exigir_adulto(current_user)
    family_id = familia_do(current_user)
    alunos = filhos_da_familia(db, payload.aluno_ids, family_id, ["aluno_ids"])
    cronograma = Cronograma(
        family_id=family_id,
        chave_origem=payload.chave_origem.strip(),
        titulo=payload.titulo.strip(),
        subtitulo=payload.subtitulo.strip(),
        turma=payload.turma.strip(),
        turmas=[item.strip() for item in payload.turmas if item.strip()],
        serie=(payload.serie or "").strip() or None,
        bimestre=payload.bimestre,
        ano_letivo=payload.ano_letivo,
        escola=(payload.escola or "").strip() or None,
        aviso=payload.aviso.strip(),
        introducao=payload.introducao.strip(),
        orientacoes=[],
        created_by_id=current_user.id,
        status="ativo",
        hash_conteudo="",
    )
    db.add(cronograma)
    db.flush()
    _vincular(db, cronograma, alunos, current_user, substituir=True)
    db.commit()
    db.refresh(cronograma)
    return {"id": cronograma.id, "chave_origem": cronograma.chave_origem}


@router.get("/cronogramas/{cronograma_id}")
def detalhe_cronograma(
    cronograma_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalhe do documento, com alunos, eventos escolares e o vínculo do PDF."""
    cronograma = _cronograma_ou_404(db, cronograma_id, current_user)
    total = db.query(Avaliacao).filter(Avaliacao.cronograma_id == cronograma.id).count()
    return {
        "id": cronograma.id,
        "chave_origem": cronograma.chave_origem,
        "titulo": cronograma.titulo,
        "subtitulo": cronograma.subtitulo,
        "turma": cronograma.turma,
        "turmas": cronograma.turmas or [],
        "serie": cronograma.serie,
        "bimestre": cronograma.bimestre,
        "ano_letivo": cronograma.ano_letivo,
        "escola": cronograma.escola,
        "data_publicacao": cronograma.data_publicacao,
        "autor": cronograma.autor,
        "aviso": cronograma.aviso,
        "introducao": cronograma.introducao,
        "orientacoes": cronograma.orientacoes or [],
        "alunos": alunos_do(cronograma),
        "eventos_escolares": [
            {
                "id": evento.id,
                "tipo": evento.tipo,
                "legenda": evento.legenda,
                "data_inicio": evento.data_inicio,
                "data_fim": evento.data_fim,
            }
            for evento in cronograma.eventos
        ],
        "total_avaliacoes": total,
        "pdf": pdf_do(cronograma),
    }


@router.get("/cronogramas/{cronograma_id}/avaliacoes")
def avaliacoes_do_cronograma(
    cronograma_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Avaliações na mesma ordem do PDF."""
    cronograma = _cronograma_ou_404(db, cronograma_id, current_user)
    itens = (
        db.query(Avaliacao)
        .options(*_opcoes_avaliacao())
        .filter(Avaliacao.cronograma_id == cronograma.id)
        .order_by(Avaliacao.ordem.asc(), Avaliacao.id.asc())
        .all()
    )
    return [serial_avaliacao(item, current_user) for item in itens]


def _arquivo_pdf(db: Session, cronograma: Cronograma):
    if cronograma.comunicado_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Este cronograma não tem PDF de origem.")
    atividade = db.query(Atividade).filter(Atividade.id == cronograma.comunicado_id).first()
    if atividade is None or atividade.family_id != cronograma.family_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comunicado de origem não encontrado.")
    from app.api.v1.endpoints.estudos import PASTA_ANEXOS, _garantir_arquivos
    resumo = _garantir_arquivos(atividade, db)
    idx = None
    if cronograma.anexo_nome:
        for posicao, item in enumerate(resumo):
            if item.get("name") == cronograma.anexo_nome:
                idx = posicao
                break
    if idx is None and cronograma.anexo_idx is not None and 0 <= cronograma.anexo_idx < len(resumo):
        idx = cronograma.anexo_idx
    if idx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Anexo do PDF não encontrado neste comunicado.",
        )
    item = resumo[idx]
    caminho = PASTA_ANEXOS / str(item["arquivo"])
    if not caminho.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conteúdo do anexo não encontrado.")
    return caminho, item, idx


@router.get("/cronogramas/{cronograma_id}/pdf/link")
def link_pdf(
    cronograma_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Endereço do PDF original, no mesmo formato do anexo de comunicado."""
    cronograma = _cronograma_ou_404(db, cronograma_id, current_user)
    _caminho, item, idx = _arquivo_pdf(db, cronograma)
    db.commit()
    from app.api.v1.endpoints.estudos import LINK_SEGUNDOS, _assinar
    import time
    exp = int(time.time()) + LINK_SEGUNDOS
    sig = _assinar(cronograma.comunicado_id, idx, exp)
    return {
        "url": (
            f"{settings.API_V1_STR}/estudos/atividades/{cronograma.comunicado_id}"
            f"/anexos/{idx}/download?inline=1&exp={exp}&sig={sig}"
        ),
        "nome": item.get("name") or cronograma.anexo_nome,
    }


@router.get("/cronogramas/{cronograma_id}/pdf")
def baixar_pdf(
    cronograma_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Entrega o PDF original para o navegador abrir."""
    cronograma = _cronograma_ou_404(db, cronograma_id, current_user)
    caminho, item, _idx = _arquivo_pdf(db, cronograma)
    db.commit()
    return FileResponse(
        caminho,
        media_type=str(item.get("type") or "application/pdf"),
        filename=str(item.get("name") or "cronograma.pdf"),
        content_disposition_type="inline",
    )


@router.delete("/cronogramas/{cronograma_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_cronograma(
    cronograma_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apaga o cronograma e as avaliações que vieram dele."""
    exigir_adulto(current_user)
    cronograma = _cronograma_ou_404(db, cronograma_id, current_user)
    db.delete(cronograma)
    db.commit()


@router.get("/avaliacoes/proximas")
def proximas(
    aluno_id: Optional[int] = None,
    dias: int = Query(7, ge=1, le=60),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Ocorrências de hoje até os próximos dias, no horário de Brasília."""
    inicio = hoje_local()
    return _calendario_eventos(
        db, current_user, inicio, inicio + timedelta(days=dias),
        None if current_user.is_child else aluno_id,
        None, None, False,
    )


@router.get("/avaliacoes")
def listar_avaliacoes(
    aluno_id: Optional[int] = None,
    de: Optional[date] = None,
    ate: Optional[date] = None,
    disciplina: Optional[list[str]] = Query(None),
    categoria: Optional[list[str]] = Query(None),
    cronograma_id: Optional[int] = None,
    bimestre: Optional[int] = None,
    ano_letivo: Optional[int] = None,
    incluir_sem_data: bool = False,
    q: Optional[str] = None,
    limite: int = Query(200, ge=1, le=200),
    antes_de: Optional[date] = None,
    antes_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista avaliações. O intervalo de e até inclui quem tem qualquer dia dentro dele."""
    consulta = (
        db.query(Avaliacao)
        .join(Cronograma)
        .options(*_opcoes_avaliacao())
        .filter(Cronograma.family_id == familia_do(current_user), Cronograma.status == "ativo")
    )
    if current_user.is_child:
        consulta = consulta.filter(Cronograma.vinculos.any(CronogramaAluno.aluno_id == current_user.id))
    elif aluno_id is not None:
        consulta = consulta.filter(Cronograma.vinculos.any(CronogramaAluno.aluno_id == aluno_id))
    if cronograma_id is not None:
        consulta = consulta.filter(Avaliacao.cronograma_id == cronograma_id)
    if bimestre is not None:
        consulta = consulta.filter(Cronograma.bimestre == bimestre)
    if ano_letivo is not None:
        consulta = consulta.filter(Cronograma.ano_letivo == ano_letivo)
    if disciplina:
        consulta = consulta.filter(Avaliacao.disciplina.in_(disciplina))
    if categoria:
        consulta = consulta.filter(Avaliacao.categoria.in_(categoria))
    if de is not None or ate is not None:
        consulta = consulta.join(AvaliacaoOcorrencia)
        if de is not None:
            consulta = consulta.filter(AvaliacaoOcorrencia.data_fim >= de)
        if ate is not None:
            consulta = consulta.filter(AvaliacaoOcorrencia.data_inicio <= ate)
    elif not incluir_sem_data:
        consulta = consulta.filter(Avaliacao.sem_data.is_(False))
    if q and q.strip():
        like = f"%{q.strip()}%"
        consulta = consulta.filter(or_(
            Avaliacao.titulo.ilike(like),
            Avaliacao.objeto_conhecimento.ilike(like),
            Avaliacao.criterio_correcao.ilike(like),
        ))
    if antes_de is not None and antes_id is not None:
        consulta = consulta.filter(or_(
            Avaliacao.data_inicio > antes_de,
            and_(Avaliacao.data_inicio == antes_de, Avaliacao.id > antes_id),
            and_(Avaliacao.data_inicio.is_(None), Avaliacao.id > antes_id),
        ))
    # O DISTINCT fica só no id. No Postgres a coluna JSON não tem operador de igualdade.
    ids = (
        consulta.enable_eagerloads(False)
        .with_entities(Avaliacao.id.label("avaliacao_id"))
        .distinct()
        .subquery()
    )
    itens = (
        db.query(Avaliacao)
        .options(*_opcoes_avaliacao())
        .filter(Avaliacao.id.in_(db.query(ids.c.avaliacao_id)))
        .order_by(Avaliacao.data_inicio.asc().nulls_last(), Avaliacao.disciplina.asc(), Avaliacao.ordem.asc(), Avaliacao.id.asc())
        .limit(limite)
        .all()
    )
    return [serial_avaliacao(item, current_user) for item in itens]


@router.post("/avaliacoes", status_code=status.HTTP_201_CREATED)
def criar_avaliacao(
    payload: AvaliacaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cria uma avaliação com as datas e os itens do critério."""
    exigir_adulto(current_user)
    cronograma = _cronograma_ou_404(db, payload.cronograma_id, current_user)
    pacote = _pacote_avaliacao(payload, payload.sequencia)
    avaliacao = Avaliacao(
        family_id=cronograma.family_id,
        cronograma=cronograma,
        chave_origem=payload.chave_origem,
        disciplina=payload.disciplina,
        categoria=payload.categoria,
        titulo=payload.titulo,
        created_by_id=current_user.id,
    )
    db.add(avaliacao)
    db.flush()
    _aplicar_avaliacao(avaliacao, payload, payload.sequencia, pacote)
    _gravar_ocorrencias(db, avaliacao, payload.ocorrencias, current_user)
    _gravar_itens(db, avaliacao, payload.itens_criterio, current_user)
    db.commit()
    return serial_avaliacao(carregar_avaliacao(db, avaliacao.id, current_user), current_user, completo=True)


@router.get("/avaliacoes/{avaliacao_id}")
def detalhe_avaliacao(
    avaliacao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalhe completo, com o texto integral do PDF."""
    return serial_avaliacao(carregar_avaliacao(db, avaliacao_id, current_user), current_user, completo=True)


@router.put("/avaliacoes/{avaliacao_id}")
def substituir_avaliacao(
    avaliacao_id: int,
    payload: AvaliacaoPut,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Substitui a avaliação, inclusive datas e itens."""
    exigir_adulto(current_user)
    avaliacao = carregar_avaliacao(db, avaliacao_id, current_user)
    pacote = _pacote_avaliacao(payload, avaliacao.ordem)
    from app.services.provas import _ocorrencias_json, _registrar_historico
    antes = _ocorrencias_json(avaliacao.ocorrencias)
    _aplicar_avaliacao(avaliacao, payload, avaliacao.ordem, pacote)
    _gravar_ocorrencias(db, avaliacao, payload.ocorrencias, current_user)
    _gravar_itens(db, avaliacao, payload.itens_criterio, current_user)
    _registrar_historico(db, avaliacao, antes, pacote["ocorrencias"], current_user, None, None)
    db.commit()
    return serial_avaliacao(carregar_avaliacao(db, avaliacao.id, current_user), current_user, completo=True)


@router.patch("/avaliacoes/{avaliacao_id}")
def atualizar_avaliacao(
    avaliacao_id: int,
    payload: AvaliacaoPatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Atualiza só o que foi enviado. Serve para remarcar a data quando a escola avisar."""
    exigir_adulto(current_user)
    avaliacao = carregar_avaliacao(db, avaliacao_id, current_user)
    aplicar_patch(db, avaliacao, payload, current_user)
    db.commit()
    return serial_avaliacao(carregar_avaliacao(db, avaliacao.id, current_user), current_user, completo=True)


@router.delete("/avaliacoes/{avaliacao_id}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_avaliacao(
    avaliacao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Apaga uma avaliação."""
    exigir_adulto(current_user)
    avaliacao = carregar_avaliacao(db, avaliacao_id, current_user)
    db.delete(avaliacao)
    db.commit()


def _calendario_eventos(
    db: Session,
    usuario: User,
    de: date,
    ate: date,
    aluno_id: Optional[int],
    disciplina: Optional[list[str]],
    categoria: Optional[list[str]],
    incluir_eventos: bool,
) -> list[dict]:
    consulta = (
        db.query(AvaliacaoOcorrencia)
        .join(Avaliacao)
        .join(Cronograma)
        .options(
            selectinload(AvaliacaoOcorrencia.avaliacao)
            .selectinload(Avaliacao.cronograma)
            .selectinload(Cronograma.vinculos)
        )
        .filter(
            Cronograma.family_id == familia_do(usuario),
            Cronograma.status == "ativo",
            AvaliacaoOcorrencia.data_inicio <= ate,
            AvaliacaoOcorrencia.data_fim >= de,
        )
    )
    if usuario.is_child:
        consulta = consulta.filter(Cronograma.vinculos.any(CronogramaAluno.aluno_id == usuario.id))
    elif aluno_id is not None:
        consulta = consulta.filter(Cronograma.vinculos.any(CronogramaAluno.aluno_id == aluno_id))
    if disciplina:
        consulta = consulta.filter(Avaliacao.disciplina.in_(disciplina))
    if categoria:
        consulta = consulta.filter(Avaliacao.categoria.in_(categoria))
    eventos = []
    for ocorrencia in consulta.all():
        avaliacao = ocorrencia.avaliacao
        cronograma = avaliacao.cronograma
        eventos.append({
            "id": f"av-{avaliacao.id}-oc-{ocorrencia.id}",
            "avaliacao_id": avaliacao.id,
            "tipo": "avaliacao",
            "titulo_exibicao": titulo_evento(avaliacao, ocorrencia.turma),
            "disciplina": avaliacao.disciplina,
            "categoria": avaliacao.categoria,
            "titulo": avaliacao.titulo,
            "inicio": ocorrencia.data_inicio,
            "fim": ocorrencia.data_fim,
            "dia_inteiro": True,
            "periodo": ocorrencia.data_fim > ocorrencia.data_inicio,
            "turma": ocorrencia.turma,
            "valor": float(avaliacao.valor) if avaliacao.valor is not None else None,
            "aluno_ids": [vinculo.aluno_id for vinculo in cronograma.vinculos],
            "cor": CORES_CATEGORIA.get(avaliacao.categoria, "#546E7A"),
            "_ordem": (ocorrencia.data_inicio, ORDEM_CATEGORIA.get(avaliacao.categoria, 9), avaliacao.disciplina, avaliacao.ordem),
        })
    if incluir_eventos and not disciplina and not categoria:
        escolares = (
            db.query(EventoEscolar)
            .join(Cronograma)
            .filter(
                Cronograma.family_id == familia_do(usuario),
                Cronograma.status == "ativo",
                EventoEscolar.data_inicio <= ate,
                EventoEscolar.data_fim >= de,
            )
        )
        if usuario.is_child:
            escolares = escolares.filter(Cronograma.vinculos.any(CronogramaAluno.aluno_id == usuario.id))
        elif aluno_id is not None:
            escolares = escolares.filter(Cronograma.vinculos.any(CronogramaAluno.aluno_id == aluno_id))
        for evento in escolares.all():
            eventos.append({
                "id": f"ev-{evento.id}",
                "tipo": "evento_escolar",
                "evento_tipo": evento.tipo,
                "titulo_exibicao": evento.legenda,
                "inicio": evento.data_inicio,
                "fim": evento.data_fim,
                "dia_inteiro": True,
                "periodo": evento.data_fim > evento.data_inicio,
                "cor": CORES_EVENTO.get(evento.tipo, "#546E7A"),
                "_ordem": (evento.data_inicio, 8, evento.legenda, evento.id),
            })
    eventos.sort(key=lambda item: item["_ordem"])
    for item in eventos:
        item.pop("_ordem", None)
    return eventos


@router.get("/calendario")
def calendario(
    de: date,
    ate: date,
    aluno_id: Optional[int] = None,
    disciplina: Optional[list[str]] = Query(None),
    categoria: Optional[list[str]] = Query(None),
    incluir_eventos_escolares: bool = True,
    agrupar: str = Query("evento"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calendário do período. O fim da ocorrência é inclusivo."""
    if ate < de:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="ate não pode ser anterior a de.")
    if agrupar not in {"evento", "dia"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="agrupar deve ser evento ou dia.")
    eventos = _calendario_eventos(
        db, current_user, de, ate,
        None if current_user.is_child else aluno_id,
        disciplina, categoria, incluir_eventos_escolares,
    )
    if agrupar == "evento":
        return eventos
    dias = {}
    cursor = de
    while cursor <= ate:
        dias[cursor.isoformat()] = []
        cursor += timedelta(days=1)
    for evento in eventos:
        if evento.get("tipo") != "avaliacao":
            continue
        inicio = evento["inicio"]
        fim = evento["fim"]
        cursor = max(inicio, de)
        limite = min(fim, ate)
        while cursor <= limite:
            dias[cursor.isoformat()].append({
                "avaliacao_id": evento["avaliacao_id"],
                "disciplina": evento["disciplina"],
                "categoria": evento["categoria"],
                "titulo": evento["titulo"],
                "periodo": evento["periodo"],
                "inicio_periodo": cursor == inicio,
                "fim_periodo": cursor == fim,
                "turma": evento.get("turma"),
            })
            cursor += timedelta(days=1)
    return dias
