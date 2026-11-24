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
    from PIL import EpsImagePlugin, Image, ImageOps
    PIL_AVAILABLE = True
    # O Pillow chama o Ghostscript para abrir EPS. Nenhuma tela usa EPS, então fica desligado no processo
    # inteiro (vale também para quem abre imagem em outros módulos). A compressão de PDF não passa por aqui.
    EpsImagePlugin.gs_binary = False
except ImportError:
    PIL_AVAILABLE = False

FORMATOS_ACEITOS = ("JPEG", "PNG", "WEBP", "GIF")
# O JPEG é aberto já reduzido (draft), então aguenta foto de celular de 64 MP. Os outros abrem inteiros.
MAX_PIXELS_JPEG = 65_000_000
MAX_PIXELS_OUTROS = 25_000_000


def abrir_imagem(dados: bytes, lado_desejado: int) -> "Image.Image":
    """Abre só JPEG, PNG, WebP e GIF, e confere o tamanho ANTES de descompactar. ValueError/OSError se recusar."""
    img = Image.open(BytesIO(dados), formats=FORMATOS_ACEITOS)
    # MPO é o JPEG de alguns celulares (duas fotos no mesmo arquivo); vale a primeira.
    jpeg = img.format in ("JPEG", "MPO")
    pixels = img.width * img.height
    if pixels > (MAX_PIXELS_JPEG if jpeg else MAX_PIXELS_OUTROS):
        raise ValueError(f"imagem grande demais ({img.width}x{img.height})")
    if jpeg:
        img.draft("RGB", (lado_desejado * 2, lado_desejado * 2))
    return img


def sem_metadados(img: "Image.Image") -> "Image.Image":
    """Só os pixels, em RGB: sem comentário, EXIF, XMP, ICC nem texto do PNG."""
    limpa = Image.new("RGB", img.size)
    limpa.paste(img if img.mode == "RGB" else img.convert("RGB"))
    return limpa


def resize_photo_base64(
    b64: str,
    max_size: int = 200,
    quality: int = 78,
) -> Optional[str]:
    """
    Redimensiona uma imagem em base64 para no máximo max_size pixels (maior lado).
    Aplica orientação EXIF para fotos de celular não ficarem inclinadas.
    Mantém proporção. Retorna base64 JPEG (sem prefixo data:...), sem metadados.
    Se Pillow não estiver instalado, o formato não for aceito ou der erro, retorna o base64 original.
    """
    if not b64 or not b64.strip():
        return None
    if not PIL_AVAILABLE:
        return b64
    try:
        raw = b64
        if "," in b64:
            raw = b64.split(",", 1)[1]
        img = abrir_imagem(base64.b64decode(raw), max_size)
        if img.mode in ("P", "1"):  # paleta: sem isto a redução perde qualidade
            img = img.convert("RGB")
        # Reduz antes de girar e converter: gasta menos memória.
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        # Aplicar orientação EXIF (fotos de celular deixam de ficar "deitadas")
        try:
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        out = BytesIO()
        sem_metadados(img).save(out, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(out.getvalue()).decode("utf-8")
    except Exception as e:
        logger.warning("resize_photo_base64 failed: %s", e)
        return b64
