"""Download público do app Android da criança e envio de nova versão (só admin).

O APK não fica no git: um admin envia pelo site e o servidor guarda no banco.
"""
import hashlib
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session, defer

from app.api.deps import get_current_admin, get_db
from app.models.app_android import AppAndroid
from app.models.user import User

router = APIRouter()

TAMANHO_MAXIMO = 50 * 1024 * 1024
VERSOES_GUARDADAS = 3
VERSAO_VALIDA = re.compile(r"^\d+(\.\d+){0,3}$")


def _info(app: AppAndroid) -> dict:
    criado = app.created_at
    if criado is not None and criado.tzinfo is None:
        criado = criado.replace(tzinfo=timezone.utc)
    return {
        "versao": app.versao,
        "tamanho_bytes": app.tamanho_bytes,
        "sha256": app.sha256,
        "publicado_em": criado.isoformat() if criado else None,
        "arquivo": "/api/v1/app-android/download",
    }


def _ultima(db: Session, com_conteudo: bool = False):
    consulta = db.query(AppAndroid)
    if not com_conteudo:
        consulta = consulta.options(defer(AppAndroid.conteudo))
    return consulta.order_by(AppAndroid.id.desc()).first()


@router.get("/ultima")
def ultima_versao(db: Session = Depends(get_db)):
    """Versão disponível para download. Público: o celular da criança não precisa de login."""
    app = _ultima(db)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma versão do app foi enviada ainda.")
    return _info(app)


@router.get("/download")
def baixar(db: Session = Depends(get_db)):
    app = _ultima(db, com_conteudo=True)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nenhuma versão do app foi enviada ainda.")
    nome = f"GestaoFamiliar-crianca-{app.versao}.apk"
    return Response(
        content=app.conteudo,
        media_type="application/vnd.android.package-archive",
        headers={
            "Content-Disposition": f'attachment; filename="{nome}"',
            "Cache-Control": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def enviar_versao(
    versao: str = Form(...),
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """Admin envia o APK assinado de uma versão nova; ela passa a ser a baixada em /app."""
    versao = versao.strip()
    if not VERSAO_VALIDA.match(versao):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Versão inválida. Use o formato 1.0.2.")
    if not (arquivo.filename or "").lower().endswith(".apk"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Envie o arquivo .apk do app.")
    conteudo = await arquivo.read(TAMANHO_MAXIMO + 1)
    if len(conteudo) > TAMANHO_MAXIMO:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="O arquivo passa de 50 MB.")
    # Todo APK é um arquivo ZIP: começa com "PK\x03\x04".
    if not conteudo.startswith(b"PK\x03\x04"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="O arquivo não parece ser um APK.")
    novo = AppAndroid(
        versao=versao,
        tamanho_bytes=len(conteudo),
        sha256=hashlib.sha256(conteudo).hexdigest(),
        conteudo=conteudo,
        enviado_por_id=admin.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(novo)
    db.flush()
    antigos = db.query(AppAndroid.id).order_by(AppAndroid.id.desc()).offset(VERSOES_GUARDADAS).all()
    if antigos:
        db.query(AppAndroid).filter(AppAndroid.id.in_([a.id for a in antigos])).delete(synchronize_session=False)
    db.commit()
    db.refresh(novo)
    return _info(novo)
