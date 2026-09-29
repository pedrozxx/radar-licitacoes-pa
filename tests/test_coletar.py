"""Contrato do snapshot consumido pelo site, sem consultas externas."""

from unittest.mock import AsyncMock

import pytest

from api._core.pncp import PncpIndisponivel, Resultado
from scripts import coletar as job


@pytest.mark.parametrize("truncado", [True, False])
async def test_snapshot_preserva_truncamento(monkeypatch, truncado):
    monkeypatch.setattr(job, "MODALIDADES_COLETADAS", [6])
    monkeypatch.setattr(job, "buscar", AsyncMock(return_value=Resultado(
        itens=[{"numeroControlePNCP": "exemplo"}],
        truncado=truncado, modalidades_ok=[6],
    )))
    dados = await job.coletar(30, "PA")
    assert dados["truncado"] is truncado
    assert dados["itens"][0]["id"] == "exemplo"


async def test_falha_parcial_preserva_itens_e_avisa(monkeypatch):
    monkeypatch.setattr(job, "MODALIDADES_COLETADAS", [6, 8])
    monkeypatch.setattr(job, "PAUSA_ENTRE_MODALIDADES", 0)
    monkeypatch.setattr(job, "buscar", AsyncMock(side_effect=[
        Resultado(itens=[{"numeroControlePNCP": "exemplo"}], modalidades_ok=[6]),
        PncpIndisponivel("indisponível"),
    ]))
    dados = await job.coletar(30, "PA")
    assert dados["truncado"] is True
    assert dados["modalidades_falhas"] == [8]
    assert dados["resumo"]["total"] == 1


def test_coleta_vazia_preserva_arquivo_publicado(monkeypatch, tmp_path):
    destino = tmp_path / "snapshot.json"
    destino.write_text('"snapshot anterior"', encoding="utf-8")
    monkeypatch.setattr(job.sys, "argv", ["coletar", "--saida", str(destino)])
    monkeypatch.setattr(job, "coletar", AsyncMock(return_value={"itens": []}))
    assert job.main() == 1
    assert destino.read_text(encoding="utf-8") == '"snapshot anterior"'


@pytest.mark.parametrize("relativo", [True, False])
def test_saida_personalizada_grava_e_termina_com_sucesso(monkeypatch, tmp_path, relativo):
    import json

    monkeypatch.chdir(tmp_path)
    destino = "snapshot.json" if relativo else str(tmp_path / "snapshot.json")
    monkeypatch.setattr(job.sys, "argv", ["coletar", "--saida", destino])
    dados = {
        "itens": [{"id": "exemplo"}], "modalidades_falhas": [],
        "resumo": {"total": 1, "com_valor": 0, "urgentes": 0},
    }
    monkeypatch.setattr(job, "coletar", AsyncMock(return_value=dados))
    assert job.main() == 0
    assert json.loads((tmp_path / "snapshot.json").read_text(encoding="utf-8")) == dados
