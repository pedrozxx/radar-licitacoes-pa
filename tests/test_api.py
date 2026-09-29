"""Contrato HTTP: validação e falhas da origem, sem rede."""

from unittest.mock import AsyncMock

import httpx
import pytest

from api import index
from api._core.pncp import PncpIndisponivel, PncpLimiteExcedido, Resultado


@pytest.mark.parametrize("erro,status", [
    (PncpLimiteExcedido("limite"), 429),
    (PncpIndisponivel("fora do ar"), 503),
])
async def test_falha_da_origem_nao_vira_lista_vazia(monkeypatch, erro, status):
    monkeypatch.setattr(index, "buscar", AsyncMock(side_effect=erro))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=index.app), base_url="http://test"
    ) as client:
        resposta = await client.get("/api/licitacoes")
    assert resposta.status_code == status
    assert resposta.json() == {"detail": str(erro)}


@pytest.mark.parametrize("parametros,status", [
    ({"dias": 32}, 422), ({"modalidades": "abc"}, 400),
    ({"modalidades": "999"}, 400), ({"modalidades": ","}, 400),
])
async def test_consulta_invalida_nao_chama_origem(monkeypatch, parametros, status):
    async def nao_consultar(*args, **kwargs):
        pytest.fail("parâmetros inválidos chegaram à origem")
    monkeypatch.setattr(index, "buscar", nao_consultar)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=index.app), base_url="http://test"
    ) as client:
        resposta = await client.get("/api/licitacoes", params=parametros)
    assert resposta.status_code == status


async def test_api_preserva_resultado_parcial(monkeypatch):
    monkeypatch.setattr(index, "buscar", AsyncMock(return_value=Resultado(
        itens=[{"numeroControlePNCP": "exemplo", "valorTotalEstimado": 50}],
        truncado=True, modalidades_ok=[6], modalidades_falhas=[8],
    )))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=index.app), base_url="http://test"
    ) as client:
        resposta = await client.get("/api/licitacoes")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["truncado"] is True
    assert dados["modalidades_falhas"] == [8]
    assert dados["resumo"]["valor_total"] == 50
