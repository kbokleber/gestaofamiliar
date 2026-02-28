"""
Utilitários para redimensionar imagens (ex.: thumbnails para listas).
Reduz payload em mobile quando fotos são exibidas em tamanho pequeno.
"""
import base64
import logging
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def resize_photo_base64(
    b64: str,
    max_size: int = 200,
    quality: int = 78,
) -> Optional[str]:
    """
    Redimensiona uma imagem em base64 para no máximo max_size pixels (maior lado).
    Aplica orientação EXIF para fotos de celular não ficarem inclinadas.
    Mantém proporção. Retorna base64 JPEG (sem prefixo data:...).
    Se Pillow não estiver instalado ou der erro, retorna o base64 original.
    """
    if not b64 or not b64.strip():
        return None
    if not PIL_AVAILABLE:
        return b64
    try:
        raw = b64
        if "," in b64:
            raw = b64.split(",", 1)[1]
        data = base64.b64decode(raw)
        img = Image.open(BytesIO(data))
        # Aplicar orientação EXIF (fotos de celular deixam de ficar "deitadas")
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        # Converter para RGB se for RGBA ou P
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        elif img.mode != "RGB":
            img = img.convert("RGB")
        w, h = img.size
        if w <= max_size and h <= max_size:
            # Já pequena o suficiente; re-encodar com qualidade para padronizar tamanho
            out = BytesIO()
            img.save(out, format="JPEG", quality=quality, optimize=True)
            out.seek(0)
            return base64.b64encode(out.getvalue()).decode("utf-8")
        ratio = min(max_size / w, max_size / h)
        new_w = max(1, int(w * ratio))
        new_h = max(1, int(h * ratio))
        try:
            resampler = Image.Resampling.LANCZOS
        except AttributeError:
            resampler = Image.LANCZOS
        resized = img.resize((new_w, new_h), resampler)
        out = BytesIO()
        resized.save(out, format="JPEG", quality=quality, optimize=True)
        out.seek(0)
        return base64.b64encode(out.getvalue()).decode("utf-8")
    except Exception as e:
        logger.warning("resize_photo_base64 failed: %s", e)
        return b64
