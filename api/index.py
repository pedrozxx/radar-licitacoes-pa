"""API do Radar de Licitações.

Existe por três motivos concretos, e não por gosto de arquitetura:

- **CORS.** O PNCP não libera chamada direta do navegador.
- **Limite de requisições.** A origem corta quem insiste. Um intermediário com
  cache atende muitos visitantes com uma consulta só.
- **Formato.** O PNCP exige uma consulta por modalidade e devolve campo
  aninhado com `null` onde a interface espera número. A junção e a limpeza
  acontecem aqui, não no componente React.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ._core.cache import Cache
from ._core.normalize import (
    MODALIDADES,
    Licitacao,
    deduplicar,
    normalizar,
    resumir,
)
from ._core.pncp import PncpIndisponivel, PncpLimiteExcedido, buscar

logging.basicConfig(level=logging.INFO)

JANELA_MAXIMA_DIAS = 31  # acima disso o PNCP recusa ou demora demais
MODALIDADES_PADRAO = [6, 8, 9]  # pregão eletrônico, dispensa, inexigibilidade

app = FastAPI(
    title="Radar de Licitações do Pará",
    description="Consulta as compras públicas publicadas no PNCP.",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # API pública de leitura, sem credencial
    allow_methods=["GET"],
    allow_headers=["*"],
)

cache_municipios = Cache(ttl_segundos=24 * 60 * 60)


def _ordenar(itens: list[Licitacao], criterio: str) -> list[Licitacao]:
    """`prazo` é o padrão: o que fecha antes aparece antes.

    Registro sem prazo vai para o fim em vez de virar 0 — senão ele subiria ao
    topo fingindo urgência que não existe.
    """
    if criterio == "valor":
        return sorted(itens, key=lambda i: i.valor or -1, reverse=True)
    if criterio == "publicacao":
        return sorted(itens, key=lambda i: i.publicacao or "", reverse=True)
    return sorted(
        itens,
        key=lambda i: (
            i.dias_para_encerrar is None,
            i.dias_para_encerrar if i.dias_para_encerrar is not None else 0,
        ),
    )


def _filtrar(
    itens: list[Licitacao],
    municipio: str | None,
    busca: str | None,
    valor_minimo: float | None,
    apenas_abertas: bool,
) -> list[Licitacao]:
    resultado = itens
    if municipio:
        alvo = municipio.casefold()
        resultado = [i for i in resultado if i.municipio.casefold() == alvo]
    if busca:
        termos = busca.casefold().split()
        resultado = [
            i
            for i in resultado
            if all(t in f"{i.objeto} {i.orgao} {i.unidade}".casefold() for t in termos)
        ]
    if valor_minimo is not None:
        resultado = [i for i in resultado if i.valor is not None and i.valor >= valor_minimo]
    if apenas_abertas:
        resultado = [i for i in resultado if i.status_prazo in ("aberto", "urgente")]
    return resultado


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/modalidades")
async def listar_modalidades() -> list[dict[str, Any]]:
    return [{"id": i, "nome": n} for i, n in sorted(MODALIDADES.items())]


@app.get("/api/municipios")
async def listar_municipios() -> list[str]:
    """Municípios do Pará, do IBGE. Serve para o filtro não ser texto livre."""
    if (guardado := cache_municipios.obter("PA")) is not None:
        return guardado
    url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/PA/municipios"
    try:
        async with httpx.AsyncClient(timeout=15.0) as cliente:
            resposta = await cliente.get(url)
            resposta.raise_for_status()
            nomes = sorted(m["nome"] for m in resposta.json())
    except (httpx.HTTPError, KeyError, ValueError) as erro:
        raise HTTPException(
            status_code=503, detail="Não foi possível carregar a lista de municípios."
        ) from erro
    cache_municipios.guardar("PA", nomes)
    return nomes


@app.get("/api/licitacoes")
async def listar_licitacoes(
    dias: int = Query(14, ge=1, le=JANELA_MAXIMA_DIAS),
    uf: str = Query("PA", min_length=2, max_length=2),
    municipio: str | None = None,
    busca: str | None = Query(None, max_length=120),
    valor_minimo: float | None = Query(None, ge=0),
    apenas_abertas: bool = False,
    ordenar: str = Query("prazo", pattern="^(prazo|valor|publicacao)$"),
    modalidades: str | None = Query(
        None, description="IDs separados por vírgula. Padrão: 6,8,9."
    ),
) -> dict[str, Any]:
    """Licitações publicadas nos últimos `dias`, já normalizadas e agregadas."""
    if modalidades:
        try:
            escolhidas = [int(m) for m in modalidades.split(",") if m.strip()]
        except ValueError:
            raise HTTPException(400, "modalidades deve conter apenas números.") from None
        invalidas = [m for m in escolhidas if m not in MODALIDADES]
        if invalidas:
            raise HTTPException(400, f"Modalidade desconhecida: {invalidas}")
    else:
        escolhidas = MODALIDADES_PADRAO

    if not escolhidas:
        raise HTTPException(400, "Escolha ao menos uma modalidade.")

    hoje = date.today()
    inicio = hoje - timedelta(days=dias)

    try:
        resultado = await buscar(inicio, hoje, uf.upper(), escolhidas)
    except PncpLimiteExcedido as erro:
        # 429 e não 500: o cliente sabe que é temporário e pode tentar de novo.
        raise HTTPException(429, str(erro)) from erro
    except PncpIndisponivel as erro:
        raise HTTPException(503, str(erro)) from erro

    itens = deduplicar([normalizar(c, hoje) for c in resultado.itens])
    filtrados = _ordenar(
        _filtrar(itens, municipio, busca, valor_minimo, apenas_abertas), ordenar
    )

    return {
        "periodo": {"inicio": inicio.isoformat(), "fim": hoje.isoformat()},
        "uf": uf.upper(),
        "modalidades": escolhidas,
        "total_encontrado": len(itens),
        # `truncado` sobe até a interface de propósito: uma lista cortada nunca
        # pode ser apresentada como se fosse a lista inteira.
        "truncado": resultado.truncado,
        "modalidades_falhas": resultado.modalidades_falhas,
        "resumo": resumir(filtrados),
        "itens": [i.to_dict() for i in filtrados],
    }
