import base64
import hashlib
import hmac
import io
import json
import shutil
import subprocess
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path, PurePath
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, Security, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, defer, joinedload

from app.api.deps import api_key_header, get_current_admin, get_current_user, oauth2_scheme
from app.core.config import settings
from app.db.base import get_db
from app.models.estudo import Atividade
from app.models.user import User
from app.schemas.estudo import Anexo, Atividade as AtividadeSchema
from app.schemas.estudo import AtividadeCreate, AtividadeUpdate

TIPOS_ESTUDO = {"atividade", "comunicado"}
DIAS_COMUNICADO_RECENTE = 14

PASTA_ANEXOS = Path(__file__).resolve().parents[4] / "var" / "anexo_cache"
LINK_SEGUNDOS = 600

TAMANHO_MAXIMO = 25 * 1024 * 1024
LIMITE_COMPRIMIR = 5 * 1024 * 1024
LADO_MAXIMO_IMAGEM = 1600
LIMITE_ANEXOS = 10
TIPOS_ANEXO = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".pdf": "application/pdf",
}

router = APIRouter()


def _aluno_nome(user: User) -> str:
    nome = f"{user.first_name or ''} {user.last_name or ''}".strip()
    return nome or user.username


def _carregar_anexos(atividade: Atividade) -> list[dict]:
    if not atividade.anexos:
        return []
    try:
        dados = json.loads(atividade.anexos)
    except json.JSONDecodeError:
        return []
    return dados if isinstance(dados, list) else []


def _publico(itens: list[dict]) -> list[Anexo]:
    publicos = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        publicos.append(Anexo(
            name=str(item.get("name") or "imagem"),
            type=str(item.get("type") or "application/octet-stream"),
            size=int(item.get("size") or 0),
        ))
    return publicos


def _ler_resumo(atividade: Atividade) -> list[dict]:
    if not atividade.anexos_resumo:
        return []
    try:
        dados = json.loads(atividade.anexos_resumo)
    except json.JSONDecodeError:
        return []
    return dados if isinstance(dados, list) else []


def _caches_ok(resumo: list[dict]) -> bool:
    if not resumo:
        return True
    return all(
        isinstance(item, dict) and item.get("arquivo") and (PASTA_ANEXOS / str(item["arquivo"])).is_file()
        for item in resumo
    )


def _gravar_cache(conteudo: bytes) -> str:
    PASTA_ANEXOS.mkdir(parents=True, exist_ok=True)
    chave = hashlib.sha256(conteudo).hexdigest()
    destino = PASTA_ANEXOS / chave
    if not destino.exists():
        destino.write_bytes(conteudo)
    return chave


def _garantir_arquivos(atividade: Atividade, db: Session) -> list[dict]:
    """Mantém nome, tipo e tamanho à parte do arquivo e uma cópia em disco para o navegador abrir direto."""
    resumo = _ler_resumo(atividade)
    if resumo and _caches_ok(resumo):
        return resumo
    novo = []
    for item in _carregar_anexos(atividade):
        if not isinstance(item, dict):
            continue
        chave = item.get("arquivo")
        if chave and (PASTA_ANEXOS / str(chave)).is_file():
            novo.append({
                "name": item.get("name") or "imagem",
                "type": item.get("type") or "application/octet-stream",
                "size": int(item.get("size") or 0),
                "arquivo": chave,
            })
            continue
        dados = item.get("data")
        if not dados:
            continue
        conteudo = base64.b64decode(dados)
        chave = _gravar_cache(conteudo)
        novo.append({
            "name": item.get("name") or "imagem",
            "type": item.get("type") or "application/octet-stream",
            "size": len(conteudo),
            "arquivo": chave,
        })
    atividade.anexos_resumo = json.dumps(novo)
    db.commit()
    return novo


def _assinar(atividade_id: int, idx: int, exp: int) -> str:
    mensagem = f"{atividade_id}:{idx}:{exp}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), mensagem, hashlib.sha256).hexdigest()


def _link_valido(atividade_id: int, idx: int, exp: Optional[int], sig: Optional[str]) -> bool:
    if exp is None or not sig or exp < int(time.time()) or exp > int(time.time()) + LINK_SEGUNDOS + 30:
        return False
    esperado = _assinar(atividade_id, idx, exp)
    return hmac.compare_digest(esperado, sig)


def _to_schema(atividade: Atividade, incluir_anexos: bool = True, resumo: Optional[list[dict]] = None) -> AtividadeSchema:
    return AtividadeSchema(
        id=atividade.id,
        aluno_id=atividade.aluno_id,
        family_id=atividade.family_id,
        aluno_nome=_aluno_nome(atividade.aluno) if atividade.aluno else "",
        titulo=atividade.titulo,
        descricao=atividade.descricao or "",
        disciplina=atividade.disciplina or None,
        professor=atividade.professor or "",
        data=atividade.data,
        prazo_entrega=atividade.prazo_entrega,
        tipo=atividade.tipo or "atividade",
        autor=atividade.autor,
        numero=atividade.numero,
        status=None if (atividade.tipo or "atividade") == "comunicado" else (atividade.status or "pendente"),
        anexos=_publico(resumo if resumo is not None else _ler_resumo(atividade)) if incluir_anexos else [],
        concluida_em=atividade.concluida_em,
        created_by_id=atividade.created_by_id,
        created_at=atividade.created_at,
    )


def _pode_ver(atividade: Atividade, current_user: User) -> None:
    if current_user.is_superuser:
        _mesma_familia(atividade, current_user)
        return
    if atividade.aluno_id == current_user.id:
        return
    if (
        (atividade.tipo or "atividade") == "comunicado"
        and not current_user.is_child
        and current_user.family_id is not None
        and atividade.family_id == current_user.family_id
    ):
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")


def _tipo_valido(tipo: Optional[str]) -> str:
    valor = tipo or "atividade"
    if valor not in TIPOS_ESTUDO:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo deve ser atividade ou comunicado.")
    return valor


def _aplicar_conteudo(atividade: Atividade, payload: AtividadeCreate | AtividadeUpdate, aluno: User) -> None:
    tipo = _tipo_valido(payload.tipo)
    if tipo == "atividade" and payload.prazo_entrega is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Prazo de entrega é obrigatório.")
    atividade.aluno_id = aluno.id
    atividade.family_id = aluno.family_id
    atividade.titulo = payload.titulo.strip()
    atividade.descricao = payload.descricao or ""
    atividade.professor = (payload.professor or "").strip()
    atividade.data = payload.data
    atividade.tipo = tipo
    atividade.autor = (payload.autor or "").strip() or None
    atividade.numero = (payload.numero or "").strip() or None
    atividade.aluno = aluno
    if tipo == "comunicado":
        atividade.prazo_entrega = None
        atividade.disciplina = None
        atividade.status = None
        atividade.concluida_em = None
        return
    atividade.prazo_entrega = payload.prazo_entrega
    atividade.disciplina = (payload.disciplina or "").strip()
    if atividade.status not in {"pendente", "concluida"}:
        atividade.status = "pendente"


def _destinatarios(db: Session, payload: AtividadeCreate, current_user: User) -> list[User]:
    ids: list[int] = []
    if payload.aluno_ids:
        ids.extend(payload.aluno_ids)
    if payload.aluno_id:
        ids.append(payload.aluno_id)
    unicos = list(dict.fromkeys(ids))
    if not unicos:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Selecione ao menos um filho.")
    if _tipo_valido(payload.tipo) == "atividade" and len(unicos) > 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Atividade é de um filho só.")
    return [_filho_ativo(db, aluno_id, current_user) for aluno_id in unicos]


def _anexo_valido(nome: str, conteudo: bytes, content_type: str) -> str:
    extensao = PurePath(nome).suffix.lower()
    tipo = TIPOS_ANEXO.get(extensao)
    if tipo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie uma imagem PNG, JPG ou um PDF.",
        )
    informado = (content_type or "").split(";")[0].strip().lower()
    if informado in {"image/jpg", "image/pjpeg"}:
        informado = "image/jpeg"
    if informado and informado not in {"application/octet-stream", "binary/octet-stream"} and informado != tipo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie uma imagem PNG, JPG ou um PDF.",
        )
    png = conteudo.startswith(b"\x89PNG\r\n\x1a\n")
    jpeg = conteudo.startswith(b"\xff\xd8\xff")
    pdf = conteudo.startswith(b"%PDF")
    if tipo == "image/png" and not png:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O arquivo não é um PNG válido.")
    if tipo == "image/jpeg" and not jpeg:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O arquivo não é um JPG válido.")
    if tipo == "application/pdf" and not pdf:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O arquivo não é um PDF válido.")
    return tipo


def _ghostscript() -> Optional[str]:
    return shutil.which("gs") or shutil.which("gswin64c") or shutil.which("gswin32c")


def _comprimir_pdf_pymupdf(conteudo: bytes) -> bytes:
    import fitz

    documento = fitz.open(stream=conteudo, filetype="pdf")
    try:
        reduzido = documento.tobytes(garbage=4, deflate=True, clean=True)
    finally:
        documento.close()
    if not reduzido.startswith(b"%PDF") or len(reduzido) >= len(conteudo):
        return conteudo
    return reduzido


def _comprimir_pdf(conteudo: bytes) -> bytes:
    executavel = _ghostscript()
    if not executavel:
        return _comprimir_pdf_pymupdf(conteudo)
    with tempfile.TemporaryDirectory() as pasta:
        origem = Path(pasta) / "origem.pdf"
        destino = Path(pasta) / "destino.pdf"
        origem.write_bytes(conteudo)
        comando = [
            executavel,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={destino}",
            str(origem),
        ]
        try:
            subprocess.run(comando, check=True, timeout=180, capture_output=True)
        except (subprocess.SubprocessError, OSError):
            return conteudo
        if not destino.is_file():
            return conteudo
        reduzido = destino.read_bytes()
    if not reduzido.startswith(b"%PDF") or len(reduzido) >= len(conteudo):
        return conteudo
    return reduzido


def _comprimir_imagem(conteudo: bytes, tipo: str) -> bytes:
    from PIL import Image

    imagem = Image.open(io.BytesIO(conteudo))
    imagem.load()
    maior = max(imagem.size)
    if maior > LADO_MAXIMO_IMAGEM:
        escala = LADO_MAXIMO_IMAGEM / maior
        novo = (max(1, int(imagem.width * escala)), max(1, int(imagem.height * escala)))
        imagem = imagem.resize(novo, Image.Resampling.LANCZOS)
    saida = io.BytesIO()
    if tipo == "image/png":
        imagem.save(saida, format="PNG", optimize=True)
    else:
        if imagem.mode not in ("RGB", "L"):
            imagem = imagem.convert("RGB")
        imagem.save(saida, format="JPEG", quality=80, optimize=True)
    reduzido = saida.getvalue()
    if not reduzido or len(reduzido) >= len(conteudo):
        return conteudo
    return reduzido


def _reduzir_se_grande(conteudo: bytes, tipo: str) -> bytes:
    if len(conteudo) <= LIMITE_COMPRIMIR:
        return conteudo
    if tipo == "application/pdf":
        return _comprimir_pdf(conteudo)
    if tipo.startswith("image/"):
        return _comprimir_imagem(conteudo, tipo)
    return conteudo


def _nome_arquivo(nome: str) -> str:
    limpo = PurePath(nome or "imagem").name.replace('"', "").strip()
    return (limpo or "imagem")[:150]


def _mesma_familia(atividade: Atividade, current_user: User) -> None:
    if current_user.is_superuser and atividade.family_id != current_user.family_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")


def _filho_ativo(db: Session, aluno_id: int, current_user: User) -> User:
    aluno = db.query(User).filter(User.id == aluno_id).first()
    if aluno is None or not aluno.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filho não encontrado ou inativo.",
        )
    if aluno.is_superuser or not aluno.is_child:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A atividade precisa ser de um usuário marcado como filho.",
        )
    if not aluno.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O filho não tem família associada.",
        )
    if aluno.family_id != current_user.family_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esse filho pertence a outra família.",
        )
    return aluno


def _get_or_404(db: Session, atividade_id: int) -> Atividade:
    atividade = (
        db.query(Atividade)
        .options(joinedload(Atividade.aluno), defer(Atividade.anexos))
        .filter(Atividade.id == atividade_id)
        .first()
    )
    if atividade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Atividade não encontrada.")
    return atividade


def _hoje_local() -> date:
    return datetime.now(timezone(timedelta(hours=-3))).date()


def _filtrar_texto(query, termo: str):
    like = f"%{termo.strip()}%"
    return query.filter(or_(
        Atividade.titulo.ilike(like),
        Atividade.descricao.ilike(like),
        Atividade.autor.ilike(like),
        Atividade.numero.ilike(like),
        Atividade.aluno.has(or_(
            User.first_name.ilike(like),
            User.last_name.ilike(like),
            User.username.ilike(like),
        )),
    ))


def _pagina_anterior(query, antes_de: Optional[date], antes_id: Optional[int]):
    if antes_de is None or antes_id is None:
        return query
    return query.filter(or_(
        Atividade.data < antes_de,
        and_(Atividade.data == antes_de, Atividade.id < antes_id),
    ))


@router.get("/atividades", response_model=List[AtividadeSchema])
async def list_atividades(
    response: Response,
    aluno_id: Optional[int] = None,
    tipo: Optional[str] = None,
    anteriores: int = Query(0),
    q: Optional[str] = None,
    limite: int = Query(20, ge=1, le=50),
    antes_de: Optional[date] = None,
    antes_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista atividades. Aceita Bearer ou header X-API-Token.

    O filho recebe somente as próprias. O administrador recebe as da
    própria família e pode filtrar com o parâmetro aluno_id.
    Comunicado recente volta só das últimas duas semanas. Os mais antigos
    e a pesquisa vêm em páginas.
    """
    if tipo is not None:
        tipo = _tipo_valido(tipo)
    query = db.query(Atividade).options(joinedload(Atividade.aluno), defer(Atividade.anexos))
    if current_user.is_superuser:
        query = query.filter(Atividade.family_id == current_user.family_id)
        if aluno_id is not None:
            query = query.filter(Atividade.aluno_id == aluno_id)
    elif current_user.is_child:
        query = query.filter(Atividade.aluno_id == current_user.id)
    else:
        query = query.filter(or_(
            Atividade.aluno_id == current_user.id,
            and_(Atividade.tipo == "comunicado", Atividade.family_id == current_user.family_id),
        ))
    if tipo is not None:
        query = query.filter(Atividade.tipo == tipo)
    if tipo != "comunicado":
        atividades = query.order_by(Atividade.prazo_entrega.asc(), Atividade.id.asc()).all()
        return [_to_schema(item, incluir_anexos=False) for item in atividades]

    termo = (q or "").strip()
    corte = _hoje_local() - timedelta(days=DIAS_COMUNICADO_RECENTE)
    if termo:
        query = _filtrar_texto(query, termo)
        response.headers["X-Tem-Anteriores"] = "0"
    elif anteriores:
        query = query.filter(Atividade.data < corte)
        response.headers["X-Tem-Anteriores"] = "1"
    else:
        tem_anteriores = query.filter(Atividade.data < corte).first() is not None
        response.headers["X-Tem-Anteriores"] = "1" if tem_anteriores else "0"
        query = query.filter(Atividade.data >= corte)
    query = _pagina_anterior(query, antes_de, antes_id)
    query = query.order_by(Atividade.data.desc(), Atividade.id.desc())
    if termo or anteriores:
        linhas = query.limit(limite + 1).all()
        response.headers["X-Tem-Mais"] = "1" if len(linhas) > limite else "0"
        atividades = linhas[:limite]
    else:
        response.headers["X-Tem-Mais"] = "0"
        atividades = query.all()
    return [_to_schema(item, incluir_anexos=False) for item in atividades]


@router.get("/atividades/{atividade_id}", response_model=AtividadeSchema)
async def read_atividade(
    atividade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalhe de uma atividade. O filho só abre a própria. Comunicado também abre para os pais da família."""
    atividade = _get_or_404(db, atividade_id)
    _pode_ver(atividade, current_user)
    return _to_schema(atividade, resumo=_garantir_arquivos(atividade, db))


@router.get("/atividades/{atividade_id}/anexos/{idx}/link")
async def link_anexo(
    atividade_id: int,
    idx: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Endereço curto para o navegador abrir o arquivo direto, sem baixar tudo antes."""
    atividade = _get_or_404(db, atividade_id)
    _pode_ver(atividade, current_user)
    resumo = _garantir_arquivos(atividade, db)
    if idx < 0 or idx >= len(resumo):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Anexo {idx} não encontrado.")
    exp = int(time.time()) + LINK_SEGUNDOS
    sig = _assinar(atividade_id, idx, exp)
    return {
        "url": f"{settings.API_V1_STR}/estudos/atividades/{atividade_id}/anexos/{idx}/download?exp={exp}&sig={sig}",
    }


@router.post("/atividades/{atividade_id}/anexos", response_model=AtividadeSchema)
async def adicionar_anexo(
    atividade_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Anexa uma imagem PNG, JPG ou um PDF. Somente administrador, via multipart no campo file."""
    atividade = _get_or_404(db, atividade_id)
    _mesma_familia(atividade, current_user)
    conteudo = await file.read()
    if not conteudo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O arquivo está vazio.")
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="O arquivo passa de 25 MB.")
    tipo = _anexo_valido(file.filename or "", conteudo, file.content_type or "")
    conteudo = _reduzir_se_grande(conteudo, tipo)
    tipo = _anexo_valido(file.filename or "", conteudo, tipo)
    resumo = list(_garantir_arquivos(atividade, db))
    anexos = _carregar_anexos(atividade)
    if len(anexos) >= LIMITE_ANEXOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Essa atividade já tem 10 anexos.")
    chave = _gravar_cache(conteudo)
    meta = {
        "name": _nome_arquivo(file.filename or "imagem"),
        "type": tipo,
        "size": len(conteudo),
        "arquivo": chave,
    }
    anexos.append({**meta, "data": base64.b64encode(conteudo).decode("ascii")})
    atividade.anexos = json.dumps(anexos)
    resumo.append(meta)
    atividade.anexos_resumo = json.dumps(resumo)
    db.commit()
    db.refresh(atividade)
    return _to_schema(atividade, resumo=resumo)


@router.get("/atividades/{atividade_id}/anexos/{idx}/download")
async def baixar_anexo(
    atividade_id: int,
    idx: int,
    exp: Optional[int] = Query(None),
    sig: Optional[str] = Query(None),
    inline: int = Query(0),
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
    api_key: Optional[str] = Security(api_key_header),
):
    """Entrega o arquivo para o navegador abrir. Aceita o link assinado ou Bearer / X-API-Token."""
    atividade = _get_or_404(db, atividade_id)
    if not _link_valido(atividade_id, idx, exp, sig):
        current_user = await get_current_user(token=token, api_key=api_key, db=db)
        _pode_ver(atividade, current_user)
    resumo = _garantir_arquivos(atividade, db)
    if idx < 0 or idx >= len(resumo):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Anexo {idx} não encontrado.")
    item = resumo[idx]
    caminho = PASTA_ANEXOS / str(item["arquivo"])
    if not caminho.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conteúdo do anexo não encontrado.")
    return FileResponse(
        caminho,
        media_type=str(item.get("type") or "application/octet-stream"),
        filename=str(item.get("name") or "anexo"),
        content_disposition_type="inline" if inline else "attachment",
    )


@router.delete("/atividades/{atividade_id}/anexos/{idx}", response_model=AtividadeSchema)
async def excluir_anexo(
    atividade_id: int,
    idx: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Remove uma imagem da atividade. Somente administrador."""
    atividade = _get_or_404(db, atividade_id)
    _mesma_familia(atividade, current_user)
    anexos = _carregar_anexos(atividade)
    if idx < 0 or idx >= len(anexos):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Anexo {idx} não encontrado.")
    del anexos[idx]
    atividade.anexos = json.dumps(anexos) if anexos else None
    resumo = _ler_resumo(atividade)
    if 0 <= idx < len(resumo):
        del resumo[idx]
    atividade.anexos_resumo = json.dumps(resumo) if resumo else None
    db.commit()
    db.refresh(atividade)
    return _to_schema(atividade, resumo=resumo)


@router.post("/atividades", response_model=AtividadeSchema, status_code=status.HTTP_201_CREATED)
async def create_atividade(
    payload: AtividadeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """Cria uma atividade para um filho. Somente administrador, via Bearer ou X-API-Token."""
    if not payload.titulo.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Título é obrigatório.")
    alunos = _destinatarios(db, payload, current_user)
    criadas = []
    for aluno in alunos:
        atividade = Atividade(created_by_id=current_user.id, status="pendente")
        _aplicar_conteudo(atividade, payload, aluno)
        db.add(atividade)
        criadas.append(atividade)
    db.commit()
    for atividade in criadas:
        db.refresh(atividade)
    return _to_schema(criadas[0])


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
    _mesma_familia(atividade, current_user)
    aluno = _filho_ativo(db, payload.aluno_id, current_user)
    _aplicar_conteudo(atividade, payload, aluno)
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
    if (atividade.tipo or "atividade") == "comunicado":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comunicado não tem conclusão.")
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
    from app.services.whatsapp import avisar_atividade_concluida
    try:
        await avisar_atividade_concluida(db, atividade)
    except Exception:
        import logging
        logging.getLogger(__name__).warning("Falha ao avisar o WhatsApp da atividade %s", atividade.id, exc_info=True)
    return _to_schema(atividade)


@router.post("/atividades/{atividade_id}/reabrir", response_model=AtividadeSchema)
async def reabrir_atividade(
    atividade_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    """O administrador devolve a atividade para pendente. Aceita Bearer ou X-API-Token."""
    atividade = _get_or_404(db, atividade_id)
    _mesma_familia(atividade, current_user)
    if (atividade.tipo or "atividade") == "comunicado":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comunicado não pode voltar para pendente.")
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
    _mesma_familia(atividade, current_user)
    db.delete(atividade)
    db.commit()
    return {"message": "Atividade excluída com sucesso"}


from app.api.v1.endpoints.provas import router as provas_router

router.include_router(provas_router)
