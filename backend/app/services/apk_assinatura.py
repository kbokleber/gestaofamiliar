"""Lê o certificado de quem assinou um APK (esquema de assinatura v2/v3 do Android).

Serve para o servidor só aceitar versões assinadas com a chave da família: um APK com outra
assinatura (ex.: token de publicação vazado) é recusado antes de ir para a página /app.
Não valida a assinatura criptograficamente: um APK com assinatura inválida também não instala
no Android, então copiar só o certificado não adianta.
"""
from __future__ import annotations

import hashlib
import struct

_EOCD = b"PK\x05\x06"
_MAGICO = b"APK Sig Block 42"
_IDS = (0x7109871A, 0xF05368C0, 0x1B93AD61)  # v2, v3 e v3.1


class ApkInvalido(ValueError):
    pass


def _prefixados(dados: bytes) -> list[bytes]:
    """Sequência de itens com tamanho uint32 na frente."""
    itens, i = [], 0
    while i < len(dados):
        if i + 4 > len(dados):
            raise ApkInvalido("bloco de assinatura truncado")
        (n,) = struct.unpack_from("<I", dados, i)
        i += 4
        if i + n > len(dados):
            raise ApkInvalido("bloco de assinatura truncado")
        itens.append(dados[i:i + n])
        i += n
    return itens


def _um(dados: bytes) -> bytes:
    if len(dados) < 4:
        raise ApkInvalido("bloco de assinatura truncado")
    (n,) = struct.unpack_from("<I", dados, 0)
    if 4 + n > len(dados):
        raise ApkInvalido("bloco de assinatura truncado")
    return dados[4:4 + n]


def _bloco_de_assinatura(apk: bytes) -> bytes:
    fim = apk.rfind(_EOCD, max(0, len(apk) - 65557))
    if fim < 0 or fim + 22 > len(apk):
        raise ApkInvalido("o arquivo não é um ZIP válido")
    (inicio_cd,) = struct.unpack_from("<I", apk, fim + 16)
    if inicio_cd < 24 or inicio_cd > fim or apk[inicio_cd - 16:inicio_cd] != _MAGICO:
        raise ApkInvalido("o APK não tem assinatura v2/v3")
    (tamanho,) = struct.unpack_from("<Q", apk, inicio_cd - 24)
    comeco = inicio_cd - tamanho - 8
    if comeco < 0 or struct.unpack_from("<Q", apk, comeco)[0] != tamanho:
        raise ApkInvalido("bloco de assinatura inconsistente")
    return apk[comeco + 8:inicio_cd - 24]


def certificados(apk: bytes) -> set[str]:
    """SHA-256 (hex, minúsculo) dos certificados que assinam o APK."""
    pares = _bloco_de_assinatura(apk)
    achados: set[str] = set()
    i = 0
    while i + 12 <= len(pares):
        (n,) = struct.unpack_from("<Q", pares, i)
        if n < 4 or i + 8 + n > len(pares):
            raise ApkInvalido("bloco de assinatura inconsistente")
        (ident,) = struct.unpack_from("<I", pares, i + 8)
        valor = pares[i + 12:i + 8 + n]
        i += 8 + n
        if ident not in _IDS:
            continue
        for assinante in _prefixados(_um(valor)):
            dados_assinados = _um(assinante)
            resumos = _um(dados_assinados)
            resto = dados_assinados[4 + len(resumos):]
            for cert in _prefixados(_um(resto)):
                achados.add(hashlib.sha256(cert).hexdigest())
    if not achados:
        raise ApkInvalido("o APK não tem assinatura v2/v3")
    return achados


def comparar_versoes(a: str, b: str) -> int:
    """Positivo se a > b ("2.0.10" > "2.0.9")."""
    pa = [int(p) for p in a.split(".")]
    pb = [int(p) for p in b.split(".")]
    tamanho = max(len(pa), len(pb))
    pa += [0] * (tamanho - len(pa))
    pb += [0] * (tamanho - len(pb))
    return (pa > pb) - (pa < pb)
