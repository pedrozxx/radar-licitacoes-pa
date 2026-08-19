"""Coletor diário do PNCP.

Roda no GitHub Actions, não no navegador de ninguém. É aqui que a lentidão e o
limite de requisições do PNCP deixam de ser problema: um job agendado pode
esperar, pedir devagar e tentar de novo sem que exista um usuário olhando para
uma tela travada.

O resultado é um JSON estático em `web/public/dados/`. O site lê esse arquivo e
carrega instantaneamente — e continua funcionando mesmo quando o PNCP está fora
do ar, o que acontece com frequência.

Uso:
    python scripts/coletar.py --dias 30 --uf PA
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from api._core.normalize import (  # noqa: E402
    MODALIDADES,
    deduplicar,
    normalizar,
    resumir,
)
from api._core.pncp import PncpIndisponivel, buscar  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("coletor")

DESTINO = RAIZ / "web" / "public" / "dados" / "licitacoes-pa.json"

# Modalidades que de fato movimentam compra estadual e municipal. Leilão e
# concurso quase nunca aparecem no Pará e só gastariam requisição.
MODALIDADES_COLETADAS = [6, 8, 9, 4, 12]

# O job tem tempo: cada modalidade ganha seu próprio orçamento, e a pausa
# entre elas é longa de propósito para não acionar o limite da origem.
ORCAMENTO_POR_MODALIDADE = 90.0
PAUSA_ENTRE_MODALIDADES = 8.0
MAX_PAGINAS = 6  # até 300 registros por modalidade


async def coletar(dias: int, uf: str) -> dict:
    hoje = date.today()
    inicio = hoje - timedelta(days=dias)

    crus: list[dict] = []
    ok: list[int] = []
    falhas: list[int] = []

    for indice, modalidade in enumerate(MODALIDADES_COLETADAS):
        nome = MODALIDADES.get(modalidade, str(modalidade))
        log.info("coletando %s (%s)...", nome, modalidade)
        try:
            resultado = await buscar(
                inicio,
                hoje,
                uf,
                [modalidade],
                orcamento=ORCAMENTO_POR_MODALIDADE,
                max_paginas=MAX_PAGINAS,
            )
            crus.extend(resultado.itens)
            ok.append(modalidade)
            log.info("  %d registros%s", len(resultado.itens),
                     " (truncado)" if resultado.truncado else "")
        except PncpIndisponivel as erro:
            log.warning("  falhou: %s", erro)
            falhas.append(modalidade)

        if indice + 1 < len(MODALIDADES_COLETADAS):
            await asyncio.sleep(PAUSA_ENTRE_MODALIDADES)

    itens = deduplicar([normalizar(c, hoje) for c in crus])
    itens.sort(
        key=lambda i: (
            i.dias_para_encerrar is None,
            i.dias_para_encerrar if i.dias_para_encerrar is not None else 0,
        )
    )

    return {
        "gerado_em": datetime.now(UTC).isoformat(),
        "uf": uf,
        "periodo": {"inicio": inicio.isoformat(), "fim": hoje.isoformat()},
        "modalidades_coletadas": ok,
        "modalidades_falhas": falhas,
        "resumo": resumir(itens),
        "itens": [i.to_dict() for i in itens],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta licitações do PNCP.")
    parser.add_argument("--dias", type=int, default=30)
    parser.add_argument("--uf", default="PA")
    parser.add_argument("--saida", type=Path, default=DESTINO)
    argumentos = parser.parse_args()

    dados = asyncio.run(coletar(argumentos.dias, argumentos.uf.upper()))

    # Uma coleta que não trouxe nada não pode sobrescrever o arquivo bom que já
    # está publicado. Sem esta guarda, um dia de instabilidade do PNCP apagaria
    # os dados do site e ninguém perceberia até alguém abrir a página.
    if not dados["itens"]:
        log.error("nenhum registro coletado — arquivo existente preservado")
        return 1

    argumentos.saida.parent.mkdir(parents=True, exist_ok=True)
    argumentos.saida.write_text(
        json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    resumo = dados["resumo"]
    log.info(
        "gravado %s: %d licitações, %d com valor, %d urgentes",
        argumentos.saida.relative_to(RAIZ),
        resumo["total"],
        resumo["com_valor"],
        resumo["urgentes"],
    )
    if dados["modalidades_falhas"]:
        log.warning("modalidades que falharam: %s", dados["modalidades_falhas"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
