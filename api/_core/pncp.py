"""Cliente do PNCP.

Quatro comportamentos da origem ditam este código. Todos foram medidos contra
a API real, nenhum foi suposto:

1. **`codigoModalidadeContratacao` é obrigatório.** Não existe "trazer tudo" —
   é preciso consultar modalidade por modalidade e juntar.
2. **Há limite de requisições, e ele tem duas caras:** `429 Too Many Requests`
   e, o mais traiçoeiro, `200` com corpo **HTML**. Quem chamar `.json()` direto
   recebe um erro de parse e nunca descobre a causa. Não há `Retry-After` nem
   cabeçalho de quota; medindo, a origem aceita cerca de 5 a 6 requisições em
   rajada antes de cortar.
3. **É lenta.** Uma consulta de 10 dias levou 4,4 s.
4. **O tempo total é imprevisível.** Com nova tentativa e espera crescente, o
   pior caso de uma consulta a três modalidades passava de três minutos.

O ponto 4 é o que define a forma deste módulo. Uma página que o usuário abre
não pode ficar pendurada esperando uma origem instável, então `buscar` recebe
um **orçamento de tempo**: quando o relógio estoura, devolve o que já tem e
avisa que truncou. Ninguém fica olhando para uma tela travada, e ninguém lê
uma lista curta achando que é a lista inteira.

A coleta ampla — várias modalidades, várias páginas — não acontece aqui: ela
roda em `scripts/coletar.py`, fora do caminho da requisição, onde pode ser
lenta e educada à vontade.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import httpx

from .cache import Cache

log = logging.getLogger(__name__)

BASE = "https://pncp.gov.br/api/consulta/v1"
TAMANHO_PAGINA = 50  # o mínimo aceito é 10; 50 reduz o número de idas à origem
TENTATIVAS = 2
ESPERA_INICIAL = 3.0
PAUSA_ENTRE_REQUISICOES = 1.0
TIMEOUT_HTTP = 12.0
ORCAMENTO_PADRAO = 20.0  # segundos de parede para a consulta inteira

cache = Cache(ttl_segundos=15 * 60)

MENSAGEM_LIMITE = (
    "O PNCP está limitando as consultas neste momento. "
    "Os dados voltam em alguns instantes — tente de novo."
)


class PncpIndisponivel(RuntimeError):
    """A origem falhou de um jeito que o usuário precisa saber."""


class PncpLimiteExcedido(PncpIndisponivel):
    """Limite de requisições do PNCP. Difere de indisponibilidade real."""


@dataclass
class Resultado:
    """O que voltou, e o que não deu tempo de vir.

    `truncado` existe para que a interface nunca apresente uma lista parcial
    como se fosse completa. Corte silencioso é o pior tipo de bug de dados:
    a tela parece certa e o número está errado.
    """

    itens: list[dict[str, Any]] = field(default_factory=list)
    truncado: bool = False
    modalidades_ok: list[int] = field(default_factory=list)
    modalidades_falhas: list[int] = field(default_factory=list)


class _Relogio:
    """Orçamento de tempo de parede compartilhado pela consulta inteira."""

    def __init__(self, orcamento: float) -> None:
        self._fim = time.monotonic() + orcamento

    @property
    def restante(self) -> float:
        return self._fim - time.monotonic()

    @property
    def estourou(self) -> bool:
        return self.restante <= 0


def _garantir_json(resposta: httpx.Response) -> Any:
    """Valida que veio JSON antes de tentar interpretar.

    Checar o content-type é o que transforma um erro de parse incompreensível
    numa mensagem que a interface consegue explicar.
    """
    tipo = resposta.headers.get("content-type", "")
    if "application/json" not in tipo:
        trecho = resposta.text[:200].lower()
        if "limite" in trecho or "excedido" in trecho:
            raise PncpLimiteExcedido(MENSAGEM_LIMITE)
        raise PncpIndisponivel(
            f"O PNCP respondeu em {tipo or 'formato desconhecido'}, não em JSON."
        )
    return resposta.json()


async def _buscar_pagina(
    cliente: httpx.AsyncClient,
    caminho: str,
    params: dict[str, Any],
    relogio: _Relogio,
) -> dict[str, Any]:
    """Uma página, com nova tentativa — sempre dentro do orçamento."""
    espera = ESPERA_INICIAL
    for tentativa in range(1, TENTATIVAS + 1):
        if relogio.estourou:
            raise TimeoutError("orçamento esgotado")
        try:
            resposta = await cliente.get(
                f"{BASE}{caminho}",
                params=params,
                timeout=min(TIMEOUT_HTTP, max(relogio.restante, 1.0)),
            )
            if resposta.status_code == 429:
                # A outra cara do limite. Sem este ramo o 429 cairia no
                # tratamento genérico e o usuário leria "não respondeu" —
                # que é falso: respondeu, e disse para esperar.
                raise PncpLimiteExcedido(MENSAGEM_LIMITE)
            if resposta.status_code == 204:  # intervalo sem registro
                return {"data": [], "totalPaginas": 0}
            if resposta.status_code == 400:
                # Erro de parâmetro. Repetir não resolve e mascara o defeito.
                raise PncpIndisponivel(
                    f"Consulta recusada pelo PNCP: {resposta.text[:160]}"
                )
            resposta.raise_for_status()
            return _garantir_json(resposta)
        except PncpLimiteExcedido:
            if tentativa == TENTATIVAS or relogio.restante < espera:
                raise
            log.warning("limite do PNCP; aguardando %.1fs", espera)
            await asyncio.sleep(espera)
            espera *= 2
        except (httpx.TimeoutException, httpx.HTTPStatusError) as erro:
            if tentativa == TENTATIVAS or relogio.restante < espera:
                raise PncpIndisponivel("O PNCP não respondeu a tempo.") from erro
            await asyncio.sleep(espera)
            espera *= 2
    return {"data": [], "totalPaginas": 0}


async def _buscar_modalidade(
    cliente: httpx.AsyncClient,
    modalidade: int,
    inicio: date,
    fim: date,
    uf: str,
    relogio: _Relogio,
    max_paginas: int,
) -> tuple[list[dict[str, Any]], bool]:
    """Páginas de uma modalidade. Devolve (itens, faltou_pagina)."""
    itens: list[dict[str, Any]] = []
    pagina = 1
    while pagina <= max_paginas:
        corpo = await _buscar_pagina(
            cliente,
            "/contratacoes/publicacao",
            {
                "dataInicial": inicio.strftime("%Y%m%d"),
                "dataFinal": fim.strftime("%Y%m%d"),
                "codigoModalidadeContratacao": modalidade,
                "uf": uf,
                "pagina": pagina,
                "tamanhoPagina": TAMANHO_PAGINA,
            },
            relogio,
        )
        lote = corpo.get("data") or []
        itens.extend(lote)
        total_paginas = corpo.get("totalPaginas") or 0
        if not lote or pagina >= total_paginas:
            return itens, False
        if pagina >= max_paginas:
            return itens, True  # havia mais página e paramos de propósito
        pagina += 1
        if relogio.estourou:
            return itens, True
        await asyncio.sleep(min(PAUSA_ENTRE_REQUISICOES, max(relogio.restante, 0)))
    return itens, False


async def buscar(
    inicio: date,
    fim: date,
    uf: str,
    modalidades: list[int],
    orcamento: float = ORCAMENTO_PADRAO,
    max_paginas: int = 1,
) -> Resultado:
    """Consulta as modalidades pedidas dentro de um orçamento de tempo.

    Serializado de propósito: em paralelo a origem corta antes de terminar, e
    aí nenhuma modalidade volta. Devagar e completo vence rápido e vazio.
    """
    chave = f"{inicio}:{fim}:{uf}:{sorted(modalidades)}:{max_paginas}"
    if (guardado := cache.obter(chave)) is not None:
        log.info("cache: %s", chave)
        return guardado

    relogio = _Relogio(orcamento)
    resultado = Resultado()
    primeiro_erro: PncpIndisponivel | None = None

    async with httpx.AsyncClient(headers={"Accept": "application/json"}) as cliente:
        for indice, modalidade in enumerate(modalidades):
            if relogio.estourou:
                resultado.truncado = True
                resultado.modalidades_falhas.extend(modalidades[indice:])
                break
            try:
                itens, faltou = await _buscar_modalidade(
                    cliente, modalidade, inicio, fim, uf, relogio, max_paginas
                )
                resultado.itens.extend(itens)
                resultado.modalidades_ok.append(modalidade)
                resultado.truncado = resultado.truncado or faltou
            except (PncpIndisponivel, TimeoutError) as erro:
                log.warning("modalidade %s falhou: %s", modalidade, erro)
                resultado.modalidades_falhas.append(modalidade)
                resultado.truncado = True
                if primeiro_erro is None:
                    primeiro_erro = (
                        erro
                        if isinstance(erro, PncpIndisponivel)
                        else PncpIndisponivel("O PNCP não respondeu a tempo.")
                    )
                if isinstance(erro, PncpLimiteExcedido):
                    # Insistir depois de ser cortado só piora. Sai com o que tem.
                    resultado.modalidades_falhas.extend(modalidades[indice + 1 :])
                    break
            if indice + 1 < len(modalidades) and not relogio.estourou:
                await asyncio.sleep(
                    min(PAUSA_ENTRE_REQUISICOES, max(relogio.restante, 0))
                )

    # Nada voltou e tudo falhou: é falha de verdade, precisa subir para virar
    # mensagem de erro na tela, e não lista vazia fingindo "nenhum resultado".
    #
    # O erro ORIGINAL sobe, não um genérico: só ele distingue "limite atingido,
    # tente em instantes" (429) de "origem fora do ar" (503). Trocar por uma
    # mensagem única aqui apagaria essa diferença antes de chegar na tela.
    if not resultado.itens and resultado.modalidades_falhas:
        raise primeiro_erro or PncpIndisponivel(
            "Não foi possível consultar o PNCP agora. Tente novamente em instantes."
        )

    # Resultado incompleto não entra no cache: congelaria o buraco por 15 min.
    if not resultado.truncado:
        cache.guardar(chave, resultado)
    return resultado
