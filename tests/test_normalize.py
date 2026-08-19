"""Testes da normalização.

Cada caso aqui saiu de algo observado na resposta real do PNCP, não de
imaginação: valor zerado, prazo ausente, campo aninhado faltando, objeto com
quebra de linha, e o mesmo registro voltando em duas modalidades.
"""

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from api._core.normalize import (
    Licitacao,
    deduplicar,
    dias_ate,
    normalizar,
    resumir,
    status_prazo,
)

HOJE = date(2026, 8, 19)


def registro(**troca):
    """Um item cru do PNCP, com a forma que a API devolve de verdade."""
    base = {
        "numeroControlePNCP": "00394452000103-1-015453/2026",
        "objetoCompra": "Aquisição de materiais de consumo",
        "orgaoEntidade": {"cnpj": "00394452000103", "razaoSocial": "COMANDO DO EXERCITO"},
        "unidadeOrgao": {"nomeUnidade": "8 BATALHAO", "municipioNome": "Belém"},
        "modalidadeId": 6,
        "modalidadeNome": "Pregão - Eletrônico",
        "situacaoCompraNome": "Divulgada no PNCP",
        "valorTotalEstimado": 1061529.77,
        "dataPublicacaoPncp": "2026-08-03T04:00:10",
        "dataAberturaProposta": "2026-08-04T08:00:00",
        "dataEncerramentoProposta": "2026-08-25T09:00:00",
        "linkSistemaOrigem": "https://exemplo.gov.br/edital/1",
    }
    base.update(troca)
    return base


class TestValor:
    def test_valor_normal_e_preservado(self):
        assert normalizar(registro(), HOJE).valor == pytest.approx(1061529.77)

    def test_zero_vira_none_e_nao_zero(self):
        """O PNCP manda 0.0 para "não informado".

        Tratar como zero real faria a interface exibir "R$ 0,00", como se fosse
        um contrato de graça, e ainda contaria no denominador da média.
        """
        assert normalizar(registro(valorTotalEstimado=0.0), HOJE).valor is None

    def test_none_continua_none(self):
        assert normalizar(registro(valorTotalEstimado=None), HOJE).valor is None

    def test_texto_invalido_nao_derruba(self):
        assert normalizar(registro(valorTotalEstimado="sem valor"), HOJE).valor is None


class TestPrazo:
    @pytest.mark.parametrize(
        "encerramento,esperado",
        [
            ("2026-08-25T09:00:00", "aberto"),  # 6 dias
            ("2026-08-22T09:00:00", "urgente"),  # 3 dias, no limite
            ("2026-08-19T23:00:00", "urgente"),  # hoje
            ("2026-08-14T09:00:00", "encerrado"),  # passou
            (None, "sem_prazo"),
        ],
    )
    def test_classificacao(self, encerramento, esperado):
        item = normalizar(registro(dataEncerramentoProposta=encerramento), HOJE)
        assert item.status_prazo == esperado

    def test_sem_prazo_nunca_vira_aberto(self):
        """Dizer "aberto" sobre data que não existe é inventar informação."""
        assert status_prazo(None) == "sem_prazo"
        assert status_prazo(None) != "aberto"

    def test_data_ilegivel_nao_explode(self):
        item = normalizar(registro(dataEncerramentoProposta="31/12/2026"), HOJE)
        assert item.encerramento is None
        assert item.status_prazo == "sem_prazo"

    def test_dias_ate_conta_certo(self):
        assert dias_ate("2026-08-22T09:00:00", HOJE) == 3
        assert dias_ate("2026-08-14T09:00:00", HOJE) == -5


class TestCamposFaltando:
    def test_orgao_ausente_nao_quebra(self):
        item = normalizar(registro(orgaoEntidade=None), HOJE)
        assert item.orgao == "Órgão não informado"
        assert item.cnpj == ""

    def test_unidade_ausente_nao_quebra(self):
        item = normalizar(registro(unidadeOrgao=None), HOJE)
        assert item.municipio == "Não informado"

    def test_objeto_com_quebra_de_linha_e_colapsado(self):
        item = normalizar(registro(objetoCompra="Compra  de\n\n  papel"), HOJE)
        assert item.objeto == "Compra de papel"

    def test_modalidade_sem_nome_usa_a_tabela(self):
        item = normalizar(registro(modalidadeNome=None, modalidadeId=8), HOJE)
        assert item.modalidade == "Dispensa de licitação"


class TestDeduplicar:
    def test_remove_repetido_entre_modalidades(self):
        """O backend varre várias modalidades; o mesmo edital pode voltar duas
        vezes. Sem deduplicar, o valor total soma dobrado."""
        itens = [normalizar(registro(), HOJE), normalizar(registro(), HOJE)]
        assert len(deduplicar(itens)) == 1

    def test_ids_diferentes_sao_mantidos(self):
        itens = [
            normalizar(registro(), HOJE),
            normalizar(registro(numeroControlePNCP="outro-id"), HOJE),
        ]
        assert len(deduplicar(itens)) == 2

    def test_sem_id_e_preservado(self):
        """Descartar registro por falta de chave perde dado real."""
        itens = [
            normalizar(registro(numeroControlePNCP=None), HOJE),
            normalizar(registro(numeroControlePNCP=None), HOJE),
        ]
        assert len(deduplicar(itens)) == 2


class TestResumo:
    def test_total_ignora_sem_valor_e_informa_quantos_contou(self):
        """O usuário precisa saber que o total não cobre todos os registros."""
        itens = [
            normalizar(registro(valorTotalEstimado=100.0), HOJE),
            normalizar(registro(numeroControlePNCP="b", valorTotalEstimado=None), HOJE),
            normalizar(registro(numeroControlePNCP="c", valorTotalEstimado=50.0), HOJE),
        ]
        r = resumir(itens)
        assert r["total"] == 3
        assert r["com_valor"] == 2
        assert r["valor_total"] == pytest.approx(150.0)

    def test_lista_vazia_nao_quebra(self):
        r = resumir([])
        assert r == {
            "total": 0,
            "com_valor": 0,
            "valor_total": 0,
            "urgentes": 0,
            "por_orgao": [],
        }

    def test_agrupa_por_orgao_somando(self):
        itens = [
            normalizar(registro(valorTotalEstimado=100.0), HOJE),
            normalizar(registro(numeroControlePNCP="b", valorTotalEstimado=300.0), HOJE),
        ]
        r = resumir(itens)
        assert r["por_orgao"][0] == {"orgao": "COMANDO DO EXERCITO", "valor": 400.0}

    def test_conta_urgentes(self):
        itens = [
            normalizar(registro(dataEncerramentoProposta="2026-08-20T09:00:00"), HOJE),
            normalizar(
                registro(
                    numeroControlePNCP="b",
                    dataEncerramentoProposta="2026-09-30T09:00:00",
                ),
                HOJE,
            ),
        ]
        assert resumir(itens)["urgentes"] == 1


def test_licitacao_e_imutavel():
    """Congelada de propósito: nada muda um registro depois de normalizado."""
    item = normalizar(registro(), HOJE)
    assert isinstance(item, Licitacao)
    # dataclass(frozen=True) levanta FrozenInstanceError, não Exception genérica.
    with pytest.raises(FrozenInstanceError):
        item.valor = 1  # type: ignore[misc]
