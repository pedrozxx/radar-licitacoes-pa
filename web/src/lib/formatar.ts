/**
 * Formatação para exibição.
 *
 * Fica isolado em funções puras porque é aqui que mora a regra mais fácil de
 * errar em painel de dado público: **ausência não é zero**. O PNCP manda
 * `null` e `0` para "valor não informado"; imprimir "R$ 0,00" faria a tela
 * afirmar que existe contrato de graça.
 */

/** Reais em português, sem centavos quando o número é grande demais para importar. */
export function formatarValor(valor: number | null): string {
  if (valor === null || Number.isNaN(valor)) return 'não informado'
  return valor.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: valor >= 1000 ? 0 : 2,
  })
}

/** Versão compacta para os agregados do topo: R$ 5,1 mi. */
export function formatarValorCompacto(valor: number): string {
  if (valor >= 1_000_000) return `R$ ${(valor / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi`
  if (valor >= 1_000) return `R$ ${(valor / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 0 })} mil`
  return formatarValor(valor)
}

/**
 * Interpreta a data no fuso LOCAL.
 *
 * `new Date('2026-07-29')` é lido como meia-noite **UTC**; em UTC-3 isso vira
 * 28/07 às 21h e a tela mostra o dia anterior. Acrescentar a hora força a
 * leitura local. Datas que já vêm com hora (`...T09:00:00`) não têm o problema.
 */
function paraDataLocal(iso: string): Date {
  return new Date(/^\d{4}-\d{2}-\d{2}$/.test(iso) ? `${iso}T00:00:00` : iso)
}

export function formatarData(iso: string | null): string {
  if (!iso) return '—'
  const data = paraDataLocal(iso)
  if (Number.isNaN(data.getTime())) return '—'
  return data.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function formatarDataHora(iso: string | null): string {
  if (!iso) return '—'
  const data = paraDataLocal(iso)
  if (Number.isNaN(data.getTime())) return '—'
  return data.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Texto do prazo. É o par textual da cor — sem ele, quem não distingue cor
 * perde a informação de urgência inteira.
 */
export function textoPrazo(dias: number | null): string {
  if (dias === null) return 'sem prazo informado'
  if (dias < 0) return `encerrou há ${Math.abs(dias)} ${Math.abs(dias) === 1 ? 'dia' : 'dias'}`
  if (dias === 0) return 'encerra hoje'
  if (dias === 1) return 'encerra amanhã'
  return `encerra em ${dias} dias`
}

/** CNPJ com máscara. Devolve o original se não tiver 14 dígitos. */
export function formatarCnpj(cnpj: string): string {
  const digitos = cnpj.replace(/\D/g, '')
  if (digitos.length !== 14) return cnpj
  return digitos.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5')
}

/** Corta sem cortar palavra no meio. */
export function resumirTexto(texto: string, limite: number): string {
  if (texto.length <= limite) return texto
  const corte = texto.slice(0, limite)
  const ultimoEspaco = corte.lastIndexOf(' ')
  return `${corte.slice(0, ultimoEspaco > limite * 0.6 ? ultimoEspaco : limite).trimEnd()}…`
}
