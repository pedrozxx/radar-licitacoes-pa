/**
 * Filtro e ordenação no cliente.
 *
 * Roda sobre o snapshot já carregado, então é instantâneo e funciona mesmo
 * com o PNCP fora do ar. Funções puras de propósito: é a regra que decide
 * o que o usuário vê, e precisa de teste.
 */

import type { Filtros, Licitacao, Resumo } from './types'

/** Remove acento para que "Belem" encontre "Belém". */
function normalizar(texto: string): string {
  return texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
}

export function filtrar(itens: Licitacao[], filtros: Filtros): Licitacao[] {
  let resultado = itens

  if (filtros.municipio) {
    const alvo = normalizar(filtros.municipio)
    resultado = resultado.filter((i) => normalizar(i.municipio) === alvo)
  }

  if (filtros.busca.trim()) {
    // Todos os termos precisam aparecer, em qualquer ordem e em qualquer
    // um dos campos de texto. Busca por substring resolve o caso real
    // ("papel a4") melhor do que casar a frase inteira.
    const termos = normalizar(filtros.busca).split(/\s+/).filter(Boolean)
    resultado = resultado.filter((i) => {
      const alvo = normalizar(`${i.objeto} ${i.orgao} ${i.unidade} ${i.municipio}`)
      return termos.every((t) => alvo.includes(t))
    })
  }

  if (filtros.status === 'abertas') {
    resultado = resultado.filter(
      (i) => i.status_prazo === 'aberto' || i.status_prazo === 'urgente',
    )
  } else if (filtros.status === 'urgentes') {
    resultado = resultado.filter((i) => i.status_prazo === 'urgente')
  }

  return ordenar(resultado, filtros.ordenar)
}

/** 0 = ainda aberto, 1 = já encerrado, 2 = sem prazo informado. */
function faixaDePrazo(dias: number | null): 0 | 1 | 2 {
  if (dias === null) return 2
  return dias >= 0 ? 0 : 1
}

export function ordenar(itens: Licitacao[], criterio: Filtros['ordenar']): Licitacao[] {
  const copia = [...itens]

  if (criterio === 'valor') {
    // Sem valor vai para o fim, não para o topo como se fosse zero.
    return copia.sort((a, b) => (b.valor ?? -1) - (a.valor ?? -1))
  }

  if (criterio === 'publicacao') {
    return copia.sort((a, b) => (b.publicacao ?? '').localeCompare(a.publicacao ?? ''))
  }

  // Prazo, em três faixas:
  //   1. ainda aberto — o que fecha antes vem primeiro
  //   2. já encerrado — o que venceu há menos tempo vem primeiro
  //   3. sem prazo informado
  //
  // Ordenar só pelo número poria -495 (venceu há mais de um ano) no topo de
  // uma lista chamada "prazo mais próximo", que é o oposto do que o usuário
  // pediu. E `null` virando 0 subiria ao topo fingindo urgência inexistente.
  return copia.sort((a, b) => {
    const fa = faixaDePrazo(a.dias_para_encerrar)
    const fb = faixaDePrazo(b.dias_para_encerrar)
    if (fa !== fb) return fa - fb
    if (fa === 2) return 0 // ambos sem prazo
    // Dentro da mesma faixa, o mais próximo de hoje primeiro: crescente entre
    // os abertos (0, 1, 2…) e decrescente entre os vencidos (-1, -2, …).
    const da = a.dias_para_encerrar ?? 0
    const db = b.dias_para_encerrar ?? 0
    return fa === 0 ? da - db : db - da
  })
}

/**
 * Recalcula os agregados sobre a lista filtrada.
 *
 * Precisa ser recalculado, e não reaproveitado do snapshot: o total do
 * arquivo é de todos os registros, e exibi-lo ao lado de uma lista filtrada
 * faria o usuário ler um número que não corresponde ao que está vendo.
 */
export function resumirLista(itens: Licitacao[]): Resumo {
  const comValor = itens.filter((i) => i.valor !== null) as (Licitacao & { valor: number })[]

  const porOrgao = new Map<string, number>()
  for (const item of comValor) {
    porOrgao.set(item.orgao, (porOrgao.get(item.orgao) ?? 0) + item.valor)
  }

  return {
    total: itens.length,
    com_valor: comValor.length,
    valor_total: comValor.reduce((soma, i) => soma + i.valor, 0),
    urgentes: itens.filter((i) => i.status_prazo === 'urgente').length,
    por_orgao: [...porOrgao.entries()]
      .map(([orgao, valor]) => ({ orgao, valor }))
      .sort((a, b) => b.valor - a.valor)
      .slice(0, 8),
  }
}

/** Municípios presentes nos dados, para o filtro não oferecer opção vazia. */
export function municipiosDisponiveis(itens: Licitacao[]): string[] {
  return [...new Set(itens.map((i) => i.municipio))].sort((a, b) =>
    a.localeCompare(b, 'pt-BR'),
  )
}
