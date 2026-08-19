import { describe, expect, it } from 'vitest'

import {
  formatarCnpj,
  formatarData,
  formatarValor,
  formatarValorCompacto,
  resumirTexto,
  textoPrazo,
} from './formatar'

describe('formatarValor', () => {
  it('formata em reais', () => {
    expect(formatarValor(1500)).toContain('1.500')
  })

  it('diz "não informado" em vez de R$ 0,00', () => {
    // O PNCP usa null para valor ausente. Imprimir "R$ 0,00" faria a tela
    // afirmar que existe um contrato de graça.
    expect(formatarValor(null)).toBe('não informado')
  })

  it('não quebra com NaN', () => {
    expect(formatarValor(Number.NaN)).toBe('não informado')
  })

  it('mantém centavos em valor pequeno', () => {
    expect(formatarValor(373.62)).toContain('373,62')
  })
})

describe('formatarValorCompacto', () => {
  it('abrevia milhões', () => {
    expect(formatarValorCompacto(5_133_749)).toBe('R$ 5,1 mi')
  })

  it('abrevia milhares', () => {
    expect(formatarValorCompacto(84_451)).toBe('R$ 84 mil')
  })

  it('mantém valor pequeno por extenso', () => {
    expect(formatarValorCompacto(373.62)).toContain('373,62')
  })
})

describe('textoPrazo', () => {
  it.each([
    [null, 'sem prazo informado'],
    [0, 'encerra hoje'],
    [1, 'encerra amanhã'],
    [5, 'encerra em 5 dias'],
    [-1, 'encerrou há 1 dia'],
    [-5, 'encerrou há 5 dias'],
  ])('dias %s vira "%s"', (dias, esperado) => {
    expect(textoPrazo(dias)).toBe(esperado)
  })

  it('nunca chama de aberto o que não tem prazo', () => {
    // O texto é o par da cor: sem ele, quem não distingue cor perde a
    // informação de urgência inteira.
    expect(textoPrazo(null)).not.toContain('encerra em')
  })
})

describe('formatarData', () => {
  it('formata ISO em pt-BR', () => {
    expect(formatarData('2026-08-14T09:00:00')).toBe('14/08/2026')
  })

  it('devolve travessão para nulo', () => {
    expect(formatarData(null)).toBe('—')
  })

  it('devolve travessão para data ilegível', () => {
    expect(formatarData('31/12/2026')).toBe('—')
  })

  it('não recua um dia em data sem hora', () => {
    // `new Date('2026-07-29')` é interpretado como meia-noite UTC; em UTC-3
    // isso vira 28/07 às 21h e a tela mostra o dia anterior. O período exibido
    // no cabeçalho vinha um dia menor que o coletado por causa disto.
    expect(formatarData('2026-07-29')).toBe('29/07/2026')
    expect(formatarData('2026-01-01')).toBe('01/01/2026')
  })
})

describe('formatarCnpj', () => {
  it('aplica a máscara', () => {
    expect(formatarCnpj('00394452000103')).toBe('00.394.452/0001-03')
  })

  it('devolve o original quando não tem 14 dígitos', () => {
    expect(formatarCnpj('123')).toBe('123')
  })
})

describe('resumirTexto', () => {
  it('não corta o que já cabe', () => {
    expect(resumirTexto('curto', 20)).toBe('curto')
  })

  it('corta sem partir palavra ao meio', () => {
    const saida = resumirTexto('Aquisição de materiais de consumo diversos', 25)
    expect(saida.endsWith('…')).toBe(true)
    expect(saida.length).toBeLessThanOrEqual(26)
    expect(saida).not.toContain('consu…')
  })
})
