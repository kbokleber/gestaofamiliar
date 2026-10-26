import hashlib
import json
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.estudo import Atividade
from app.models.prova import (
    Avaliacao,
    AvaliacaoHistorico,
    AvaliacaoItem,
    AvaliacaoOcorrencia,
    Cronograma,
    CronogramaAluno,
    EventoEscolar,
)
from app.models.user import User
from app.schemas.prova import (
    AvaliacaoIn,
    AvaliacaoPatch,
    DocumentoIn,
    Importacao,
    OcorrenciaIn,
)

ORDEM_CATEGORIA = {
    "AV1": 0,
    "AV2": 1,
    "REDACAO": 2,
    "PRODUTIVIDADE": 3,
    "RECUPERACAO": 4,
    "SUBSTITUTIVA": 5,
    "OUTRO": 6,
}
CORES_CATEGORIA = {
    "AV1": "#43A047",
    "AV2": "#FB8C00",
    "RECUPERACAO": "#EF9A9A",
    "REDACAO": "#8E24AA",
    "PRODUTIVIDADE": "#1E88E5",
    "SUBSTITUTIVA": "#D81B60",
    "OUTRO": "#546E7A",
}
CORES_EVENTO = {
    "RECESSO": "#E53935",
    "DIVULGACAO_RESULTADO": "#FDD835",
    "PROVAS_SUBSTITUTIVAS": "#D81B60",
    "INICIO_BIMESTRE": "#7E57C2",
    "TERMINO_BIMESTRE": "#7E57C2",
    "SEMANA_AV1": "#43A047",
    "SEMANA_AV2": "#FB8C00",
    "SEMANA_RECUPERACAO": "#EF9A9A",
    "OUTRO": "#546E7A",
}


def hoje_local() -> date:
    from datetime import datetime, timezone
    return datetime.now(timezone(timedelta(hours=-3))).date()


def _numero(valor) -> Optional[str]:
    if valor is None:
        return None
    return format(Decimal(str(valor)).normalize(), "f")


def _hash(dados: dict) -> str:
    bruto = json.dumps(dados, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def _ocorrencias_json(ocorrencias: list) -> list[dict]:
    return [
        {
            "data_inicio": item.data_inicio.isoformat(),
            "data_fim": item.data_fim.isoformat(),
            "turma": item.turma,
        }
        for item in ocorrencias
    ]


def _pacote_avaliacao(dados: AvaliacaoIn, ordem: int) -> dict:
    ocorrencias = _ocorrencias_json(dados.ocorrencias)
    inicios = [item.data_inicio for item in dados.ocorrencias]
    fins = [item.data_fim for item in dados.ocorrencias]
    return {
        "chave_origem": dados.chave_origem,
        "disciplina": dados.disciplina,
        "categoria": dados.categoria,
        "categoria_rotulo": dados.categoria_rotulo,
        "sequencia": dados.sequencia,
        "ordem": ordem,
        "titulo": dados.titulo,
        "data_texto": dados.data_texto,
        "sem_data": not ocorrencias,
        "data_inicio": min(inicios).isoformat() if inicios else None,
        "data_fim": max(fins).isoformat() if fins else None,
        "ocorrencias": ocorrencias,
        "valor": _numero(dados.valor),
        "valor_texto": dados.valor_texto,
        "objeto_conhecimento": dados.objeto_conhecimento,
        "criterio_correcao": dados.criterio_correcao,
        "itens_criterio": [
            {
                "ordem": item.ordem,
                "descricao": item.descricao,
                "pontos": _numero(item.pontos),
                "por_unidade": item.por_unidade,
                "quantidade": item.quantidade,
            }
            for item in dados.itens_criterio
        ],
        "material_necessario": dados.material_necessario,
        "observacoes": dados.observacoes,
    }


def _pacote_documento(documento: DocumentoIn) -> dict:
    return {
        "chave_origem": documento.chave_origem,
        "titulo": documento.titulo,
        "subtitulo": documento.subtitulo,
        "turma": documento.turma,
        "turmas": documento.turmas,
        "serie": documento.serie,
        "bimestre": documento.bimestre,
        "ano_letivo": documento.ano_letivo,
        "escola": documento.escola,
        "data_publicacao": documento.data_publicacao.isoformat() if documento.data_publicacao else None,
        "autor": documento.autor,
        "aviso": documento.aviso,
        "introducao": documento.introducao,
        "orientacoes": [item.model_dump() for item in documento.orientacoes],
        "eventos_escolares": [
            {
                "tipo": item.tipo,
                "legenda": item.legenda,
                "data_inicio": item.data_inicio.isoformat(),
                "data_fim": item.data_fim.isoformat(),
            }
            for item in documento.eventos_escolares
        ],
        "calendario_organizacional": [item.model_dump(mode="json") for item in documento.calendario_organizacional],
    }


def erro(loc: list, msg: str) -> None:
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=[{"loc": loc, "msg": msg}])


def familia_do(usuario: User) -> int:
    if usuario.family_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada.")
    return usuario.family_id


def exigir_adulto(usuario: User) -> None:
    if usuario.is_child:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Somente um adulto pode alterar as avaliações.",
        )


def filhos_da_familia(db: Session, aluno_ids: list[int], family_id: int, loc: list) -> list[User]:
    alunos = db.query(User).filter(User.id.in_(aluno_ids)).all()
    por_id = {aluno.id: aluno for aluno in alunos}
    for indice, aluno_id in enumerate(aluno_ids):
        aluno = por_id.get(aluno_id)
        if (
            aluno is None
            or not aluno.is_active
            or not aluno.is_child
            or aluno.is_superuser
            or aluno.family_id != family_id
        ):
            erro([*loc, indice], "O aluno não é um filho desta família.")
    return [por_id[aluno_id] for aluno_id in aluno_ids]


def _conferir_chaves(payload: Importacao) -> None:
    vistas = set()
    for indice, avaliacao in enumerate(payload.avaliacoes):
        if not avaliacao.chave_origem:
            erro(["avaliacoes", indice, "chave_origem"], "chave_origem é obrigatória.")
        if avaliacao.chave_origem in vistas:
            erro(["avaliacoes", indice, "chave_origem"], "chave_origem duplicada no payload.")
        vistas.add(avaliacao.chave_origem)
    if not payload.documento.chave_origem:
        erro(["documento", "chave_origem"], "chave_origem é obrigatória.")


def _conferir_comunicado(db: Session, documento: DocumentoIn, family_id: int) -> None:
    if documento.comunicado_id is None:
        return
    atividade = db.query(Atividade).filter(Atividade.id == documento.comunicado_id).first()
    if atividade is None or atividade.family_id != family_id:
        erro(["documento", "comunicado_id"], "Comunicado não encontrado nesta família.")


def _nome(usuario: User) -> str:
    nome = f"{usuario.first_name or ''} {usuario.last_name or ''}".strip()
    return nome or usuario.username


def _vincular(db: Session, cronograma: Cronograma, alunos: list[User], usuario: User, substituir: bool) -> bool:
    atuais = {vinculo.aluno_id: vinculo for vinculo in cronograma.vinculos}
    mudou = False
    if substituir:
        novos = {aluno.id for aluno in alunos}
        for aluno_id, vinculo in list(atuais.items()):
            if aluno_id not in novos:
                db.delete(vinculo)
                mudou = True
    for aluno in alunos:
        if aluno.id not in atuais:
            db.add(CronogramaAluno(
                cronograma=cronograma,
                aluno_id=aluno.id,
                family_id=cronograma.family_id,
                created_by_id=usuario.id,
            ))
            mudou = True
    return mudou


def _preencher_documento(cronograma: Cronograma, documento: DocumentoIn, pacote: dict) -> None:
    cronograma.titulo = documento.titulo
    cronograma.subtitulo = documento.subtitulo
    cronograma.turma = documento.turma
    cronograma.turmas = documento.turmas
    cronograma.serie = documento.serie
    cronograma.bimestre = documento.bimestre
    cronograma.ano_letivo = documento.ano_letivo
    cronograma.escola = documento.escola
    cronograma.data_publicacao = documento.data_publicacao
    cronograma.autor = documento.autor
    cronograma.aviso = documento.aviso
    cronograma.introducao = documento.introducao
    cronograma.orientacoes = [item.model_dump() for item in documento.orientacoes]
    cronograma.calendario_organizacional = pacote["calendario_organizacional"]
    cronograma.comunicado_id = documento.comunicado_id
    cronograma.anexo_idx = documento.anexo_idx
    cronograma.anexo_nome = documento.anexo_nome
    cronograma.hash_conteudo = _hash(pacote)


def _eventos_iguais(cronograma: Cronograma, documento: DocumentoIn) -> bool:
    atual = sorted(
        (evento.tipo, evento.legenda, evento.data_inicio.isoformat(), evento.data_fim.isoformat())
        for evento in cronograma.eventos
    )
    novo = sorted(
        (evento.tipo, evento.legenda, evento.data_inicio.isoformat(), evento.data_fim.isoformat())
        for evento in documento.eventos_escolares
    )
    return atual == novo


def _trocar_eventos(db: Session, cronograma: Cronograma, documento: DocumentoIn, usuario: User) -> None:
    for evento in list(cronograma.eventos):
        db.delete(evento)
    db.flush()
    for evento in documento.eventos_escolares:
        db.add(EventoEscolar(
            family_id=cronograma.family_id,
            cronograma=cronograma,
            tipo=evento.tipo,
            legenda=evento.legenda,
            data_inicio=evento.data_inicio,
            data_fim=evento.data_fim,
            created_by_id=usuario.id,
        ))


def _gravar_ocorrencias(db: Session, avaliacao: Avaliacao, ocorrencias: list[OcorrenciaIn], usuario: User) -> None:
    for item in list(avaliacao.ocorrencias):
        db.delete(item)
    db.flush()
    for item in ocorrencias:
        db.add(AvaliacaoOcorrencia(
            family_id=avaliacao.family_id,
            avaliacao=avaliacao,
            data_inicio=item.data_inicio,
            data_fim=item.data_fim,
            turma=item.turma,
            created_by_id=usuario.id,
        ))


def _gravar_itens(db: Session, avaliacao: Avaliacao, itens: list, usuario: User) -> None:
    for item in list(avaliacao.itens):
        db.delete(item)
    db.flush()
    for item in itens:
        db.add(AvaliacaoItem(
            family_id=avaliacao.family_id,
            avaliacao=avaliacao,
            ordem=item.ordem,
            descricao=item.descricao,
            pontos=item.pontos,
            por_unidade=item.por_unidade,
            quantidade=item.quantidade,
            created_by_id=usuario.id,
        ))


def _aplicar_avaliacao(avaliacao: Avaliacao, dados: AvaliacaoIn, ordem: int, pacote: dict) -> None:
    avaliacao.disciplina = dados.disciplina
    avaliacao.categoria = dados.categoria
    avaliacao.categoria_rotulo = dados.categoria_rotulo
    avaliacao.sequencia = dados.sequencia
    avaliacao.ordem = ordem
    avaliacao.titulo = dados.titulo
    avaliacao.data_texto = dados.data_texto
    avaliacao.sem_data = pacote["sem_data"]
    avaliacao.data_inicio = date.fromisoformat(pacote["data_inicio"]) if pacote["data_inicio"] else None
    avaliacao.data_fim = date.fromisoformat(pacote["data_fim"]) if pacote["data_fim"] else None
    avaliacao.valor = dados.valor
    avaliacao.valor_texto = dados.valor_texto
    avaliacao.objeto_conhecimento = dados.objeto_conhecimento
    avaliacao.criterio_correcao = dados.criterio_correcao
    avaliacao.material_necessario = dados.material_necessario
    avaliacao.observacoes = dados.observacoes
    avaliacao.ambiguidades = dados.ambiguidades
    avaliacao.hash_conteudo = _hash(pacote)


def _registrar_historico(
    db: Session,
    avaliacao: Avaliacao,
    antes: list[dict],
    depois: list[dict],
    usuario: User,
    motivo: Optional[str],
    comunicado_id: Optional[int],
) -> None:
    if antes == depois:
        return
    db.add(AvaliacaoHistorico(
        family_id=avaliacao.family_id,
        avaliacao=avaliacao,
        ocorrencias_antes=antes,
        ocorrencias_depois=depois,
        motivo=motivo,
        comunicado_id=comunicado_id,
        created_by_id=usuario.id,
    ))


def importar_cronograma(
    db: Session,
    usuario: User,
    payload: Importacao,
    modo_remocao: str,
    substituir_alunos: bool,
) -> dict:
    _conferir_chaves(payload)
    family_id = familia_do(usuario)
    documento = payload.documento
    _conferir_comunicado(db, documento, family_id)
    alunos = filhos_da_familia(db, documento.aluno_ids, family_id, ["documento", "aluno_ids"])
    pacote_documento = _pacote_documento(documento)
    hash_documento = _hash(pacote_documento)
    avisos = []

    cronograma = (
        db.query(Cronograma)
        .options(selectinload(Cronograma.vinculos), selectinload(Cronograma.eventos))
        .filter(Cronograma.family_id == family_id, Cronograma.chave_origem == documento.chave_origem)
        .first()
    )
    if cronograma is None:
        cronograma = Cronograma(
            family_id=family_id,
            chave_origem=documento.chave_origem,
            bimestre=documento.bimestre,
            ano_letivo=documento.ano_letivo,
            created_by_id=usuario.id,
            status="ativo",
        )
        db.add(cronograma)
        db.flush()
        situacao = "criado"
        _preencher_documento(cronograma, documento, pacote_documento)
        _trocar_eventos(db, cronograma, documento, usuario)
    else:
        if cronograma.hash_conteudo != hash_documento:
            _preencher_documento(cronograma, documento, pacote_documento)
            situacao = "atualizado"
        else:
            cronograma.comunicado_id = documento.comunicado_id
            cronograma.anexo_idx = documento.anexo_idx
            cronograma.anexo_nome = documento.anexo_nome
            situacao = "inalterado"
        if not _eventos_iguais(cronograma, documento):
            _trocar_eventos(db, cronograma, documento, usuario)
            situacao = "atualizado"
    alunos_mudaram = _vincular(db, cronograma, alunos, usuario, substituir_alunos)
    if alunos_mudaram and situacao == "inalterado":
        situacao = "atualizado"

    if documento.comunicado_id and documento.anexo_idx is not None and documento.anexo_nome:
        atividade = db.query(Atividade).filter(Atividade.id == documento.comunicado_id).first()
        nomes = []
        if atividade is not None and atividade.anexos:
            try:
                bruto = json.loads(atividade.anexos)
            except json.JSONDecodeError:
                bruto = []
            if isinstance(bruto, list):
                nomes = [str(item.get("name") or "") for item in bruto if isinstance(item, dict)]
        if documento.anexo_nome not in nomes and documento.anexo_idx >= len(nomes):
            avisos.append(
                f"comunicado_id {documento.comunicado_id}: anexo_idx {documento.anexo_idx} "
                "não encontrado; vínculo pelo nome do arquivo"
            )

    existentes = {
        item.chave_origem: item
        for item in db.query(Avaliacao)        .options(
            selectinload(Avaliacao.ocorrencias),
            selectinload(Avaliacao.itens),
        ).filter(Avaliacao.cronograma_id == cronograma.id).all()
    }
    recebidas = set()
    relatorio = {"criadas": 0, "atualizadas": 0, "inalteradas": 0, "removidas": 0}
    detalhes = []
    for indice, dados in enumerate(payload.avaliacoes):
        ordem = indice + 1
        pacote = _pacote_avaliacao(dados, ordem)
        assinatura = _hash(pacote)
        recebidas.add(dados.chave_origem)
        atual = existentes.get(dados.chave_origem)
        if atual is None:
            outra = db.query(Avaliacao).filter(
                Avaliacao.family_id == family_id,
                Avaliacao.chave_origem == dados.chave_origem,
            ).first()
            if outra is not None and outra.cronograma_id != cronograma.id:
                erro(["avaliacoes", indice, "chave_origem"], "chave_origem já usada em outro cronograma.")
            avaliacao = Avaliacao(
                family_id=family_id,
                cronograma=cronograma,
                chave_origem=dados.chave_origem,
                disciplina=dados.disciplina,
                categoria=dados.categoria,
                titulo=dados.titulo,
                created_by_id=usuario.id,
            )
            db.add(avaliacao)
            db.flush()
            _aplicar_avaliacao(avaliacao, dados, ordem, pacote)
            _gravar_ocorrencias(db, avaliacao, dados.ocorrencias, usuario)
            _gravar_itens(db, avaliacao, dados.itens_criterio, usuario)
            relatorio["criadas"] += 1
            detalhes.append({"chave_origem": dados.chave_origem, "acao": "criada", "id": avaliacao.id})
            continue
        if atual.hash_conteudo == assinatura:
            relatorio["inalteradas"] += 1
            detalhes.append({"chave_origem": dados.chave_origem, "acao": "inalterada", "id": atual.id})
            continue
        antes = _ocorrencias_json(atual.ocorrencias)
        _aplicar_avaliacao(atual, dados, ordem, pacote)
        _gravar_ocorrencias(db, atual, dados.ocorrencias, usuario)
        _gravar_itens(db, atual, dados.itens_criterio, usuario)
        _registrar_historico(
            db, atual, antes, pacote["ocorrencias"], usuario, "Reimportação do cronograma", documento.comunicado_id,
        )
        relatorio["atualizadas"] += 1
        detalhes.append({"chave_origem": dados.chave_origem, "acao": "atualizada", "id": atual.id})

    if modo_remocao == "remover":
        for chave, avaliacao in existentes.items():
            if chave in recebidas:
                continue
            db.delete(avaliacao)
            relatorio["removidas"] += 1
            detalhes.append({"chave_origem": chave, "acao": "removida", "id": avaliacao.id})

    db.flush()
    return {
        "cronograma_id": cronograma.id,
        "cronograma": situacao,
        "avaliacoes": relatorio,
        "detalhes": detalhes,
        "avisos": avisos,
    }


def pode_ver_cronograma(cronograma: Cronograma, usuario: User) -> None:
    if cronograma.family_id != familia_do(usuario):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cronograma não encontrado.")
    if usuario.is_child and usuario.id not in {vinculo.aluno_id for vinculo in cronograma.vinculos}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cronograma não encontrado.")


def query_visivel(db: Session, usuario: User, aluno_id: Optional[int] = None):
    family_id = familia_do(usuario)
    consulta = db.query(Cronograma).filter(Cronograma.family_id == family_id, Cronograma.status == "ativo")
    if usuario.is_child:
        consulta = consulta.filter(Cronograma.vinculos.any(CronogramaAluno.aluno_id == usuario.id))
    elif aluno_id is not None:
        consulta = consulta.filter(Cronograma.vinculos.any(CronogramaAluno.aluno_id == aluno_id))
    return consulta


def _float(valor) -> Optional[float]:
    if valor is None:
        return None
    return float(valor)


def _orientacao(cronograma: Cronograma, categoria: str) -> Optional[str]:
    if categoria == "PRODUTIVIDADE":
        trecho = "produtiv"
    elif categoria == "RECUPERACAO":
        trecho = "recuper"
    else:
        return None
    for item in cronograma.orientacoes or []:
        titulo = str(item.get("titulo") or "").lower()
        if trecho in titulo:
            return item.get("texto")
    return None


def serial_ocorrencia(item: AvaliacaoOcorrencia) -> dict:
    return {
        "id": item.id,
        "data_inicio": item.data_inicio,
        "data_fim": item.data_fim,
        "turma": item.turma,
    }


def serial_item(item: AvaliacaoItem) -> dict:
    return {
        "ordem": item.ordem,
        "descricao": item.descricao,
        "pontos": _float(item.pontos),
        "por_unidade": item.por_unidade,
        "quantidade": item.quantidade,
    }


def soma_itens(itens: list[AvaliacaoItem]) -> Optional[float]:
    valores = [Decimal(str(item.pontos)) for item in itens if item.pontos is not None]
    if not valores:
        return None
    return float(sum(valores, Decimal("0")))


def alunos_do(cronograma: Cronograma) -> list[dict]:
    return [
        {"id": vinculo.aluno_id, "nome": _nome(vinculo.aluno) if vinculo.aluno else str(vinculo.aluno_id)}
        for vinculo in cronograma.vinculos
    ]


def pdf_do(cronograma: Cronograma) -> Optional[dict]:
    if cronograma.comunicado_id is None:
        return None
    from app.core.config import settings
    idx = cronograma.anexo_idx if cronograma.anexo_idx is not None else 0
    return {
        "comunicado_id": cronograma.comunicado_id,
        "anexo_idx": idx,
        "nome": cronograma.anexo_nome,
        "url_inline": (
            f"{settings.API_V1_STR}/estudos/atividades/{cronograma.comunicado_id}"
            f"/anexos/{idx}/download?inline=1"
        ),
    }


def serial_avaliacao(avaliacao: Avaliacao, usuario: User, completo: bool = False) -> dict:
    cronograma = avaliacao.cronograma
    dados = {
        "id": avaliacao.id,
        "chave_origem": avaliacao.chave_origem,
        "disciplina": avaliacao.disciplina,
        "categoria": avaliacao.categoria,
        "categoria_rotulo": avaliacao.categoria_rotulo,
        "sequencia": avaliacao.sequencia,
        "ordem": avaliacao.ordem,
        "titulo": avaliacao.titulo,
        "data_texto": avaliacao.data_texto,
        "sem_data": avaliacao.sem_data,
        "data_inicio": avaliacao.data_inicio,
        "data_fim": avaliacao.data_fim,
        "ocorrencias": [serial_ocorrencia(item) for item in avaliacao.ocorrencias],
        "valor": _float(avaliacao.valor),
        "valor_texto": avaliacao.valor_texto,
        "objeto_conhecimento": avaliacao.objeto_conhecimento,
        "criterio_correcao": avaliacao.criterio_correcao,
        "itens_criterio": [serial_item(item) for item in avaliacao.itens],
        "soma_itens": soma_itens(avaliacao.itens),
        "material_necessario": avaliacao.material_necessario,
        "observacoes": avaliacao.observacoes,
        "ambiguidades": [] if usuario.is_child else (avaliacao.ambiguidades or []),
        "cronograma_id": avaliacao.cronograma_id,
        "aluno_ids": [vinculo.aluno_id for vinculo in cronograma.vinculos] if cronograma else [],
    }
    if completo and cronograma is not None:
        dados["cronograma"] = {
            "id": cronograma.id,
            "titulo": cronograma.titulo,
            "turma": cronograma.turma,
            "bimestre": cronograma.bimestre,
            "ano_letivo": cronograma.ano_letivo,
        }
        dados["alunos"] = alunos_do(cronograma)
        dados["pdf"] = pdf_do(cronograma)
        dados["orientacoes_categoria"] = _orientacao(cronograma, avaliacao.categoria)
    return dados


def titulo_evento(avaliacao: Avaliacao, turma: Optional[str]) -> str:
    categoria = f"{avaliacao.categoria} ({turma})" if turma else avaliacao.categoria
    return f"{avaliacao.disciplina} · {categoria} · {avaliacao.titulo}"


def carregar_avaliacao(db: Session, avaliacao_id: int, usuario: User) -> Avaliacao:
    avaliacao = (
        db.query(Avaliacao)
        .options(
            selectinload(Avaliacao.ocorrencias),
            selectinload(Avaliacao.itens),
            selectinload(Avaliacao.cronograma).selectinload(Cronograma.vinculos).selectinload(CronogramaAluno.aluno),
        )
        .filter(Avaliacao.id == avaliacao_id)
        .first()
    )
    if avaliacao is None or avaliacao.cronograma is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avaliação não encontrada.")
    pode_ver_cronograma(avaliacao.cronograma, usuario)
    return avaliacao


def aplicar_patch(db: Session, avaliacao: Avaliacao, payload: AvaliacaoPatch, usuario: User) -> None:
    campos = payload.model_dump(exclude_unset=True)
    motivo = campos.pop("alteracao_motivo", None)
    comunicado_id = campos.pop("alteracao_comunicado_id", None)
    ocorrencias = campos.pop("ocorrencias", None)
    itens = campos.pop("itens_criterio", None)
    for campo, valor in campos.items():
        if isinstance(valor, str):
            valor = valor.strip()
        setattr(avaliacao, campo, valor)
    antes = _ocorrencias_json(avaliacao.ocorrencias)
    if ocorrencias is not None:
        convertidas = [OcorrenciaIn(**item) for item in ocorrencias]
        _gravar_ocorrencias(db, avaliacao, convertidas, usuario)
        avaliacao.sem_data = not convertidas
        avaliacao.data_inicio = min((item.data_inicio for item in convertidas), default=None)
        avaliacao.data_fim = max((item.data_fim for item in convertidas), default=None)
        _registrar_historico(db, avaliacao, antes, _ocorrencias_json(convertidas), usuario, motivo, comunicado_id)
    if itens is not None:
        from app.schemas.prova import ItemIn
        _gravar_itens(db, avaliacao, [ItemIn(**item) for item in itens], usuario)
