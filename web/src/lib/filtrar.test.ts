import { describe, expect, it } from 'vitest'

import { filtrar, municipiosDisponiveis, ordenar, resumirLista } from './filtrar'
import { FILTROS_INICIAIS, type Licitacao } from './types'

function licitacao(troca: Partial<Licitacao> = {}): Licitacao {
  return {
    id: 'a',
    objeto: 'Aquisição de materiais de consumo',
    orgao: 'COMANDO DO EXERCITO',
    cnpj: '00394452000103',
    unidade: '8 BATALHAO',
    municipio: 'Belém',
    modalidade: 'Pregão eletrônico',
    modalidade_id: 6,
    situacao: 'Divulgada no PNCP',
    valor: 1000,
    publicacao: '2026-08-03T04:00:10',
    abertura: '2026-08-04T08:00:00',
    encerramento: '2026-08-25T09:00:00',
    dias_para_encerrar: 6,
    status_prazo: 'aberto',
    link: null,
    ...troca,
  }
}

describe('filtrar por município', () => {
  const itens = [
    licitacao({ id: '1', municipio: 'Belém' }),
    licitacao({ id: '2', municipio: 'Castanhal' }),
  ]

  it('filtra pelo nome exato', () => {
    const saida = filtrar(itens, { ...FILTROS_INICIAIS, municipio: 'Castanhal' })
    expect(saida).toHaveLength(1)
    expect(saida[0]?.municipio).toBe('Castanhal')
  })

  it('ignora acento — "Belem" encontra "Belém"', () => {
    const saida = filtrar(itens, { ...FILTROS_INICIAIS, municipio: 'Belem' })
    expect(saida).toHaveLength(1)
  })
})

describe('busca textual', () => {
  const itens = [
    licitacao({ id: '1', objeto: 'Aquisição de papel A4' }),
    licitacao({ id: '2', objeto: 'Contratação de serviço de limpeza' }),
  ]

  it('acha por parte do objeto', () => {
    expect(filtrar(itens, { ...FILTROS_INICIAIS, busca: 'papel' })).toHaveLength(1)
  })

  it('exige todos os termos, em qualquer ordem', () => {
    expect(filtrar(itens, { ...FILTROS_INICIAIS, busca: 'a4 papel' })).toHaveLength(1)
    expect(filtrar(itens, { ...FILTROS_INICIAIS, busca: 'papel limpeza' })).toHaveLength(0)
  })

  it('busca também no órgão', () => {
    expect(filtrar(itens, { ...FILTROS_INICIAIS, busca: 'exercito' })).toHaveLength(2)
  })

  it('busca vazia não filtra nada', () => {
    expect(filtrar(itens, { ...FILTROS_INICIAIS, busca: '   ' })).toHaveLength(2)
  })
})

describe('filtro por status', () => {
  const itens = [
    licitacao({ id: '1', status_prazo: 'aberto' }),
    licitacao({ id: '2', status_prazo: 'urgente' }),
    licitacao({ id: '3', status_prazo: 'encerrado' }),
    licitacao({ id: '4', status_prazo: 'sem_prazo' }),
  ]

  it('"abertas" inclui urgentes e exclui encerradas e sem prazo', () => {
    const saida = filtrar(itens, { ...FILTROS_INICIAIS, status: 'abertas' })
    expect(saida.map((i) => i.id).sort()).toEqual(['1', '2'])
  })

  it('"urgentes" traz só urgentes', () => {
    const saida = filtrar(itens, { ...FILTROS_INICIAIS, status: 'urgentes' })
    expect(saida.map((i) => i.id)).toEqual(['2'])
  })
})

describe('ordenação', () => {
  it('por prazo: sem prazo vai para o fim, não para o topo', () => {
    // Se `null` virasse 0, o registro sem prazo subiria ao topo fingindo
    // urgência máxima — exatamente o oposto da verdade.
    const itens = [
      licitacao({ id: 'sem', dias_para_encerrar: null, status_prazo: 'sem_prazo' }),
      licitacao({ id: 'longe', dias_para_encerrar: 30 }),
      licitacao({ id: 'perto', dias_para_encerrar: 2 }),
    ]
    expect(ordenar(itens, 'prazo').map((i) => i.id)).toEqual(['perto', 'longe', 'sem'])
  })

  it('por prazo: o que fecha logo vem antes do que já venceu', () => {
    // Ordenar só pelo número poria -495 (venceu há mais de um ano) no topo de
    // uma lista chamada "prazo mais próximo" — exatamente o oposto do que o
    // usuário pediu. O que ainda dá para disputar vem primeiro.
    const itens = [
      licitacao({ id: 'vencido-antigo', dias_para_encerrar: -495, status_prazo: 'encerrado' }),
      licitacao({ id: 'vencido-ontem', dias_para_encerrar: -1, status_prazo: 'encerrado' }),
      licitacao({ id: 'fecha-hoje', dias_para_encerrar: 0, status_prazo: 'urgente' }),
      licitacao({ id: 'fecha-em-10', dias_para_encerrar: 10, status_prazo: 'aberto' }),
      licitacao({ id: 'sem-prazo', dias_para_encerrar: null, status_prazo: 'sem_prazo' }),
    ]
    expect(ordenar(itens, 'prazo').map((i) => i.id)).toEqual([
      'fecha-hoje',
      'fecha-em-10',
      'vencido-ontem',
      'vencido-antigo',
      'sem-prazo',
    ])
  })

  it('por valor: sem valor vai para o fim', () => {
    const itens = [
      licitacao({ id: 'sem', valor: null }),
      licitacao({ id: 'alto', valor: 5000 }),
      licitacao({ id: 'baixo', valor: 10 }),
    ]
    expect(ordenar(itens, 'valor').map((i) => i.id)).toEqual(['alto', 'baixo', 'sem'])
  })

  it('não muda o array original', () => {
    const itens = [licitacao({ id: 'a', valor: 1 }), licitacao({ id: 'b', valor: 2 })]
    ordenar(itens, 'valor')
    expect(itens.map((i) => i.id)).toEqual(['a', 'b'])
  })
})

describe('resumirLista', () => {
  it('recalcula sobre a lista filtrada, não sobre o total do arquivo', () => {
    // Reaproveitar o resumo do snapshot ao lado de uma lista filtrada faria o
    // usuário ler um número que não corresponde ao que está vendo na tela.
    const itens = [licitacao({ id: '1', valor: 100 }), licitacao({ id: '2', valor: 300 })]
    const filtrados = filtrar(itens, { ...FILTROS_INICIAIS, busca: 'materiais' })
    expect(resumirLista(filtrados).valor_total).toBe(400)
  })

  it('ignora sem valor no total e informa quantos contou', () => {
    const itens = [
      licitacao({ id: '1', valor: 100 }),
      licitacao({ id: '2', valor: null }),
    ]
    const resumo = resumirLista(itens)
    expect(resumo.total).toBe(2)
    expect(resumo.com_valor).toBe(1)
    expect(resumo.valor_total).toBe(100)
  })

  it('lista vazia devolve zeros sem quebrar', () => {
    expect(resumirLista([])).toEqual({
      total: 0,
      com_valor: 0,
      valor_total: 0,
      urgentes: 0,
      por_orgao: [],
    })
  })

  it('agrupa por órgão somando', () => {
    const itens = [
      licitacao({ id: '1', orgao: 'A', valor: 100 }),
      licitacao({ id: '2', orgao: 'B', valor: 300 }),
      licitacao({ id: '3', orgao: 'A', valor: 50 }),
    ]
    expect(resumirLista(itens).por_orgao).toEqual([
      { orgao: 'B', valor: 300 },
      { orgao: 'A', valor: 150 },
    ])
  })
})

describe('municipiosDisponiveis', () => {
  it('lista sem repetir e em ordem', () => {
    const itens = [
      licitacao({ id: '1', municipio: 'Castanhal' }),
      licitacao({ id: '2', municipio: 'Belém' }),
      licitacao({ id: '3', municipio: 'Castanhal' }),
    ]
    expect(municipiosDisponiveis(itens)).toEqual(['Belém', 'Castanhal'])
  })
})
