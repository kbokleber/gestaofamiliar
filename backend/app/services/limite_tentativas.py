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


def ip_do_pedido(request: Request, proxies: int = 2) -> str:
    """IP de quem chamou, lido de trás para frente no X-Forwarded-For.

    Quem chama pode escrever o que quiser no começo do cabeçalho; cada proxy só
    acrescenta no fim. Com Traefik e nginx na frente (proxies=2), o nginx põe o IP
    do Traefik por último e o valor anterior é o IP que o Traefik viu: o cliente.
    """
    valores = [v.strip() for v in request.headers.get("x-forwarded-for", "").split(",") if v.strip()]
    if proxies > 0 and valores:
        return valores[-proxies] if len(valores) >= proxies else valores[0]
    return request.client.host if request.client else "desconhecido"
