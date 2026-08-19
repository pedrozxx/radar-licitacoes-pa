"""Testes do cliente do PNCP, sem tocar a rede.

Dois casos carregam o peso aqui:

- O limite de requisições tem **duas caras** (`429` e `200` com corpo HTML).
  As duas precisam virar `PncpLimiteExcedido`, senão uma delas chega ao usuário
  como erro de parse ou como "não respondeu" — ambos falsos.
- Resultado incompleto precisa vir marcado como `truncado`. Corte silencioso é
  o pior bug de dados: a tela parece certa e o número está errado.
"""

from datetime import date

import httpx
import pytest
import respx

from api._core.cache import Cache
from api._core.pncp import (
    BASE,
    PncpIndisponivel,
    PncpLimiteExcedido,
    buscar,
    cache,
)

INICIO = date(2026, 8, 1)
FIM = date(2026, 8, 10)

HTML_LIMITE = (
    "<html><head><title>Limite de Requisicoes Excedido</title></head>"
    "<body><h2>Limite de requisicoes excedido</h2></body></html>"
)


@pytest.fixture(autouse=True)
def _cache_limpo():
    """Sem isto um teste vaza resultado para o seguinte."""
    cache.limpar()
    yield
    cache.limpar()


def _pagina(itens, total_paginas=1):
    return httpx.Response(
        200,
        json={"data": itens, "totalPaginas": total_paginas},
        headers={"content-type": "application/json"},
    )


def _html_limite():
    return httpx.Response(
        200, text=HTML_LIMITE, headers={"content-type": "text/html"}
    )


class TestLimiteDeRequisicoes:
    @respx.mock
    async def test_200_com_html_vira_limite_excedido(self):
        """O caso traiçoeiro: status 200, corpo HTML. `.json()` direto quebraria
        com erro de parse e esconderia a causa real."""
        respx.get(url__startswith=BASE).mock(return_value=_html_limite())
        with pytest.raises(PncpLimiteExcedido):
            await buscar(INICIO, FIM, "PA", [6], orcamento=2)

    @respx.mock
    async def test_429_vira_o_mesmo_erro(self):
        """Sem este ramo o 429 cairia no tratamento genérico e o usuário leria
        "não respondeu" — falso: respondeu, e disse para esperar."""
        respx.get(url__startswith=BASE).mock(
            return_value=httpx.Response(
                429, json={}, headers={"content-type": "application/json"}
            )
        )
        with pytest.raises(PncpLimiteExcedido):
            await buscar(INICIO, FIM, "PA", [6], orcamento=2)

    @respx.mock
    async def test_html_desconhecido_vira_indisponivel(self):
        respx.get(url__startswith=BASE).mock(
            return_value=httpx.Response(
                200, text="<html>manutencao</html>",
                headers={"content-type": "text/html"},
            )
        )
        with pytest.raises(PncpIndisponivel):
            await buscar(INICIO, FIM, "PA", [6], orcamento=2)

    @respx.mock
    async def test_para_de_insistir_apos_ser_cortado(self):
        """Depois do corte, insistir nas outras modalidades só piora."""
        respx.get(url__startswith=BASE).mock(return_value=_html_limite())
        with pytest.raises(PncpIndisponivel):
            await buscar(INICIO, FIM, "PA", [6, 8, 9], orcamento=2)


class TestTruncamento:
    @respx.mock
    async def test_falha_parcial_marca_truncado(self):
        """Uma modalidade fora não pode zerar a tela — mas o usuário precisa
        saber que a lista está incompleta."""
        respx.get(url__startswith=BASE).mock(
            side_effect=[
                _pagina([{"numeroControlePNCP": "a"}]),
                httpx.Response(500),
                httpx.Response(500),
            ]
        )
        r = await buscar(INICIO, FIM, "PA", [6, 8], orcamento=10)
        assert len(r.itens) == 1
        assert r.truncado is True
        assert r.modalidades_ok == [6]
        assert 8 in r.modalidades_falhas

    @respx.mock
    async def test_pagina_a_mais_marca_truncado(self):
        """Havia página 2 e paramos no teto: isso é corte, e precisa aparecer."""
        respx.get(url__startswith=BASE).mock(
            return_value=_pagina([{"numeroControlePNCP": "a"}], total_paginas=5)
        )
        r = await buscar(INICIO, FIM, "PA", [6], orcamento=10, max_paginas=1)
        assert r.truncado is True

    @respx.mock
    async def test_resultado_completo_nao_marca_truncado(self):
        respx.get(url__startswith=BASE).mock(
            return_value=_pagina([{"numeroControlePNCP": "a"}], total_paginas=1)
        )
        r = await buscar(INICIO, FIM, "PA", [6], orcamento=10)
        assert r.truncado is False


class TestOrcamentoDeTempo:
    @respx.mock
    async def test_orcamento_zerado_nao_chama_a_origem(self):
        """A garantia que impede a página de ficar pendurada."""
        rota = respx.get(url__startswith=BASE).mock(return_value=_pagina([]))
        with pytest.raises(PncpIndisponivel):
            await buscar(INICIO, FIM, "PA", [6], orcamento=-1)
        assert rota.call_count == 0


class TestComportamentoNormal:
    @respx.mock
    async def test_junta_modalidades(self):
        respx.get(url__startswith=BASE).mock(
            side_effect=[
                _pagina([{"numeroControlePNCP": "a"}]),
                _pagina([{"numeroControlePNCP": "b"}]),
            ]
        )
        r = await buscar(INICIO, FIM, "PA", [6, 8], orcamento=10)
        assert len(r.itens) == 2
        assert r.modalidades_ok == [6, 8]

    @respx.mock
    async def test_204_e_periodo_sem_registro_nao_erro(self):
        respx.get(url__startswith=BASE).mock(return_value=httpx.Response(204))
        r = await buscar(INICIO, FIM, "PA", [6], orcamento=10)
        assert r.itens == []
        assert r.truncado is False

    @respx.mock
    async def test_400_nao_repete_tentativa(self):
        """Parâmetro inválido não melhora com insistência."""
        rota = respx.get(url__startswith=BASE).mock(
            return_value=httpx.Response(
                400, json={"message": "faltou parametro"},
                headers={"content-type": "application/json"},
            )
        )
        with pytest.raises(PncpIndisponivel):
            await buscar(INICIO, FIM, "PA", [6], orcamento=10)
        assert rota.call_count == 1


class TestCacheDaBusca:
    @respx.mock
    async def test_evita_segunda_ida_a_origem(self):
        rota = respx.get(url__startswith=BASE).mock(
            return_value=_pagina([{"numeroControlePNCP": "a"}])
        )
        await buscar(INICIO, FIM, "PA", [6], orcamento=10)
        await buscar(INICIO, FIM, "PA", [6], orcamento=10)
        assert rota.call_count == 1

    @respx.mock
    async def test_truncado_nao_entra_no_cache(self):
        """Cachear resultado incompleto congela o buraco por 15 minutos."""
        respx.get(url__startswith=BASE).mock(
            side_effect=[
                _pagina([{"numeroControlePNCP": "a"}]),
                httpx.Response(500),
                httpx.Response(500),
            ]
        )
        await buscar(INICIO, FIM, "PA", [6, 8], orcamento=10)
        assert len(cache) == 0


class TestCache:
    def test_expira(self, monkeypatch):
        import api._core.cache as modulo

        agora = [1000.0]
        monkeypatch.setattr(modulo.time, "monotonic", lambda: agora[0])
        c = Cache(ttl_segundos=60)
        c.guardar("k", "v")
        assert c.obter("k") == "v"
        agora[0] += 61
        assert c.obter("k") is None

    def test_descarta_o_mais_antigo_ao_encher(self):
        c = Cache(ttl_segundos=60, tamanho_maximo=2)
        c.guardar("a", 1)
        c.guardar("b", 2)
        c.guardar("c", 3)
        assert len(c) == 2
