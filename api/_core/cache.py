"""Cache em memória com expiração.

Simples de propósito: em ambiente serverless cada instância tem o seu, e isso
já basta para absorver a rajada de acessos que vêm do mesmo filtro.

Regra que veio de errar antes: **falha não entra no cache.** Guardar um erro
faz o app continuar respondendo errado depois que a origem voltou.
"""

from __future__ import annotations

import time
from typing import Any


class Cache:
    def __init__(self, ttl_segundos: int = 900, tamanho_maximo: int = 128) -> None:
        self._ttl = ttl_segundos
        self._tamanho_maximo = tamanho_maximo
        self._dados: dict[str, tuple[float, Any]] = {}

    def obter(self, chave: str) -> Any | None:
        registro = self._dados.get(chave)
        if registro is None:
            return None
        gravado_em, valor = registro
        if time.monotonic() - gravado_em > self._ttl:
            del self._dados[chave]
            return None
        return valor

    def guardar(self, chave: str, valor: Any) -> None:
        if len(self._dados) >= self._tamanho_maximo:
            mais_antiga = min(self._dados, key=lambda k: self._dados[k][0])
            del self._dados[mais_antiga]
        self._dados[chave] = (time.monotonic(), valor)

    def limpar(self) -> None:
        self._dados.clear()

    def __len__(self) -> int:
        return len(self._dados)
