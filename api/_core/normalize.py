"""Normalização dos registros do PNCP.

O PNCP devolve um objeto largo, com campos aninhados, nome inconsistente e
`null` em lugares onde a interface espera número. Este módulo é a fronteira:
tudo que sai daqui já está no formato que o front consome, sem surpresa.

Funções puras de propósito — é o que torna o teste possível sem rede.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any

# O PNCP exige `codigoModalidadeContratacao` em toda consulta, então não há
# como pedir "tudo". Estas são as modalidades que de fato aparecem em compras
# estaduais e municipais; o backend varre e junta.
MODALIDADES: dict[int, str] = {
    1: "Leilão eletrônico",
    2: "Diálogo competitivo",
    3: "Concurso",
    4: "Concorrência eletrônica",
    5: "Concorrência presencial",
    6: "Pregão eletrônico",
    7: "Pregão presencial",
    8: "Dispensa de licitação",
    9: "Inexigibilidade",
    12: "Credenciamento",
    13: "Leilão presencial",
}

# Encerra em N dias ou menos => urgente.
DIAS_URGENTE = 3


@dataclass(frozen=True, slots=True)
class Licitacao:
    """Um registro já normalizado, pronto para a interface."""

    id: str
    objeto: str
    orgao: str
    cnpj: str
    unidade: str
    municipio: str
    modalidade: str
    modalidade_id: int
    situacao: str
    valor: float | None
    publicacao: str | None
    abertura: str | None
    encerramento: str | None
    dias_para_encerrar: int | None
    status_prazo: str
    link: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _texto(valor: Any, padrao: str = "") -> str:
    """Colapsa espaço e quebra de linha. O PNCP manda objeto com `\\n` no meio."""
    if valor is None:
        return padrao
    return " ".join(str(valor).split()) or padrao


def _valor(bruto: Any) -> float | None:
    """`None` e `0` significam a mesma coisa aqui: valor não informado.

    Tratar 0 como zero real faria o total somar errado e faria a interface
    exibir "R$ 0,00" como se fosse um contrato de graça.
    """
    if bruto is None:
        return None
    try:
        numero = float(bruto)
    except (TypeError, ValueError):
        return None
    return numero if numero > 0 else None


def _data_iso(bruto: Any) -> str | None:
    """Aceita o formato do PNCP e devolve ISO, ou `None` se não der para ler."""
    if not bruto:
        return None
    try:
        return datetime.fromisoformat(str(bruto)).isoformat()
    except ValueError:
        return None


def dias_ate(encerramento: str | None, hoje: date) -> int | None:
    """Dias inteiros entre hoje e o encerramento. Negativo se já passou."""
    if not encerramento:
        return None
    try:
        alvo = datetime.fromisoformat(encerramento).date()
    except ValueError:
        return None
    return (alvo - hoje).days


def status_prazo(dias: int | None) -> str:
    """Classifica o prazo. É o que colore a linha e ordena a urgência.

    Sem data de encerramento o status é `sem_prazo`, nunca `aberto` — dizer
    "aberto" sobre um dado que não existe é inventar informação.
    """
    if dias is None:
        return "sem_prazo"
    if dias < 0:
        return "encerrado"
    if dias <= DIAS_URGENTE:
        return "urgente"
    return "aberto"


def normalizar(bruto: dict[str, Any], hoje: date | None = None) -> Licitacao:
    """Converte um item cru do PNCP em `Licitacao`.

    `hoje` é parâmetro, e não `date.today()` dentro da função, para que o teste
    consiga fixar a data e verificar a regra de prazo sem depender do relógio.
    """
    hoje = hoje or date.today()

    orgao = bruto.get("orgaoEntidade") or {}
    unidade = bruto.get("unidadeOrgao") or {}

    encerramento = _data_iso(bruto.get("dataEncerramentoProposta"))
    dias = dias_ate(encerramento, hoje)
    modalidade_id = bruto.get("modalidadeId") or 0

    return Licitacao(
        id=_texto(bruto.get("numeroControlePNCP")),
        objeto=_texto(bruto.get("objetoCompra"), "Objeto não informado"),
        orgao=_texto(orgao.get("razaoSocial"), "Órgão não informado"),
        cnpj=_texto(orgao.get("cnpj")),
        unidade=_texto(unidade.get("nomeUnidade")),
        municipio=_texto(unidade.get("municipioNome"), "Não informado"),
        modalidade=_texto(
            bruto.get("modalidadeNome"),
            MODALIDADES.get(modalidade_id, "Não informada"),
        ),
        modalidade_id=modalidade_id,
        situacao=_texto(bruto.get("situacaoCompraNome")),
        valor=_valor(bruto.get("valorTotalEstimado")),
        publicacao=_data_iso(bruto.get("dataPublicacaoPncp")),
        abertura=_data_iso(bruto.get("dataAberturaProposta")),
        encerramento=encerramento,
        dias_para_encerrar=dias,
        status_prazo=status_prazo(dias),
        link=bruto.get("linkSistemaOrigem") or None,
    )


def deduplicar(itens: list[Licitacao]) -> list[Licitacao]:
    """Remove repetição por `numeroControlePNCP`.

    Necessário porque o backend consulta várias modalidades e o mesmo registro
    pode voltar em mais de uma resposta. Sem isso, o total soma duas vezes.
    Registro sem id é mantido — descartar dado por falta de chave é pior.
    """
    vistos: set[str] = set()
    saida: list[Licitacao] = []
    for item in itens:
        if not item.id:
            saida.append(item)
            continue
        if item.id in vistos:
            continue
        vistos.add(item.id)
        saida.append(item)
    return saida


def resumir(itens: list[Licitacao]) -> dict[str, Any]:
    """Agregados exibidos no topo. Só conta o que existe.

    `valor_total` ignora registro sem valor, e `com_valor` diz quantos
    entraram na conta — sem isso o usuário lê o total como se fosse de todos.
    """
    com_valor = [i.valor for i in itens if i.valor is not None]
    urgentes = [i for i in itens if i.status_prazo == "urgente"]

    orgaos: dict[str, float] = {}
    for item in itens:
        if item.valor is not None:
            orgaos[item.orgao] = orgaos.get(item.orgao, 0.0) + item.valor

    maiores = sorted(orgaos.items(), key=lambda par: par[1], reverse=True)[:8]

    return {
        "total": len(itens),
        "com_valor": len(com_valor),
        "valor_total": sum(com_valor),
        "urgentes": len(urgentes),
        "por_orgao": [{"orgao": nome, "valor": valor} for nome, valor in maiores],
    }
