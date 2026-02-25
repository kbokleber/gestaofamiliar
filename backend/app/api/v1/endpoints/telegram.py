"""
Endpoints para configurar Telegram e IA por família, e para cada usuário vincular seu Telegram e preferência de IA.
Inclui webhook que recebe mensagens do Telegram e responde usando a IA configurada da família.
"""
import logging
import secrets
import string
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import get_db
from app.models.user import User
from app.models.telegram import (
    FamilyTelegramConfig,
    FamilyAIConfig,
    TelegramUserLink,
    TelegramLinkCode,
)
from app.schemas.telegram import (
    FamilyBotConfigResponse,
    FamilyBotConfigUpdate,
    FamilyAIConfigResponse,
    FamilyAIConfigUpdate,
    TelegramMeResponse,
    TelegramLinkCodeResponse,
    TelegramUpdatePreferences,
)
from app.api.deps import get_current_user, get_current_family, get_user_family_ids
from app.telegram.ai_service import process_message_with_ai, _fallback_response

logger = logging.getLogger(__name__)

router = APIRouter()


def _ai_available_for_family(family_id: Optional[int], db: Session) -> bool:
    """Verifica se a família tem IA configurada e ativa."""
    if not family_id:
        return False
    cfg = db.query(FamilyAIConfig).filter(FamilyAIConfig.family_id == family_id).first()
    if not cfg or not cfg.enabled or cfg.provider == "none":
        return False
    if cfg.provider == "openai" and cfg.openai_api_key:
        return True
    if cfg.provider == "azure" and cfg.azure_endpoint and cfg.azure_api_key:
        return True
    return False


def _get_bot_username_for_family(family_id: Optional[int], db: Session) -> Optional[str]:
    """Retorna o @username do bot da família (cache em FamilyTelegramConfig)."""
    if not family_id:
        return None
    cfg = db.query(FamilyTelegramConfig).filter(FamilyTelegramConfig.family_id == family_id).first()
    return cfg.bot_username if cfg else None


# ---------- Configuração da família (bot + IA) ----------


@router.get("/family/bot", response_model=FamilyBotConfigResponse)
async def get_family_bot_config(
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family),
    db: Session = Depends(get_db),
):
    """Retorna se a família tem bot Telegram configurado (token nunca é retornado)."""
    if family_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você precisa pertencer a uma família para configurar o bot.",
        )
    cfg = db.query(FamilyTelegramConfig).filter(FamilyTelegramConfig.family_id == family_id).first()
    return FamilyBotConfigResponse(
        configured=cfg is not None and bool(cfg.bot_token),
        bot_username=cfg.bot_username if cfg else None,
    )


@router.put("/family/bot", response_model=FamilyBotConfigResponse)
async def update_family_bot_config(
    data: FamilyBotConfigUpdate,
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family),
    db: Session = Depends(get_db),
):
    """Define ou atualiza o token do bot Telegram da família. Persistido na tabela family_telegram_config."""
    if family_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você precisa pertencer a uma família para configurar o bot.",
        )
    cfg = db.query(FamilyTelegramConfig).filter(FamilyTelegramConfig.family_id == family_id).first()
    if not cfg:
        cfg = FamilyTelegramConfig(family_id=family_id, bot_token=data.bot_token)
        db.add(cfg)
    else:
        cfg.bot_token = data.bot_token
        cfg.bot_username = None  # recarregar com getMe

    # Atualizar cache do username do bot
    try:
        r = httpx.get(
            f"https://api.telegram.org/bot{data.bot_token}/getMe",
            timeout=5.0,
        )
        if r.status_code == 200:
            body = r.json()
            if body.get("ok") and body.get("result", {}).get("username"):
                cfg.bot_username = f"@{body['result']['username']}"
    except Exception:
        pass

    # Registrar webhook se tiver URL pública
    if getattr(settings, "BACKEND_PUBLIC_URL", None):
        base = settings.BACKEND_PUBLIC_URL.rstrip("/")
        webhook_url = f"{base}{settings.API_V1_STR}/telegram/webhook/{family_id}"
        try:
            httpx.post(
                f"https://api.telegram.org/bot{data.bot_token}/setWebhook",
                json={"url": webhook_url},
                timeout=10.0,
            )
        except Exception:
            pass

    db.commit()
    db.refresh(cfg)
    return FamilyBotConfigResponse(configured=True, bot_username=cfg.bot_username)


@router.get("/family/ai", response_model=FamilyAIConfigResponse)
async def get_family_ai_config(
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family),
    db: Session = Depends(get_db),
):
    """Retorna a config de IA da família (chaves nunca são retornadas)."""
    if family_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você precisa pertencer a uma família para configurar a IA.",
        )
    cfg = db.query(FamilyAIConfig).filter(FamilyAIConfig.family_id == family_id).first()
    if not cfg:
        return FamilyAIConfigResponse(
            enabled=True,
            provider="openai",
            openai_model="gpt-4o-mini",
            has_openai_key=False,
            has_azure_config=False,
        )
    return FamilyAIConfigResponse(
        enabled=cfg.enabled,
        provider=cfg.provider or "openai",
        openai_model=cfg.openai_model,
        has_openai_key=bool(cfg.openai_api_key),
        has_azure_config=bool(cfg.azure_endpoint and cfg.azure_api_key),
    )


@router.put("/family/ai", response_model=FamilyAIConfigResponse)
async def update_family_ai_config(
    data: FamilyAIConfigUpdate,
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family),
    db: Session = Depends(get_db),
):
    """Atualiza a config de IA da família. Persistido na tabela family_ai_config (enabled, provider, chaves, modelo)."""
    if family_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você precisa pertencer a uma família para configurar a IA.",
        )
    cfg = db.query(FamilyAIConfig).filter(FamilyAIConfig.family_id == family_id).first()
    if not cfg:
        cfg = FamilyAIConfig(
            family_id=family_id,
            enabled=data.enabled if data.enabled is not None else True,
            provider=data.provider or "openai",
            openai_model=data.openai_model or "gpt-4o-mini",
        )
        db.add(cfg)
    else:
        if data.enabled is not None:
            cfg.enabled = data.enabled
        if data.provider is not None:
            cfg.provider = data.provider
        if data.openai_model is not None:
            cfg.openai_model = data.openai_model
        if data.openai_api_key is not None:
            cfg.openai_api_key = (data.openai_api_key or "").strip() or None
        if data.azure_endpoint is not None:
            cfg.azure_endpoint = (data.azure_endpoint or "").strip() or None
        if data.azure_api_key is not None:
            cfg.azure_api_key = (data.azure_api_key or "").strip() or None
        if data.azure_deployment is not None:
            cfg.azure_deployment = (data.azure_deployment or "").strip() or None

    db.commit()
    db.refresh(cfg)
    return FamilyAIConfigResponse(
        enabled=cfg.enabled,
        provider=cfg.provider or "openai",
        openai_model=cfg.openai_model,
        has_openai_key=bool(cfg.openai_api_key),
        has_azure_config=bool(cfg.azure_endpoint and cfg.azure_api_key),
    )


# ---------- Vínculo do usuário (meu Telegram + preferência IA) ----------


@router.get("/me", response_model=TelegramMeResponse)
async def get_telegram_status(
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family),
    db: Session = Depends(get_db),
):
    """Retorna se o usuário tem Telegram vinculado e a preferência de IA. IA disponível = config da família."""
    link = db.query(TelegramUserLink).filter(TelegramUserLink.user_id == current_user.id).first()
    return TelegramMeResponse(
        linked=link is not None,
        telegram_username=link.telegram_username if link else None,
        use_ai=link.use_ai if link else True,
        ai_available=_ai_available_for_family(family_id, db),
    )


@router.post("/link", response_model=TelegramLinkCodeResponse)
async def generate_telegram_link_code(
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family),
    db: Session = Depends(get_db),
):
    """Gera código para vincular a conta ao bot da família. No Telegram: /start CODIGO"""
    if family_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você precisa pertencer a uma família. Configure o bot da família primeiro.",
        )
    cfg = db.query(FamilyTelegramConfig).filter(FamilyTelegramConfig.family_id == family_id).first()
    if not cfg or not cfg.bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A família ainda não configurou o bot do Telegram. Configure em Configurações > Telegram e IA.",
        )

    alphabet = string.ascii_uppercase + string.digits
    code = "".join(secrets.choice(alphabet) for _ in range(8))
    while db.query(TelegramLinkCode).filter(TelegramLinkCode.code == code).first():
        code = "".join(secrets.choice(alphabet) for _ in range(8))

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    link_code = TelegramLinkCode(code=code, user_id=current_user.id, expires_at=expires_at)
    db.add(link_code)
    db.commit()

    bot_username = cfg.bot_username
    if not bot_username and cfg.bot_token:
        try:
            r = httpx.get(
                f"https://api.telegram.org/bot{cfg.bot_token}/getMe",
                timeout=5.0,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("ok") and data.get("result", {}).get("username"):
                    bot_username = f"@{data['result']['username']}"
        except Exception:
            pass

    return TelegramLinkCodeResponse(
        code=code,
        expires_at=expires_at,
        bot_username=bot_username,
    )


@router.put("/me", response_model=TelegramMeResponse)
async def update_telegram_preferences(
    data: TelegramUpdatePreferences,
    current_user: User = Depends(get_current_user),
    family_id: Optional[int] = Depends(get_current_family),
    db: Session = Depends(get_db),
):
    """Atualiza a preferência de usar IA nas mensagens do Telegram."""
    link = db.query(TelegramUserLink).filter(TelegramUserLink.user_id == current_user.id).first()
    if not link:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vincule seu Telegram antes de alterar preferências.",
        )
    link.use_ai = data.use_ai
    db.commit()
    db.refresh(link)
    return TelegramMeResponse(
        linked=True,
        telegram_username=link.telegram_username,
        use_ai=link.use_ai,
        ai_available=_ai_available_for_family(family_id, db),
    )


@router.delete("/unlink", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_telegram(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove o vínculo da conta com o Telegram."""
    link = db.query(TelegramUserLink).filter(TelegramUserLink.user_id == current_user.id).first()
    if link:
        db.delete(link)
        db.commit()
    return None


# ---------- Webhook (Telegram envia as mensagens aqui; sem autenticação JWT) ----------


def _send_telegram_message(bot_token: str, chat_id: int, text: str) -> None:
    """Envia texto ao chat via API do Telegram. Trunca se exceder limite."""
    max_len = 4096
    if len(text) > max_len:
        text = text[: max_len - 50] + "\n\n[... resposta truncada]"
    try:
        httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15.0,
        )
    except Exception as e:
        logger.exception("Erro ao enviar mensagem ao Telegram: %s", e)


@router.post("/webhook/{family_id}")
async def telegram_webhook(
    family_id: int,
    update: dict[str, Any],
    db: Session = Depends(get_db),
):
    """
    Recebe atualizações do Telegram para o bot da família.
    Telegram chama este endpoint quando alguém envia mensagem ao bot.
    Responde usando a IA configurada da família (OpenAI/Azure) quando disponível.
    """
    cfg = db.query(FamilyTelegramConfig).filter(FamilyTelegramConfig.family_id == family_id).first()
    if not cfg or not cfg.bot_token:
        return {"ok": True}

    message = (update.get("message") or update.get("edited_message")) if isinstance(update, dict) else None
    if not message or not isinstance(message, dict):
        return {"ok": True}

    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    chat_id = chat.get("id")
    telegram_user_id = from_user.get("id")
    text = (message.get("text") or "").strip()

    if chat_id is None or telegram_user_id is None:
        return {"ok": True}

    def reply(msg: str) -> None:
        _send_telegram_message(cfg.bot_token, chat_id, msg)

    # /start [CODIGO] — vincular conta ou boas-vindas
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        code_str = parts[1].strip() if len(parts) > 1 else None
        if code_str:
            link_code = (
                db.query(TelegramLinkCode)
                .filter(
                    TelegramLinkCode.code == code_str.upper(),
                    TelegramLinkCode.expires_at > datetime.now(timezone.utc),
                )
                .first()
            )
            if link_code:
                existing = db.query(TelegramUserLink).filter(
                    TelegramUserLink.telegram_user_id == telegram_user_id
                ).first()
                if existing:
                    db.delete(existing)
                    db.commit()
                username = from_user.get("username")
                link = TelegramUserLink(
                    user_id=link_code.user_id,
                    telegram_user_id=telegram_user_id,
                    telegram_chat_id=chat_id,
                    telegram_username=f"@{username}" if username else None,
                    use_ai=True,
                )
                db.add(link)
                db.delete(link_code)
                db.commit()
                reply("Conta vinculada com sucesso. Pode perguntar sobre sua família (equipamentos, consultas, medicações, etc.). Use /ajuda para comandos.")
            else:
                reply("Código inválido ou expirado. Gere um novo no site em Configurações > Telegram e IA.")
        else:
            link = db.query(TelegramUserLink).filter(TelegramUserLink.telegram_user_id == telegram_user_id).first()
            if link:
                reply("Você já está vinculado. Envie uma mensagem ou use /ajuda.")
            else:
                reply("Para vincular sua conta, use no site: Configurações > Telegram e IA > Vincular. Depois envie /start CODIGO aqui.")
        return {"ok": True}

    # /ajuda
    if text == "/ajuda" or text == "/help":
        link = db.query(TelegramUserLink).filter(TelegramUserLink.telegram_user_id == telegram_user_id).first()
        ai_on = _ai_available_for_family(family_id, db) and (link.use_ai if link else True)
        help_text = (
            "Comandos:\n"
            "/start — vincular conta ou ver status\n"
            "/ajuda — esta mensagem\n\n"
            "Você pode perguntar em texto livre sobre: resumo da família, equipamentos, consultas, medicações, ordens de manutenção."
        )
        if not ai_on:
            help_text += "\n\nPara respostas com IA, ative e configure a API (OpenAI ou Azure) em Administração > Famílias > Editar família."
        reply(help_text)
        return {"ok": True}

    # Mensagem normal: identificar usuário e responder com IA se configurada
    link = db.query(TelegramUserLink).filter(TelegramUserLink.telegram_user_id == telegram_user_id).first()
    if not link:
        reply("Vincule sua conta primeiro. No site: Configurações > Telegram e IA > Vincular. Depois envie /start CODIGO aqui.")
        return {"ok": True}

    user = db.query(User).filter(User.id == link.user_id).first()
    if not user:
        reply("Conta não encontrada. Vincule novamente pelo site.")
        return {"ok": True}

    # Verificar se o usuário pertence a esta família (admin pode estar em várias)
    user_family_ids = get_user_family_ids(user, db)
    if family_id not in user_family_ids:
        reply("Sua conta não está nesta família. Use o bot da família em que você está cadastrado.")
        return {"ok": True}

    if not text:
        reply("Envie uma mensagem de texto ou use /ajuda.")
        return {"ok": True}

    # Usar IA da família se estiver configurada e usuário preferir
    if link.use_ai and _ai_available_for_family(family_id, db):
        try:
            response_text = process_message_with_ai(text, user, db)
            reply(response_text)
        except Exception as e:
            logger.exception("Erro ao processar mensagem com IA")
            reply(f"Erro ao processar. Tente de novo ou use /ajuda. ({str(e)[:80]})")
    else:
        reply(_fallback_response())

    return {"ok": True}
