import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('avisa quando o snapshot foi cortado mesmo sem modalidade indisponível', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      gerado_em: '2026-09-29T09:00:00Z', uf: 'PA',
      periodo: { inicio: '2026-09-01', fim: '2026-09-29' },
      modalidades_coletadas: [6], modalidades_falhas: [], truncado: true,
      resumo: { total: 0, com_valor: 0, valor_total: 0, urgentes: 0, por_orgao: [] },
      itens: [],
    }),
  }))
  render(<App />)
  expect(await screen.findByText('Esta coleta está incompleta')).toBeInTheDocument()
})
