"""Teste de ponta a ponta do GlitchTip. Só existe com GF_SENTRY_TESTE=1 e só para administrador.

Como desligar e como remover: docs/monitoramento-erros-glitchtip.md, seção "Teste em produção".
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin
from app.core.monitoramento import ErroDeTesteGlitchTip
from app.core.version import get_app_version_info

router = APIRouter(dependencies=[Depends(get_current_admin)], include_in_schema=False)


@router.get("/teste-glitchtip")
async def situacao_do_teste():
    """Diz ao site que o teste está ligado. Não gera erro."""
    return {"ligado": True, "commit": get_app_version_info()["commit"]}


@router.post("/teste-glitchtip")
async def gerar_erro_de_teste():
    """Erro de verdade, não tratado: passa pelo mesmo caminho de qualquer falha do sistema (responde 500)."""
    raise ErroDeTesteGlitchTip()
