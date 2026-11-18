"""Limite simples de tentativas em memória, por chave e numa janela de tempo.

Serve para rotas sem login, como o pareamento do celular. Vale por processo da API:
com um único container, isso cobre o uso da família.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional

from fastapi import Request


class LimiteTentativas:
    def __init__(self, maximo: int, janela_segundos: int):
        self.maximo = maximo
        self.janela = janela_segundos
        self._registros: dict[str, deque[float]] = {}
        self._trava = threading.Lock()

    def _limpar(self, fila: deque[float], agora: float) -> None:
        while fila and agora - fila[0] >= self.janela:
            fila.popleft()

    def excedido(self, chave: str, agora: Optional[float] = None) -> bool:
        agora = time.monotonic() if agora is None else agora
        with self._trava:
            fila = self._registros.get(chave)
            if not fila:
                return False
            self._limpar(fila, agora)
            return len(fila) >= self.maximo

    def registrar(self, chave: str, agora: Optional[float] = None) -> None:
        agora = time.monotonic() if agora is None else agora
        with self._trava:
            fila = self._registros.setdefault(chave, deque())
            self._limpar(fila, agora)
            fila.append(agora)
            if len(self._registros) > 10_000:
                for antiga in [c for c, f in self._registros.items() if not f]:
                    self._registros.pop(antiga, None)

    def zerar(self) -> None:
        with self._trava:
            self._registros.clear()


def ip_do_pedido(request: Request) -> str:
    """IP de quem chamou. Atrás do Traefik e do nginx, o primeiro X-Forwarded-For é o cliente."""
    encaminhado = request.headers.get("x-forwarded-for", "")
    primeiro = encaminhado.split(",")[0].strip()
    if primeiro:
        return primeiro
    real = request.headers.get("x-real-ip", "").strip()
    if real:
        return real
    return request.client.host if request.client else "desconhecido"
