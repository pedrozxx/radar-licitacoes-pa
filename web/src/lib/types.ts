/** Tipos do contrato com a API. Espelham `api/_core/normalize.py`. */

export type StatusPrazo = 'aberto' | 'urgente' | 'encerrado' | 'sem_prazo'

export interface Licitacao {
  id: string
  objeto: string
  orgao: string
  cnpj: string
  unidade: string
  municipio: string
  modalidade: string
  modalidade_id: number
  situacao: string
  /** `null` quando o PNCP não informou. Nunca 0 — ver `formatarValor`. */
  valor: number | null
  publicacao: string | null
  abertura: string | null
  encerramento: string | null
  dias_para_encerrar: number | null
  status_prazo: StatusPrazo
  link: string | null
}

export interface Resumo {
  total: number
  /** Quantos entraram em `valor_total`. Sem isto o total engana. */
  com_valor: number
  valor_total: number
  urgentes: number
  por_orgao: { orgao: string; valor: number }[]
}

export interface Snapshot {
  gerado_em: string
  uf: string
  periodo: { inicio: string; fim: string }
  modalidades_coletadas: number[]
  modalidades_falhas: number[]
  resumo: Resumo
  itens: Licitacao[]
}

export interface Filtros {
  municipio: string
  busca: string
  status: 'todas' | 'abertas' | 'urgentes'
  ordenar: 'prazo' | 'valor' | 'publicacao'
}

export const FILTROS_INICIAIS: Filtros = {
  municipio: '',
  busca: '',
  status: 'todas',
  ordenar: 'prazo',
}
