"""Utilitário de imagem: só JPEG, PNG, WebP e GIF, sem Ghostscript, com limite de pixels e sem metadados."""
import base64
import io
import struct
import subprocess
import sys
import time
import zlib

import pytest
from PIL import Image, PngImagePlugin

from app.utils import image as u

EPS = b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 10 10\n%%EndComments\nshowpage\n"


def _b64(dados):
    return base64.b64encode(dados).decode()


def _arquivo(img, formato, **k):
    saida = io.BytesIO()
    img.save(saida, formato, **k)
    return saida.getvalue()


def _png_gigante(lado):
    """PNG pequeno em bytes que diz ter lado x lado pixels, sem gastar memória para montar."""
    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))
    c = zlib.compressobj(9)
    linha = b"\0" * (lado * 3 + 1)
    idat = b"".join(c.compress(linha) for _ in range(lado)) + c.flush()
    return b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", struct.pack(">IIBBBBB", lado, lado, 8, 2, 0, 0, 0)) + bloco(b"IDAT", idat) + bloco(b"IEND", b"")


@pytest.fixture
def nenhum_processo(monkeypatch):
    def proibido(*a, **k):
        raise AssertionError(f"chamou um processo: {a}")
    for nome in ("check_call", "check_output", "run", "Popen", "call"):
        monkeypatch.setattr(subprocess, nome, proibido)


def test_eps_nao_chama_o_ghostscript(nenhum_processo):
    for dados in (EPS, EPS.replace(b"\n", b"\r\n"), b"\xc5\xd0\xd3\xc6" + struct.pack("<I", 30) + struct.pack("<I", len(EPS)) + b"\0" * 18 + EPS):
        assert u.resize_photo_base64(_b64(dados)) == _b64(dados)  # recusado: volta o original
        with pytest.raises(Exception):
            u.abrir_imagem(dados, 144)


def test_eps_tambem_nao_passa_por_quem_abre_imagem_direto(nenhum_processo):
    """O comprovante de Finanças usa Image.open e confia no tipo que o navegador informa."""
    with pytest.raises(OSError, match="Ghostscript"):
        Image.open(io.BytesIO(EPS)).load()


def test_o_bloqueio_vale_no_app_de_verdade(tmp_path):
    codigo = "import app.main; from PIL import EpsImagePlugin as e; print('BLOQUEADO' if e.gs_binary is False and not e.has_ghostscript() else 'ABERTO')"
    import os
    from pathlib import Path
    ambiente = {**os.environ, "DATABASE_URL": "postgresql://u:p@localhost/db", "SECRET_KEY": "x", "PYTHONPATH": str(Path(__file__).resolve().parents[1])}
    r = subprocess.run([sys.executable, "-c", codigo], cwd=tmp_path, env=ambiente, capture_output=True, text=True, timeout=120)
    assert r.stdout.strip().endswith("BLOQUEADO"), r.stderr[-500:]


@pytest.mark.parametrize("nome,dados", [
    ("pdf", b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"), ("svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>"),
    ("texto", b"isto nao e imagem"), ("vazio", b"\0"),
    *[(f, None) for f in ("BMP", "TIFF", "PPM", "TGA", "ICO", "PCX", "PDF", "EPS")],
])
def test_outros_formatos_sao_recusados(nenhum_processo, nome, dados):
    dados = dados if dados is not None else _arquivo(Image.new("RGB", (32, 32), "red"), nome)
    with pytest.raises(Exception):
        u.abrir_imagem(dados, 144)
    assert u.resize_photo_base64(_b64(dados)) == _b64(dados)


@pytest.mark.parametrize("formato", ["JPEG", "PNG", "WEBP", "GIF", "MPO"])
def test_formatos_aceitos_viram_jpeg_pequeno(formato):
    menor = u.resize_photo_base64(_b64(_arquivo(Image.new("RGB", (1200, 600), "red"), formato)), max_size=144)
    img = Image.open(io.BytesIO(base64.b64decode(menor)))
    assert (img.format, img.size) == ("JPEG", (144, 72))
    r, g, b = img.getpixel((70, 30))
    assert r > 200 and g < 40 and b < 40


@pytest.mark.parametrize("modo,formato", [("RGBA", "PNG"), ("P", "GIF"), ("L", "JPEG"), ("CMYK", "JPEG"), ("LA", "PNG"), ("1", "PNG"), ("I;16", "PNG"), ("RGBA", "WEBP")])
def test_modos_de_cor(modo, formato):
    menor = u.resize_photo_base64(_b64(_arquivo(Image.new(modo, (300, 200)), formato)), max_size=100)
    assert Image.open(io.BytesIO(base64.b64decode(menor))).size == (100, 67)


def test_imagem_pequena_nao_aumenta_e_orientacao_do_celular_vale():
    assert Image.open(io.BytesIO(base64.b64decode(u.resize_photo_base64(_b64(_arquivo(Image.new("RGB", (40, 30)), "PNG")))))).size == (40, 30)
    ex = Image.Exif()
    ex[0x112] = 6
    menor = u.resize_photo_base64(_b64(_arquivo(Image.new("RGB", (1200, 600)), "JPEG", exif=ex)), max_size=144)
    assert Image.open(io.BytesIO(base64.b64decode(menor))).size == (72, 144)


def test_png_de_13000_pixels_e_recusado_na_hora_e_sem_memoria():
    import tracemalloc
    texto = _b64(_png_gigante(13_000))
    tracemalloc.start()
    inicio = time.monotonic()
    assert u.resize_photo_base64(texto) == texto
    assert time.monotonic() - inicio < 0.5
    assert tracemalloc.get_traced_memory()[1] < 20_000_000
    tracemalloc.stop()


@pytest.mark.parametrize("tamanho,formato,aceita", [
    ((5000, 5000), "PNG", True), ((5001, 5000), "PNG", False), ((5001, 5000), "GIF", False), ((5001, 5000), "WEBP", False),
    ((9248, 6936), "JPEG", True), ((9500, 7000), "JPEG", False),
])
def test_limites_de_pixels(tamanho, formato, aceita):
    dados = _arquivo(Image.new("RGB" if formato != "GIF" else "P", tamanho), formato)
    if aceita:
        assert u.abrir_imagem(dados, 144)
    else:
        with pytest.raises(ValueError, match="grande demais"):
            u.abrir_imagem(dados, 144)


SEGREDOS = [b"ComentarioSegredo", b"DescSegredo", b"XmpSegredo", b"IccSegredo", b"PngSegredo", b"GifSegredo", b"Exif", b"ICC_PROFILE", b"http://ns.adobe.com"]


def _com_metadados(formato, tamanho):
    img = Image.effect_noise(tamanho, 80).convert("RGB")
    ex = Image.Exif()
    ex[0x010E] = "DescSegredo"
    ex[0x8825] = {1: "S", 2: (23.0, 59.0, 12.0)}
    if formato == "JPEG":
        return _arquivo(img, "JPEG", exif=ex, comment=b"ComentarioSegredo", xmp=b"<x>XmpSegredo</x>", icc_profile=b"IccSegredo" * 20)
    if formato == "PNG":
        info = PngImagePlugin.PngInfo()
        for chave in ("comment", "Comment", "Description"):
            info.add_text(chave, "PngSegredo")
            info.add_itxt(chave + "i", "PngSegredo", zip=True)
        info.add_itxt("XML:com.adobe.xmp", "<x>XmpSegredo</x>")
        return _arquivo(img, "PNG", pnginfo=info, exif=ex, icc_profile=b"IccSegredo" * 20)
    if formato == "WEBP":
        return _arquivo(img, "WEBP", exif=ex, xmp=b"<x>XmpSegredo</x>", icc_profile=b"IccSegredo" * 20)
    return _arquivo(img.convert("P"), "GIF", comment=b"GifSegredo")


@pytest.mark.parametrize("formato", ["JPEG", "PNG", "WEBP", "GIF"])
@pytest.mark.parametrize("tamanho", [(1200, 900), (60, 40)])
def test_miniatura_nao_leva_nenhum_metadado(formato, tamanho):
    original = _com_metadados(formato, tamanho)
    menor = base64.b64decode(u.resize_photo_base64(_b64(original), max_size=144))
    assert [s for s in SEGREDOS if s in menor] == []
    img = Image.open(io.BytesIO(menor))
    assert set(img.info) <= {"jfif", "jfif_version", "jfif_unit", "jfif_density", "dpi"}
    assert len(img.getexif()) == 0
    # Só os blocos que todo JPEG tem: nada de COM (FE) nem APP1 a APP15 (E1 a EF).
    i = 2
    while menor[i + 1] != 0xDA:
        assert menor[i] == 0xFF and menor[i + 1] != 0xFE and not 0xE1 <= menor[i + 1] <= 0xEF, hex(menor[i + 1])
        i += 2 + struct.unpack(">H", menor[i + 2:i + 4])[0]
